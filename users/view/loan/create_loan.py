from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from ...forms import LoanForm
from ..utils import isHR

from dateutil.relativedelta import relativedelta


@login_required
@user_passes_test(isHR)
def create_loan(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)

            # Make sure deduction amount is valid
            loan.loan_deduct = Decimal(request.POST.get("loan_deduct", "0"))
            if not loan.loan_deduct or loan.loan_deduct <= 0:
                loan.loan_deduct = loan.loan_amount  # fallback if empty

            # ✅ Initialize properly
            loan.balance = loan.loan_amount
            loan.is_active = True
            loan.status = "OPEN"

            # Auto compute end date
            if loan.start_date and loan.term_months:
                loan.end_date = loan.start_date + relativedelta(months=loan.term_months)

            loan.save()
            messages.success(request, f"Loan for {loan.employee.get_full_name()} created successfully.")
            return redirect("users:manage_loans")
    else:
        form = LoanForm()

    return render(request, "loans/loan_form.html", {"form": form, "title": "➕ Add Loan"})
