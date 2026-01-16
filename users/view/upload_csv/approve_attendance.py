from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from ...models import ManualAttendanceRequest
from ..utils import castUser


@login_required
def approve_attendance(request: HttpRequest, request_id: int) -> HttpResponse:
    user = castUser(request)
    attendance = get_object_or_404(
        ManualAttendanceRequest,
        id=request_id,
        status="PENDING"
    )

    # Prevent self-approval
    if attendance.user == user:
        return redirect("users:attendance_requests")

    # Make sure the user has a 'role' attribute
    if not hasattr(user, "role") or not hasattr(attendance.user, "role"):
        return redirect("users:attendance_requests")

    user_role = user.role.lower()
    target_role = attendance.user.role.lower()

    # Employee → Supervisor
    if target_role == "employee" and user_role == "supervisor":
        attendance.status = "APPROVED"
        attendance.approved_by = user
        attendance.save()
        return redirect("users:attendance_requests")

    # Supervisor → Manager
    elif target_role == "supervisor" and user_role == "manager":
        attendance.status = "APPROVED"
        attendance.approved_by = user
        attendance.save()
        return redirect("users:attendance_requests")

    # Other users cannot approve
    return redirect("users:attendance_requests")
