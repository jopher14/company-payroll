import json
from typing import cast
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from .forms import AnnouncementForm
from .models import Announcement
from users.models import Attendance, Leave, Schedule
from users.forms import User
from datetime import timedelta
from calendar import monthrange
from django.utils.timezone import localdate


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    attendance_logs = Attendance.objects.filter(employee=user)
    leaves = Leave.objects.filter(employee=user, status=Leave.APPROVED)
    schedules = Schedule.objects.filter(employee=user)

    events = []

    # Attendance events
    for log in attendance_logs:
        if not log.time_in or not log.time_out:
            title, color = "Half-Day", "orange"
        else:
            title, color = "Present", "green"

        events.append({
            "title": title,
            "start": log.date.isoformat(),
            "color": color
        })

    # Leave events
    for leave in leaves:
        events.append({
            "title": "Leave",
            "start": leave.start_date.isoformat(),
            "end": (leave.end_date + timedelta(days=1)).isoformat(),
            "color": "blue"
        })

    # Absent / Day Off logic
    today = localdate()
    days_in_month = monthrange(today.year, today.month)[1]

    scheduled_days = {d.number - 1 for s in schedules for d in s.days_of_week.all()}
    attended_dates = {log.date for log in attendance_logs} | {
        leave.start_date + timedelta(n)
        for leave in leaves
        for n in range((leave.end_date - leave.start_date).days + 1)
    }

    for day in range(1, days_in_month + 1):
        date = today.replace(day=day)

        # Skip future dates
        if date > today:
            continue

        # Day Off for weekends
        if date.weekday() in [5, 6]:  # Saturday=5, Sunday=6
            events.append({
                "title": "Day Off",
                "start": date.isoformat(),
                "color": "gray"
            })
            continue

        # Absent if scheduled and no attendance/leave
        if date.weekday() in scheduled_days and date not in attended_dates:
            events.append({
                "title": "Absent",
                "start": date.isoformat(),
                "color": "red"
            })

    # Schedule recurring events
    for sched in schedules:
        for day_obj in sched.days_of_week.all():
            events.append({
                "title": f"Schedule ({day_obj.name})",
                "daysOfWeek": str([day_obj.number - 1]),
                "startTime": sched.time_in.strftime("%H:%M"),
                "endTime": sched.time_out.strftime("%H:%M"),
                "color": "purple"
            })

    context = {
        "user": user,
        "attendance_events": json.dumps(events),
        "announcement": Announcement.objects.all().order_by("-created_at")[:5],
    }
    return render(request, "main/dashboard.html", context)


def is_hr(user):
    return user.role == "human_resources" or user.is_superuser


@login_required
@user_passes_test(is_hr)
def create_announcement(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()
            return redirect("main:announcement_list")  # redirect to dashboard or announcements list
    else:
        form = AnnouncementForm()
    return render(request, "announcement/create_announcement.html", {"form": form})


@login_required
def announcement_list(request: HttpRequest) -> HttpResponse:
    announcements = Announcement.objects.filter(is_active=True).order_by("-created_at")
    return render(request, "announcement/announcement_list.html", {"announcements": announcements})
