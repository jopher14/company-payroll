from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from ...models import ManualAttendanceRequest


@login_required
def attendance_requests(request: HttpRequest) -> HttpResponse:
    """
    List manual attendance requests:
    - Pending requests
    - Approved requests
    """

    pending_requests = ManualAttendanceRequest.objects.filter(
        status="PENDING"
    ).select_related("user").order_by("-created_at")

    approved_requests = ManualAttendanceRequest.objects.filter(
        status="APPROVED"
    ).select_related("user").order_by("-created_at")

    context = {
        "pending_requests": pending_requests,
        "approved_requests": approved_requests,
    }

    return render(request, "attendance/attendance_requests.html", context)
