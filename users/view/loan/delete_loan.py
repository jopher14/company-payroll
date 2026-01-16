from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from ...models import Loan
from ..utils import isHR


@login_required
@user_passes_test(isHR)
def delete_loan(request: HttpRequest, pk: int) -> HttpResponse:
    loan = get_object_or_404(Loan, pk=pk)
    if request.method == "POST":
        loan.delete()
        messages.success(request, "Loan deleted successfully.")
        return redirect("users:manage_loans")
    return render(request, "loans/confirm_delete.html", {"loan": loan})
