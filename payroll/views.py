from typing import cast
from django.shortcuts import render, get_object_or_404, redirect
from .models import Payroll
from users.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpRequest
from django.contrib import messages
from .utils import compute_sss, compute_philhealth, compute_pagibig, compute_withholding_tax
from collections import defaultdict
from decimal import Decimal


@login_required
def my_payslips(request: HttpRequest) -> HttpResponse:
    user = request.user
    assert user.is_authenticated

    payslips = Payroll.objects.filter(employee=user)
    return render(request, "payroll/my_payslips.html", {"payslips": payslips})


@login_required
def view_payslip(request: HttpRequest, pk: int) -> HttpResponse:
    # Get the payslip or return 404
    payslip = get_object_or_404(Payroll, pk=pk, employee=request.user)  # only their own payslip

    return render(request, 'payroll/view_payslip.html', {'payslip': payslip})


@login_required
def payroll_report(request: HttpRequest) -> HttpResponse:
    payrolls = Payroll.objects.select_related("employee").all()
    return render(request, "payroll/payroll_report.html", {"payrolls": payrolls})


@login_required
def payroll_list(request: HttpRequest) -> HttpResponse:
    payrolls = Payroll.objects.select_related("employee")

    grouped = defaultdict(list)
    for p in payrolls:
        grouped[p.employee.role].append(p)

    context = {
        "grouped_payrolls": grouped
    }
    return render(request, "payroll/payroll_list.html", context)


@login_required
def generate_payroll(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)
    if user.role != "human_resources":  # Only HR allowed
        messages.error(request, "You are not authorized to generate payroll.")
        return redirect("payroll:payroll_list")

    employees = User.objects.filter(role__in=["employee", "supervisor", "manager"])

    for emp in employees:
        salary: Decimal = emp.salary or Decimal("0.00")

        # Compute deductions (all return Decimal)
        sss = compute_sss(salary)
        philhealth = compute_philhealth(salary)
        pagibig = compute_pagibig(salary)
        tax = compute_withholding_tax(salary)

        total_deductions: Decimal = sss + philhealth + pagibig + tax
        net_pay: Decimal = salary - total_deductions

        Payroll.objects.create(
            employee=emp,
            basic_salary=salary,
            sss=sss,
            philhealth=philhealth,
            pagibig=pagibig,
            withholding_tax=tax,
            total_deductions=total_deductions,
            net_pay=net_pay,
        )

    messages.success(request, "Payroll successfully generated for all employees!")
    return redirect("payroll:payroll_list")  # <-- redirect to payroll list
