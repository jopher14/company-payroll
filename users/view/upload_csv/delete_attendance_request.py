from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from ...models import ManualAttendanceRequest


@login_required
def delete_attendance_request(request: HttpRequest, request_id: int) -> HttpResponse:
    attendance = get_object_or_404(
        ManualAttendanceRequest,
        id=request_id,
        user=request.user,
        status="PENDING"
    )

    if request.method == "POST":
        attendance.delete()

    return redirect("users:attendance_requests")
