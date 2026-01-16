from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from ...models import Overtime
from ..utils import castUser


@login_required
def overtime_action(request: HttpRequest, pk, action) -> HttpResponse:
    user = castUser(request)

    overtime = get_object_or_404(Overtime, pk=pk)

    # Only supervisors should be allowed
    if user.role != "supervisor":
        messages.error(request, "You are not authorized to perform this action.")
        return redirect("users:overtime_list")

    if action == "approve":
        overtime.status = "approved"
        overtime.reviewed_by = user  # ✅ assign to the correct field
        overtime.save()
        messages.success(
            request,
            f"Overtime request from {overtime.employee.first_name} approved ✅"
        )
    elif action == "reject":
        overtime.status = "rejected"
        overtime.reviewed_by = user  # ✅ assign to the correct field
        overtime.save()
        messages.warning(
            request,
            f"Overtime request from {overtime.employee.first_name} rejected ❌"
        )
    else:
        messages.error(request, "Invalid action.")

    return redirect("users:overtime_list")
