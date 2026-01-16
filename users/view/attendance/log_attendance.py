from typing import Optional
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.utils.timezone import localdate, localtime, now
from datetime import time
from ...models import User, ScheduleChangeRequest, EmployeeSchedule, Schedule, Attendance


@login_required
def log_attendance(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        return HttpResponse("Invalid user", status=400)

    today = localdate()
    current_time = localtime(now())

    # ✅ Check for an approved schedule change for today
    approved_request = ScheduleChangeRequest.objects.filter(
        employee=user,
        date=today,
        status="approved"
    ).first()

    schedule_in: Optional[time] = None
    schedule_out: Optional[time] = None
    if approved_request:
        # Use the approved change schedule
        schedule_in = approved_request.requested_time_in
        schedule_out = approved_request.requested_time_out
    else:
        # Fall back to HR’s default schedule (recurring or date-specific)
        schedule = EmployeeSchedule.objects.filter(employee=user, date=today).first()
        if schedule:
            schedule_in, schedule_out = schedule.time_in, schedule.time_out
        else:
            default_schedule = Schedule.objects.filter(employee=user).first()
            schedule_in = default_schedule.time_in if default_schedule else None
            schedule_out = default_schedule.time_out if default_schedule else None

    # Get or create attendance record for today
    attendance, created = Attendance.objects.get_or_create(
        employee=user,
        date=today,
    )

    if request.method == "POST":
        if not attendance.time_in:
            attendance.time_in = current_time
        elif not attendance.time_out:
            attendance.time_out = current_time
        attendance.save()
        return redirect("users:log_attendance")

    return render(request, "attendance/log_attendance.html", {
        "attendance": attendance,
        "schedule_in": schedule_in,
        "schedule_out": schedule_out,
        "current_time": current_time,
    })
