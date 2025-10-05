from holidays.countries import Philippines
from typing import cast
from django.shortcuts import render, get_object_or_404, redirect
from .models import Payroll
from django.db import transaction
from users.models import User, Attendance
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpRequest
from django.contrib import messages
from .utils import compute_sss, compute_philhealth, compute_pagibig, compute_withholding_tax
from decimal import Decimal
from datetime import datetime
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
    user = request.user
    assert user.is_authenticated

    payslips = Payroll.objects.filter(employee=user)

    for p in payslips:
        # Compute loan deductions for each payslip
        loan_deduct, loan_breakdown, loan_type_summary = compute_loan_deduction(
            p.employee,
            period={"month": p.month_name, "year": p.year}
        )

        p.loan_deduction = loan_deduct
        p.loan_breakdown = loan_breakdown
        p.loan_type_summary = loan_type_summary

        # Compute total deductions excluding loan deduction
        p.total_deductions = (
            p.sss
            + p.philhealth
            + p.pagibig
            + p.withholding_tax
            + p.attendance_deduction
        )

        # Compute gross salary
        p.gross_salary = (
            p.basic_salary
            + p.allowances
            + p.overtime_pay
            + p.holiday_pay
        )

        # Compute net pay
        p.net_pay = p.gross_salary - p.total_deductions - p.loan_deduction

        # Compute rates if missing
        p.daily_rate = p.daily_rate or compute_daily_rate(
            p.employee.salary or Decimal("0.00"),
            workdays_per_month=22,
        )
        p.hourly_rate = p.hourly_rate or compute_hourly_rate(
            p.employee.salary or Decimal("0.00"),
            workdays_per_month=22,
            hours_per_day=8,
        )

    return render(
        request,
        "payroll/my_payslip.html",
        {"payslips": payslips}
    )


@login_required
def view_payslip(request: HttpRequest, pk: int) -> HttpResponse:
    payslip = get_object_or_404(Payroll, pk=pk)

    # Compute gross salary
    gross_salary = (
        payslip.basic_salary
        + payslip.allowances
        + payslip.overtime_pay
        + payslip.holiday_pay
    )

    # Compute loan deductions
    loan_deduct, loan_breakdown, loan_type_summary = compute_loan_deduction(
        payslip.employee,
        period={"month": payslip.month_name, "year": payslip.year}
    )

    # Compute total deductions excluding loan deduction
    total_deductions = (
        payslip.sss
        + payslip.philhealth
        + payslip.pagibig
        + payslip.withholding_tax
        + payslip.attendance_deduction
    )

    # Compute net pay
    net_pay = gross_salary - total_deductions - loan_deduct

    # Compute rates if missing
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
        "total_deductions": total_deductions,
        "loan_deduct": loan_deduct,
        "loan_breakdown": loan_breakdown,
        "loan_type_summary": loan_type_summary,
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


@login_required
def generate_payroll(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    # --- Permission check ---
    if user.role != "human_resources":
        messages.error(request, "You are not authorized to generate payroll.")
        return redirect("payroll:payroll_list")

    today = datetime.now()
    year, month = today.year, today.month
    ph_holidays = set(Philippines(years=[year]).keys())

    if request.method == "POST":
        period = request.POST.get("period", "")
        if period not in ["first_half", "second_half"]:
            messages.error(request, "Invalid pay period selected.")
            return redirect("payroll:generate_payroll")

        start_day, end_day = get_period_range(period)
        employees = User.objects.filter(role__in=["employee", "supervisor", "manager"])
        skipped = []
        payroll_data = []

        with transaction.atomic():
            for emp in employees:
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

                # --- Loan deductions (Personal loans only) ---
                loan_deduction, loan_breakdown, loan_type_summary = compute_loan_deduction(emp, period)

                # --- Government deductions ---
                sss = compute_sss(salary) / 2
                philhealth = compute_philhealth(salary) / 2
                pagibig = compute_pagibig(salary) / 2
                tax = compute_withholding_tax(salary, overtime_pay + holiday_pay) / 2

                # --- Combine totals ---
                gov_deductions = sss + philhealth + pagibig + tax
                total_deductions = float(attendance_deduction) + float(loan_deduction) + float(gov_deductions)
                net_pay = float(half_salary) + float(half_allowances) + float(overtime_pay) + float(holiday_pay) - float(total_deductions)

                # --- Avoid duplicate payroll entries ---
                if Payroll.objects.filter(employee=emp, month=month, year=year, period=period).exists():
                    skipped.append(emp.get_full_name() or emp.username)
                    continue

                # --- Save payroll record ---
                Payroll.objects.create(
                    employee=emp,
                    month=month,
                    year=year,
                    period=period,
                    basic_salary=half_salary,
                    allowances=half_allowances,
                    overtime_pay=overtime_pay,
                    holiday_pay=holiday_pay,
                    attendance_deduction=attendance_deduction,
                    loan_deduction=loan_deduction,
                    sss=sss,
                    philhealth=philhealth,
                    pagibig=pagibig,
                    withholding_tax=tax,
                    total_deductions=total_deductions,
                    net_pay=net_pay,
                    daily_rate=daily_rate,
                    hourly_rate=hourly_rate,
                    loan_type_summary=loan_type_summary,  # Store for later
                )

                payroll_data.append({
                    "employee": emp.get_full_name(),
                    "attendance_deduction": attendance_deduction,
                    "loan_deduction": loan_deduction,
                    "gov_deductions": gov_deductions,
                    "net_pay": net_pay,
                    "loan_type_summary": loan_type_summary,
                })

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
