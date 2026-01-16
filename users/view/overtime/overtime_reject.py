from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from ...models import Overtime
from ..utils import castUser


@login_required
def overtime_reject(request: HttpRequest, pk) -> HttpResponse:
    user = castUser(request)

    overtime = get_object_or_404(Overtime, pk=pk)

    # Rejection logic
    if overtime.employee.role == "employee":
        if user.role in ["supervisor", "manager"]:
            overtime.status = "rejected"
            overtime.reviewed_by = user
            overtime.save()
            messages.warning(request, "Overtime rejected ❌")
        else:
            messages.error(request, "You are not authorized to reject this request ❌")

    elif overtime.employee.role == "supervisor":
        if user.role == "manager":
            overtime.status = "rejected"
            overtime.reviewed_by = user
            overtime.save()
            messages.warning(request, "Overtime rejected ❌")
        else:
            messages.error(request, "You are not authorized to reject this request ❌")

    elif overtime.employee.role == "manager":
        messages.error(request, "Manager's overtime cannot be rejected ❌")

    return redirect("users:overtime_list")
