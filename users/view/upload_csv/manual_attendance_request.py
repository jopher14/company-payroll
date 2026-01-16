from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from ...forms import ManualAttendanceForm


@login_required
def manual_attendance_request(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ManualAttendanceForm(request.POST)
        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.user = request.user
            attendance.save()
            return redirect("users:attendance_requests")
    else:
        form = ManualAttendanceForm()

    return render(request, "attendance/manual_request.html", {"form": form})
