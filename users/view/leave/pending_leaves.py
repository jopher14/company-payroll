from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from ..utils import castUser
from ...models import Leave


@login_required
def pending_leaves(request: HttpRequest) -> HttpResponse:
    user = castUser(request)

    if user.role == "manager":
        # Manager sees supervisor + employee requests
        leaves = Leave.objects.filter(
            employee__role__in=["supervisor", "employee"], status="Pending"
        )
    elif user.role == "supervisor":
        # Supervisor sees employee requests
        leaves = Leave.objects.filter(
            employee__role="employee", status="Pending"
        )
    else:
        # Employees only see their own leave requests
        leaves = Leave.objects.filter(employee=user, status="Pending")

    return render(request, "leave/pending_leaves.html", {"leaves": leaves})
