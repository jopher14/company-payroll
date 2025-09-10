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
    change_requests = ScheduleChangeRequest.objects.filter(employee=user, status__in=["pending", "approved"])
    approved_change_requests = {req.date: req for req in change_requests.filter(status="approved")}

    events: list[dict[str, Any]] = []

    today = localdate()
    days_in_month = monthrange(today.year, today.month)[1]

    # Dates with attendance or leave
    attended_dates = {log.date for log in attendance_logs}
    leave_dates = {
        leave.start_date + timedelta(n)
        for leave in leaves
        for n in range((leave.end_date - leave.start_date).days + 1)
    }

    # 🚀 Build schedule for each day in the current month
    for day in range(1, days_in_month + 1):
        current_date = today.replace(day=day)

        # Day Off (Saturday & Sunday)
        if current_date.weekday() in [5, 6]:
            events.append({
                "title": "Day Off",
                "start": current_date.isoformat(),
                "color": "grey",
                "tooltip": "Day Off",
                "allDay": True
            })
            continue

        # ✅ Approved schedule change (Green)
        if current_date in approved_change_requests:
            req = approved_change_requests[current_date]
            events.append({
                "title": f"{req.requested_time_in.strftime('%H:%M')} - {req.requested_time_out.strftime('%H:%M')}",
                "start": current_date.isoformat(),
                "color": "green",
                "tooltip": "Approved Schedule Change",
                "allDay": True
            })
            continue

        # ✅ Otherwise: show recurring HR default schedule in grey
        day_number = current_date.isoweekday() % 7 + 1  # Mon=2, Tue=3, ..., Sun=1
        recurring_for_day = schedules.filter(days_of_week__number=day_number)
        for sched in recurring_for_day:
            events.append({
                "title": f"{sched.time_in.strftime('%H:%M')} - {sched.time_out.strftime('%H:%M')}",
                "start": current_date.isoformat(),
                "color": "grey",
                "tooltip": "Default HR Schedule",
                "allDay": True
            })

        # ✅ Date-specific schedule from HR (Grey)
        specific_schedule = date_schedules.filter(date=current_date).first()
        if specific_schedule:
            events.append({
                "title": f"{specific_schedule.time_in.strftime('%H:%M')} - {specific_schedule.time_out.strftime('%H:%M')}",
                "start": current_date.isoformat(),
                "color": "grey",
                "tooltip": "Special HR Schedule",
                "allDay": True
            })
            continue

        # Mark Absent if no attendance/leave (only for past & today)
        if current_date <= today:
            if recurring_for_day and current_date not in attended_dates and current_date not in leave_dates:
                events.append({
                    "title": "Absent",
                    "start": current_date.isoformat(),
                    "color": "red",
                    "tooltip": "Absent"
                })

    # ✅ Attendance overrides (Green/Orange)
    for log in attendance_logs:
        if log.time_in and log.time_out:
            events.append({
                "title": "Present",
                "start": log.date.isoformat(),
                "color": "green",
                "tooltip": "Present"
            })
        else:
            events.append({
                "title": "Half-Day",
                "start": log.date.isoformat(),
                "color": "orange",
                "tooltip": "Half-Day"
            })

    # ✅ Leave events
    for leave in leaves:
        days = (leave.end_date - leave.start_date).days + 1
        for n in range(days):
            current_date = leave.start_date + timedelta(days=n)

            if leave.leave_type == Leave.HALF_DAY:
                title, color = "Half-Day Leave", "orange"
            else:
                title, color = "Whole-Day Leave", "blue"

            events.append({
                "title": title,
                "start": current_date.isoformat(),
                "color": color,
                "tooltip": f"{leave.employee.get_full_name()} - {title}",
                "allDay": True,
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
