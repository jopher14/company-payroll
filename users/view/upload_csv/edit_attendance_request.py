from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from ...models import ManualAttendanceRequest
from ...forms import ManualAttendanceForm


@login_required
def edit_attendance_request(request: HttpRequest, request_id: int) -> HttpResponse:
    attendance = get_object_or_404(
        ManualAttendanceRequest,
        id=request_id,
        user=request.user,
        status="PENDING"
    )

    if request.method == "POST":
        form = ManualAttendanceForm(request.POST, instance=attendance)
        if form.is_valid():
            form.save()
            return redirect("users:attendance_requests")
    else:
        form = ManualAttendanceForm(instance=attendance)

    return render(request, "attendance/manual_attendance_edit.html", {
        "form": form,
        "is_edit": True
    })
