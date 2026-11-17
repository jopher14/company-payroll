from holidays.countries import Philippines
from typing import cast
from django.shortcuts import render, get_object_or_404, redirect
from .models import Payroll
from django.db import transaction
from users.models import User, Attendance, Loan
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpRequest
from django.contrib import messages
from .utils import compute_sss, compute_philhealth, compute_pagibig, compute_withholding_tax
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
import csv
from payroll.utils import (
    compute_daily_rate,
    compute_hourly_rate,
    compute_total_attendance_deduction,
    compute_employee_overtime,
    compute_loan_deduction,
)


@login_required
def my_payslips(request: HttpRequest) -> HttpResponse:
    payslips = Payroll.objects.filter(employee=request.user).order_by("-year", "-month", "-period")
    return render(request, "payroll/payroll_list.html", {"payrolls": payslips})


@login_required
def view_payslip(request: HttpRequest, pk: int) -> HttpResponse:
    user = cast(User, request.user)
    payslips = Payroll.objects.select_related("employee")
    if user.role != User.HUMAN_RESOURCES:
        payslips = payslips.filter(employee=user)
    payslip = get_object_or_404(payslips, pk=pk)

    # Older records may have no stored gross amount.
    gross_salary = payslip.gross_salary or (
        payslip.basic_salary + payslip.allowances + payslip.overtime_pay + payslip.holiday_pay
    )
    return render(
        request,
        "payroll/my_payslip.html",
        {"payslip": payslip, "gross_salary": gross_salary},
    )


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


@login_required
def generate_payroll(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    # --- Permission check ---
    if user.role != "human_resources":
        messages.error(request, "You are not authorized to generate payroll.")
        return redirect("payroll:payroll_list")

    today = timezone.localdate()
    year, month = today.year, today.month
    ph_holidays = set(Philippines(years=[year]).keys())

    if request.method == "POST":
        period = request.POST.get("period", "")
        if period not in ["first_half", "second_half"]:
            messages.error(request, "Invalid pay period selected.")
            return redirect("payroll:generate_payroll")

        start_day, end_day = get_period_range(period)
        employees = User.objects.filter(role__in=["employee", "supervisor", "manager"]).order_by("pk")
        skipped = []

        with transaction.atomic():
            for emp in employees.select_for_update():
                if Payroll.objects.filter(employee=emp, month=month, year=year, period=period).exists():
                    skipped.append(emp.get_full_name() or emp.username)
                    continue

                salary = emp.salary or Decimal("0.00")
                allowances = emp.allowances or (salary * Decimal("0.30"))

                daily_rate = compute_daily_rate(salary)
                hourly_rate = compute_hourly_rate(salary)

                # --- Semi-monthly base pay ---
                half_salary = salary / 2
                half_allowances = allowances / 2

                # --- Attendance deductions ---
                attendance_deduction, attendance_breakdown = compute_total_attendance_deduction(
                    emp, year, month, start_day, end_day, daily_rate, hourly_rate, holidays=ph_holidays
                )

                # --- Holiday pay ---
                holiday_pay = Decimal("0.00")
                for log in attendance_breakdown:
                    log_date = datetime.strptime(log["date"], "%Y-%m-%d").date()
                    if log_date in ph_holidays and "Absent" not in log["reason"]:
                        holiday_pay += daily_rate

                # --- Overtime pay ---
                overtime_pay = compute_employee_overtime(emp, year, month, start_day, end_day, hourly_rate)

                loans = Loan.objects.select_for_update().filter(employee=emp, is_active=True).order_by("pk")
                loan_deduction, loan_breakdown, loan_type_summary, updated_loans = compute_loan_deduction(loans)

                # --- Government deductions ---
                sss = compute_sss(salary) / 2
                philhealth = compute_philhealth(salary) / 2
                pagibig = compute_pagibig(salary) / 2
                tax = compute_withholding_tax(salary, overtime_pay + holiday_pay) / 2

                # Round each stored component before calculating the totals.
                payroll = Payroll(
                    employee=emp,
                    month=month,
                    year=year,
                    period=period,
                    basic_salary=half_salary,
                    allowances=half_allowances,
                    overtime_pay=overtime_pay,
                    holiday_pay=holiday_pay,
                    attendance_deduction=attendance_deduction,
                    attendance_breakdown=attendance_breakdown,
                    loan_deduction=loan_deduction,
                    loan_breakdown=loan_breakdown,
                    sss=sss,
                    philhealth=philhealth,
                    pagibig=pagibig,
                    withholding_tax=tax,
                    daily_rate=daily_rate,
                    hourly_rate=hourly_rate,
                    loan_type_summary=loan_type_summary,
                )

                payroll.save()
                Loan.objects.bulk_update(updated_loans, ["balance", "is_active"])

        # --- Post-generation messages ---
        if skipped:
            skipped_str = ", ".join(skipped[:5])
            if len(skipped) > 5:
                skipped_str += f" ... and {len(skipped) - 5} more"
            messages.warning(request, f"Some payrolls already exist and were skipped: {skipped_str}")

        messages.success(
            request,
            f"Payroll generated for {today.strftime('%B %Y')} ({period.replace('_', ' ').title()})!"
        )
        return redirect("payroll:payroll_list")

    return render(request, "payroll/generate_form.html")


@login_required
def download_attendance_breakdown(request: HttpRequest, emp_id: int, year: int, month: int, period: str) -> HttpResponse:
    user = cast(User, request.user)
    if user.role not in ["human_resources", "admin"] and user.id != emp_id:
        return HttpResponse("Not authorized", status=403)

    employee = get_object_or_404(User, pk=emp_id)

    # ✅ Get cutoff date range
    start_day, end_day = get_period_range(period)

    # ✅ Holidays for the year
    ph_holidays = set(Philippines(years=[year]).keys())

    # ✅ Compute attendance breakdown
    _, breakdown = compute_total_attendance_deduction(
        employee, year, month, start_day, end_day,
        daily_rate=Decimal(employee.salary) / Decimal(22) if employee.salary else Decimal("0.00"),
        hourly_rate=(Decimal(employee.salary) / Decimal(22) / Decimal(8)) if employee.salary else Decimal("0.00"),
        holidays=ph_holidays,
    )

    # 📄 Create CSV response
    response = HttpResponse(content_type="text/csv")
    filename = f"attendance_breakdown_{employee.username}_{year}_{month}_{period}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(["Date", "Time In", "Time Out", "Reason"])  # ✅ removed Deduction

    for entry in breakdown:  # ✅ iterate over list
        log_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        reason = entry.get("reason", "")

        # ✅ Mark holidays
        if log_date in ph_holidays:
            if reason:
                reason = f"Holiday, {reason}"
            else:
                reason = "Holiday"

        # ✅ Fetch actual time in/out
        att = Attendance.objects.filter(employee=employee, date=log_date).first()
        time_in = att.time_in.strftime("%H:%M") if att and att.time_in else ""
        time_out = att.time_out.strftime("%H:%M") if att and att.time_out else ""

        writer.writerow([log_date.isoformat(), time_in, time_out, reason])

    return response
