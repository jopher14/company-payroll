import json
from typing import cast, Any
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from .forms import AnnouncementForm
from .models import Announcement
from users.models import Attendance, Leave, Schedule, EmployeeSchedule, ScheduleChangeRequest
from users.forms import User
from datetime import timedelta
from calendar import monthrange
from django.utils.timezone import localdate


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    # Fetch data
    attendance_logs = Attendance.objects.filter(employee=user)
    leaves = Leave.objects.filter(employee=user, status=Leave.APPROVED)
    schedules = Schedule.objects.filter(employee=user)  # recurring weekly schedules
    date_schedules = EmployeeSchedule.objects.filter(employee=user)  # date-specific schedules
    # Fetch ScheduleChangeRequests for this user (pending or approved)
    change_requests = ScheduleChangeRequest.objects.filter(employee=user, status__in=["pending", "approved"])
    approved_change_requests = change_requests.filter(status="approved")

    events: list[dict[str, Any]] = []

    # Attendance events
    for log in attendance_logs:
        title, color = ("Half-Day", "orange") if not log.time_in or not log.time_out else ("Present", "green")
        events.append({
            "title": title,
            "start": log.date.isoformat(),
            "color": color,
            "tooltip": title
        })

    # Leave events
    for leave in leaves.filter(status=Leave.APPROVED):  # Only approved leaves
        days = (leave.end_date - leave.start_date).days + 1
        for n in range(days):
            current_date = leave.start_date + timedelta(days=n)

            if leave.leave_type == Leave.HALF_DAY:
                title = "Half-Day Leave"
                color = "orange"
            else:
                title = "Whole-Day Leave"
                color = "blue"

            events.append({
                "title": title,
                "start": current_date.isoformat(),
                "color": color,
                "tooltip": f"{leave.employee.get_full_name()} - {title}",
                "allDay": True,
            })

    # Schedule change requests events
    for req in change_requests:
        if req in approved_change_requests:
            color = "green"
        else:
            color = "grey"

        events.append({
            "title": f"{req.requested_time_in.strftime('%H:%M')} - {req.requested_time_out.strftime('%H:%M')}",
            "start": req.date.isoformat(),
            "color": color,   # always green
            "tooltip": "Waiting for approval.",
            "allDay": True
        })

    today = localdate()
    days_in_month = monthrange(today.year, today.month)[1]

    # Recurring weekly schedule weekdays (0=Monday)
    recurring_weekdays = {d.number - 1 for s in schedules for d in s.days_of_week.all()}

    # Dates with attendance or leave
    attended_dates = {log.date for log in attendance_logs} | {
        leave.start_date + timedelta(n)
        for leave in leaves
        for n in range((leave.end_date - leave.start_date).days + 1)
    }

    # Process each day for absences
    for day in range(1, days_in_month + 1):
        current_date = today.replace(day=day)
        if current_date > today:
            continue

        # Day Off
        if current_date.weekday() in [5, 6]:
            events.append({
                "title": "Day Off",
                "start": current_date.isoformat(),
                "color": "gray",
                "tooltip": "Day Off"
            })
            continue

        # Date-specific schedule
        specific_schedule = date_schedules.filter(date=current_date).first()
        if specific_schedule:
            events.append({
                "title": f"{specific_schedule.time_in.strftime('%H:%M')} - {specific_schedule.time_out.strftime('%H:%M')}",
                "start": current_date.isoformat(),
                "color": "grey",
                "tooltip": "Special Schedule",
                "allDay": True
            })
            if current_date not in attended_dates:
                events.append({
                    "title": "Absent",
                    "start": current_date.isoformat(),
                    "color": "red",
                    "tooltip": "Absent"
                })
            continue

        # Recurring schedule absent
        if current_date.weekday() in recurring_weekdays and current_date not in attended_dates:
            events.append({
                "title": "Absent",
                "start": current_date.isoformat(),
                "color": "red",
                "tooltip": "Absent"
            })

    # Add recurring schedules for display
    for sched in schedules:
        for day_obj in sched.days_of_week.all():
            events.append({
                "title": f"{sched.time_in.strftime('%H:%M')} - {sched.time_out.strftime('%H:%M')}",
                "daysOfWeek": [day_obj.number - 1],
                "color": "grey",
                "tooltip": "Recurring Schedule",
                "allDay": True
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
