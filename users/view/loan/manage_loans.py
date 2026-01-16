from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from ...models import Loan
from ..utils import isHR


@login_required
@user_passes_test(isHR)
def manage_loans(request):
    loans = Loan.objects.select_related("employee").all().order_by("-start_date")
    return render(request, "loans/manage_loans.html", {"loans": loans})
