from typing import Optional
from typing import cast
from django.shortcuts import render, get_object_or_404, redirect
from .models import Payroll
from users.models import User, Overtime, Attendance
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpRequest
from django.contrib import messages
from .utils import compute_sss, compute_philhealth, compute_pagibig, compute_withholding_tax
from decimal import Decimal
from datetime import datetime
from payroll.utils import (
    compute_daily_rate,
    compute_hourly_rate,
    compute_ordinary_ot,
    compute_restday_ot,
    compute_special_holiday_ot,
    compute_special_holiday_restday_ot,
    compute_regular_holiday_ot,
    compute_regular_holiday_restday_ot,
    compute_double_holiday_ot,
    compute_double_holiday_restday_ot,
)


@login_required
def my_payslips(request: HttpRequest) -> HttpResponse:
    user = request.user
    assert user.is_authenticated

    payslips = Payroll.objects.filter(employee=user)
    return render(request, "payroll/my_payslip.html", {"payslips": payslips})


@login_required
def view_payslip(request: HttpRequest, pk: int) -> HttpResponse:
    payslip = get_object_or_404(Payroll, pk=pk)

    # Compute gross, deductions, and net pay
    gross_salary = payslip.basic_salary + payslip.allowances
    deductions = (
        payslip.sss
        + payslip.philhealth
        + payslip.pagibig
        + payslip.withholding_tax
    )
    net_pay = gross_salary - deductions

    # ✅ Use stored daily/hourly rate, fallback to utils if missing
    daily_rate = payslip.daily_rate or compute_daily_rate(
        payslip.employee.salary or Decimal("0.00"),
        workdays_per_month=22,
    )
    hourly_rate = payslip.hourly_rate or compute_hourly_rate(
        payslip.employee.salary or Decimal("0.00"),
        workdays_per_month=22,
        hours_per_day=8,
    )

    context = {
        "payslip": payslip,
        "gross_salary": gross_salary,
        "deductions": deductions,
        "net_pay": net_pay,
        "daily_rate": daily_rate,
        "hourly_rate": hourly_rate,
    }
    return render(request, "payroll/my_payslip.html", context)


@login_required
def payroll_report(request: HttpRequest) -> HttpResponse:
    payrolls = Payroll.objects.select_related("employee").all()
    return render(request, "payroll/payroll_report.html", {"payrolls": payrolls})


