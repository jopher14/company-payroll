from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from ...forms import LoanForm
from ...models import Loan
from ..utils import isHR

from dateutil.relativedelta import relativedelta


@login_required
@user_passes_test(isHR)
def edit_loan(request: HttpRequest, pk: int) -> HttpResponse:
    loan = get_object_or_404(Loan, pk=pk)

    if request.method == "POST":
        form = LoanForm(request.POST, instance=loan)
        if form.is_valid():
            loan = form.save(commit=False)

            # recalc end_date when term or start_date changes
            if loan.start_date and loan.term_months:
                loan.end_date = loan.start_date + relativedelta(months=loan.term_months)

            loan.save()
            messages.success(request, "Loan updated successfully.")
            return redirect("users:manage_loans")
    else:
        form = LoanForm(instance=loan)

    return render(request, "loans/loan_form.html", {"form": form, "title": "✏️ Edit Loan"})
