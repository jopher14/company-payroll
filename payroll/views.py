from typing import cast
from django.shortcuts import render, get_object_or_404, redirect
from .models import Payroll
from users.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpRequest
from django.contrib import messages
from .utils import compute_sss, compute_philhealth, compute_pagibig, compute_withholding_tax
from decimal import Decimal
from datetime import datetime


@login_required
def my_payslips(request: HttpRequest) -> HttpResponse:
    user = request.user
    assert user.is_authenticated

    payslips = Payroll.objects.filter(employee=user)
    return render(request, "payroll/my_payslip.html", {"payslips": payslips})


@login_required
def view_payslip(request, pk):
    payslip = get_object_or_404(Payroll, pk=pk)

    # Compute deductions if not stored already
    gross_salary = payslip.basic_salary + payslip.allowances
    deductions = payslip.sss + payslip.philhealth + payslip.pagibig + payslip.withholding_tax
    net_pay = gross_salary - deductions

    context = {
        "payslip": payslip,
        "gross_salary": gross_salary,
        "deductions": deductions,
        "net_pay": net_pay,
    }
    return render(request, "payroll/my_payslip.html", context)


@login_required
def payroll_report(request: HttpRequest) -> HttpResponse:
    payrolls = Payroll.objects.select_related("employee").all()
    return render(request, "payroll/payroll_report.html", {"payrolls": payrolls})


@login_required
def payroll_list(request):
    user = request.user

    if user.role == "human_resources":
        payrolls = Payroll.objects.all().select_related("employee")
    else:
        payrolls = Payroll.objects.filter(employee=user).select_related("employee")

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

            # ✅ Half salary + half allowances
            half_salary = salary / 2
            half_allowances = allowances / 2

            # ✅ Deductions
            sss = compute_sss(salary) / 2
            philhealth = compute_philhealth(salary) / 2
            pagibig = compute_pagibig(salary) / 2
            tax = compute_withholding_tax(salary) / 2

            total_deductions = sss + philhealth + pagibig + tax

            # ✅ Placeholder (later: fetch from Overtime & Holidays tables)
            overtime_pay = Decimal("0.00")
            holiday_pay = Decimal("0.00")

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
            )

        if skipped:
            messages.warning(
                request,
                f"Some payrolls already exist and were skipped: {', '.join(skipped)}",
            )
        messages.success(
            request,
            f"Payroll generated for {today.strftime('%B %Y')} ({period.replace('_', ' ').title()})!"
        )

        return redirect("payroll:payroll_list")

    return render(request, "payroll/generate_form.html")
