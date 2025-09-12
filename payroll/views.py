from typing import cast
from django.shortcuts import render, get_object_or_404, redirect
from .models import Payroll
from users.models import User, Overtime
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


@login_required
def generate_payroll(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)
    if user.role != "human_resources":
        messages.error(request, "You are not authorized to generate payroll.")
        return redirect("payroll:payroll_list")

    today = datetime.now()
    month = today.month
    year = today.year

    if request.method == "POST":
        period = request.POST.get("period") or ""
        if period not in ["first_half", "second_half"]:
            messages.error(request, "Invalid pay period selected.")
            return redirect("payroll:generate_payroll")

        employees = User.objects.filter(role__in=["employee", "supervisor", "manager"])
        skipped = []

        for emp in employees:
            salary: Decimal = emp.salary or Decimal("0.00")
            allowances: Decimal = emp.allowances or (salary * Decimal("0.30"))

            # ✅ Daily & Hourly Rate (based on full monthly salary)
            daily_rate = salary / Decimal("22")
            hourly_rate = daily_rate / Decimal("8")

            # ✅ Half salary + half allowances (semi-monthly payroll)
            half_salary = salary / 2
            half_allowances = allowances / 2

            # ✅ Deductions (halved for semi-monthly)
            sss = compute_sss(salary) / 2
            philhealth = compute_philhealth(salary) / 2
            pagibig = compute_pagibig(salary) / 2

            # ✅ Placeholder holiday pay (to implement later)
            holiday_pay = Decimal("0.00")

            # ==========================
            # ✅ OVERTIME COMPUTATION
            # ==========================
            overtime_pay = Decimal("0.00")

            # Example: if you already have Overtime model linked to employee
            overtime_logs = Overtime.objects.filter(
                employee=emp,
                date__year=year,
                date__month=month,
                status="approved"
            )

            for ot in overtime_logs:
                hours = ot.hours or Decimal("0.00")

                if ot.overtime_type == "ordinary":
                    overtime_pay += compute_ordinary_ot(hourly_rate, hours)
                elif ot.overtime_type == "restday":
                    overtime_pay += compute_restday_ot(hourly_rate, hours)
                elif ot.overtime_type == "special_holiday":
                    overtime_pay += compute_special_holiday_ot(hourly_rate, hours)
                elif ot.overtime_type == "special_holiday_restday":
                    overtime_pay += compute_special_holiday_restday_ot(hourly_rate, hours)
                elif ot.overtime_type == "regular_holiday":
                    overtime_pay += compute_regular_holiday_ot(hourly_rate, hours)
                elif ot.overtime_type == "regular_holiday_restday":
                    overtime_pay += compute_regular_holiday_restday_ot(hourly_rate, hours)
                elif ot.overtime_type == "double_holiday":
                    overtime_pay += compute_double_holiday_ot(hourly_rate, hours)
                elif ot.overtime_type == "double_holiday_restday":
                    overtime_pay += compute_double_holiday_restday_ot(hourly_rate, hours)

            # ✅ Tax (includes overtime)
            tax = compute_withholding_tax(salary, overtime_pay) / 2

            total_deductions = sss + philhealth + pagibig + tax

            net_pay = half_salary + half_allowances + overtime_pay + holiday_pay - total_deductions

            # ✅ Prevent duplicates
            exists = Payroll.objects.filter(
                employee=emp, month=month, year=year, period=period
            ).exists()

            if exists:
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
                holiday_pay=holiday_pay,
                sss=sss,
                philhealth=philhealth,
                pagibig=pagibig,
                withholding_tax=tax,
                total_deductions=total_deductions,
                net_pay=net_pay,
                daily_rate=daily_rate,
                hourly_rate=hourly_rate,
            )

        if skipped:
            skipped_str = ", ".join(skipped[:5])
            if len(skipped) > 5:
                skipped_str += f" ... and {len(skipped)-5} more"
            messages.warning(
                request,
                f"Some payrolls already exist and were skipped: {skipped_str}",
            )

        messages.success(
            request,
            f"Payroll generated for {today.strftime('%B %Y')} ({period.replace('_', ' ').title()})!"
        )

        return redirect("payroll:payroll_list")

    return render(request, "payroll/generate_form.html")