@login_required
def payroll_list(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    if user.role == "human_resources":
        # HR can view all payroll records
        payrolls = Payroll.objects.select_related("employee").order_by("-year", "-month", "-period")
    else:
        # Regular employees only see their own
        payrolls = Payroll.objects.filter(employee=user).select_related("employee").order_by("-year", "-month", "-period")

    context = {
        "payrolls": payrolls,
    }
    return render(request, "payroll/payroll_list.html", context)


# ----------------------------
# 🔹 Helper Functions
# ----------------------------
def get_period_range(period: str):
    if period == "first_half":
        return 1, 15
    return 16, 31


def compute_attendance_deductions(
    emp: User,
    year: int,
    month: int,
    start_day: int,
    end_day: int,
    daily_rate: Optional[Decimal] = None,
    hourly_rate: Optional[Decimal] = None
) -> Decimal:
    """Aggregate all attendance-based deductions for a given employee + period."""
    logs = Attendance.objects.filter(
        employee=emp,
        date__year=year,
        date__month=month,
        date__day__gte=start_day,
        date__day__lte=end_day,
    )

    # Sum deductions, passing the rates to each attendance record
    return sum(
        (
            att.compute_deduction(
                daily_rate=daily_rate or Decimal("0.00"),
                hourly_rate=hourly_rate or Decimal("0.00")
            )
            for att in logs
        ),
        Decimal("0.00")
    )


def compute_overtime_pay(emp: User, year: int, month: int, start_day: int, end_day: int,
                         hourly_rate: Decimal) -> Decimal:
    """Compute total overtime pay for a given employee + period."""
    logs = Overtime.objects.filter(
        employee=emp,
        date__year=year,
        date__month=month,
        date__day__gte=start_day,
        date__day__lte=end_day,
        status="approved",
    )

    mapping = {
        "ordinary": compute_ordinary_ot,
        "restday": compute_restday_ot,
        "special_holiday": compute_special_holiday_ot,
        "special_holiday_restday": compute_special_holiday_restday_ot,
        "regular_holiday": compute_regular_holiday_ot,
        "regular_holiday_restday": compute_regular_holiday_restday_ot,
        "double_holiday": compute_double_holiday_ot,
        "double_holiday_restday": compute_double_holiday_restday_ot,
    }

    total = Decimal("0.00")
    for ot in logs:
        func = mapping.get(ot.overtime_type)
        if func:
            total += func(hourly_rate, ot.hours or Decimal("0.00"))
    return total


@login_required
def generate_payroll(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)
    if user.role != "human_resources":
        messages.error(request, "You are not authorized to generate payroll.")
        return redirect("payroll:payroll_list")

    today = datetime.now()
    month, year = today.month, today.year

    if request.method == "POST":
        period = request.POST.get("period") or ""
        if period not in ["first_half", "second_half"]:
            messages.error(request, "Invalid pay period selected.")
            return redirect("payroll:generate_payroll")

        start_day, end_day = get_period_range(period)
        employees = User.objects.filter(role__in=["employee", "supervisor", "manager"])
        skipped = []

        for emp in employees:
            salary = emp.salary or Decimal("0.00")
            allowances = emp.allowances or (salary * Decimal("0.30"))

            daily_rate = compute_daily_rate(salary)
            hourly_rate = compute_hourly_rate(salary)

            # ✅ Salary components
            half_salary = salary / 2
            half_allowances = allowances / 2

            # ✅ Gov deductions (halved)
            sss = compute_sss(salary) / 2
            philhealth = compute_philhealth(salary) / 2
            pagibig = compute_pagibig(salary) / 2

            # ✅ Attendance deductions
            attendance_deduction = compute_attendance_deductions(
                emp, year, month, start_day, end_day,
            )

            # ✅ Overtime
            overtime_pay = compute_overtime_pay(emp, year, month, start_day, end_day, hourly_rate)

            # ✅ Tax
            tax = compute_withholding_tax(salary, overtime_pay) / 2

            # ✅ Totals
            total_deductions = sss + philhealth + pagibig + tax + attendance_deduction
            net_pay = half_salary + half_allowances + overtime_pay - total_deductions

            # ✅ Prevent duplicates
            if Payroll.objects.filter(employee=emp, month=month, year=year, period=period).exists():
                skipped.append(emp.get_full_name() or emp.username)
                continue

            Payroll.objects.create(
                employee=emp,
                month=month,
                year=year,
                period=period,
                basic_salary=half_salary,
                allowances=half_allowances,
                overtime_pay=overtime_pay,
                holiday_pay=Decimal("0.00"),  # extend later if needed
                sss=sss,
                philhealth=philhealth,
                pagibig=pagibig,
                withholding_tax=tax,
                attendance_deduction=attendance_deduction,
                total_deductions=total_deductions,
                net_pay=net_pay,
                daily_rate=daily_rate,
                hourly_rate=hourly_rate,
            )

        # ✅ Feedback
        if skipped:
            skipped_str = ", ".join(skipped[:5])
            if len(skipped) > 5:
                skipped_str += f" ... and {len(skipped)-5} more"
            messages.warning(request, f"Some payrolls already exist and were skipped: {skipped_str}")

        messages.success(request, f"Payroll generated for {today.strftime('%B %Y')} ({period.replace('_', ' ').title()})!")
        return redirect("payroll:payroll_list")

    return render(request, "payroll/generate_form.html")
