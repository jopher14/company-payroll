import json
from typing import cast, Any
from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from .forms import AnnouncementForm
from .models import Announcement
from users.models import Attendance, Leave, Schedule, EmployeeSchedule, ScheduleChangeRequest, Overtime
from users.forms import User
from datetime import timedelta, datetime, date
from calendar import monthrange
from django.utils.timezone import localdate
import holidays
from django.db.models import Q
from django.http import JsonResponse


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    # Fetch data for employee
    attendance_logs = Attendance.objects.filter(employee=user)
    leaves = Leave.objects.filter(employee=user, status=Leave.APPROVED)
    schedules = Schedule.objects.filter(employee=user)  # recurring weekly schedules
    date_schedules = EmployeeSchedule.objects.filter(employee=user)  # date-specific schedules
    change_requests = ScheduleChangeRequest.objects.filter(
        employee=user, status__in=["pending", "approved"]
    )
    approved_change_requests = {req.date: req for req in change_requests.filter(status="approved")}

    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')

    events: list[dict[str, Any]] = []

    today = localdate()
    days_in_month = monthrange(today.year, today.month)[1]

    # ✅ Get PH holidays for current and next year
    ph_holidays = holidays.country_holidays("PH", years=[today.year, today.year + 1])

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

        # ✅ Holiday
        if current_date in ph_holidays:
            events.append({
                "title": ph_holidays.get(current_date),
                "start": current_date.isoformat(),
                "color": "purple",
                "tooltip": ph_holidays.get(current_date),
                "allDay": True
            })
            continue

        # ✅ Day Off
        if current_date.weekday() in [5, 6]:
            events.append({
                "title": "Day Off",
                "start": current_date.isoformat(),
                "color": "grey",
                "tooltip": "Day Off",
                "allDay": True
            })
            continue

        # ✅ Approved schedule change
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

        # ✅ Default recurring schedule
        day_number = current_date.isoweekday() % 7 + 1
        recurring_for_day = schedules.filter(days_of_week__number=day_number)
        for sched in recurring_for_day:
            events.append({
                "title": f"{sched.time_in.strftime('%H:%M')} - {sched.time_out.strftime('%H:%M')}",
                "start": current_date.isoformat(),
                "color": "grey",
                "tooltip": "Default HR Schedule",
                "allDay": True
            })

        # ✅ Date-specific schedule
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

        # ✅ Mark Absent (only past or today)
        if current_date <= today:
            if recurring_for_day and current_date not in attended_dates and current_date not in leave_dates:
                events.append({
                    "title": "Absent",
                    "start": current_date.isoformat(),
                    "color": "red",
                    "tooltip": "Absent"
                })

    # ✅ Attendance overrides
    for log in attendance_logs:
        day_str = log.date.isoformat()
        status = log.status

        if status == "Present":
            title, color, tooltip = "Present", "green", "Present"
        elif status == "Late":
            minutes_late = 0
            if log.time_in and log.schedule and log.schedule.time_in:
                minutes_late = (
                    datetime.combine(log.date, log.time_in) -
                    datetime.combine(log.date, log.schedule.time_in)
                ).seconds // 60
            title, color, tooltip = "Late", "red", f"Late {minutes_late}m" if minutes_late else "Late"
        elif status == "Half Day":
            title, color, tooltip = "Half-Day", "orange", "Half-Day"
        elif status == "Absent":
            title, color, tooltip = "Absent", "red", "Absent"
        elif status == "On Leave":
            title, color, tooltip = "Leave", "blue", "On Leave"
        else:
            title, color, tooltip = status, "grey", status

        # ✅ Override if approved half-day leave exists
        half_day_leave = leaves.filter(
            status=Leave.APPROVED,
            leave_type=Leave.HALF_DAY,
            start_date__lte=log.date,
            end_date__gte=log.date
        ).first()

        if half_day_leave:
            title = "Half-Day Leave"
            color = "orange"
            tooltip = f"{log.employee.get_full_name()} - Half-Day Leave"

        events.append({
            "title": title,
            "start": day_str,
            "color": color,
            "tooltip": tooltip
        })

    # ✅ Leave events
    for leave in leaves:
        days = (leave.end_date - leave.start_date).days + 1
        for n in range(days):
            current_date = leave.start_date + timedelta(days=n)
            if current_date in {log.date for log in attendance_logs}:
                continue

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

    # ✅ Pending requests count (filtered by same team)
    pending_leaves_count = 0
    pending_overtimes_count = 0
    pending_schedule_changes_count = 0

    if user.role in ["manager", "supervisor"]:
        # Get all related teams (employee, supervisor, manager)
        user_teams = user.teams.all() | user.supervised_teams.all() | user.managed_teams.all()

        # Filter pending requests from employees in those teams
        team_leaves = Leave.objects.filter(status="Pending", employee__teams__in=user_teams).distinct()
        team_overtimes = Overtime.objects.filter(status="pending", employee__teams__in=user_teams).distinct()
        team_changes = ScheduleChangeRequest.objects.filter(status="pending", employee__teams__in=user_teams).distinct()

        # Supervisor only counts employee requests (not from other supervisors/managers)
        if user.role == "supervisor":
            team_leaves = team_leaves.filter(employee__role="employee").exclude(employee=user)
            team_overtimes = team_overtimes.filter(employee__role="employee").exclude(employee=user)
            team_changes = team_changes.filter(employee__role="employee").exclude(employee=user)

        pending_leaves_count = team_leaves.count()
        pending_overtimes_count = team_overtimes.count()
        pending_schedule_changes_count = team_changes.count()

    elif user.role == "human_resources":
        # HR sees all pending requests
        pending_leaves_count = Leave.objects.filter(status="Pending").count()
        pending_overtimes_count = Overtime.objects.filter(status="pending").count()
        pending_schedule_changes_count = ScheduleChangeRequest.objects.filter(status="pending").count()

    context = {
        "user": user,
        "attendance_events": json.dumps(events),
        "announcement": Announcement.objects.all().order_by("-created_at")[:5],
        "pending_leaves_count": pending_leaves_count,
        "pending_overtimes_count": pending_overtimes_count,
        "pending_schedule_changes_count": pending_schedule_changes_count,
        "accouncements": announcements,
    }

    return render(request, "main/dashboard.html", context)


def is_hr(user):
    return user.role == "human_resources" or user.is_superuser


@login_required
@user_passes_test(is_hr)
def create_announcement(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user

            # ✅ Auto-hide if event date already passed
            if announcement.event_date and announcement.event_date < date.today():
                announcement.is_active = False
            else:
                announcement.is_active = True

            announcement.save()
            return redirect("main:announcement_list")  # redirect to dashboard or announcements list
    else:
        form = AnnouncementForm()

    return render(request, "announcement/create_announcement.html", {"form": form})


@login_required
def announcement_list(request: HttpRequest) -> HttpResponse:
    # ✅ 1. Auto-hide expired announcements
    expired_announcements = Announcement.objects.filter(
        event_date__lt=date.today(),
        is_active=True
    )
    if expired_announcements.exists():
        expired_announcements.update(is_active=False)

    # ✅ 2. Fetch active + valid announcements (upcoming or general)
    announcements = Announcement.objects.filter(
        Q(is_active=True),
        Q(event_date__isnull=True) | Q(event_date__gte=date.today())
    ).order_by('-created_at')

    # ✅ 3. Render dashboard
    return render(request, "main/dashboard.html", {"announcement": announcements})


@login_required
@user_passes_test(is_hr)
def edit_announcement(request: HttpRequest, pk: int) -> HttpResponse:
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == "POST":
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            form.save()
            return redirect("main:dashboard")
    else:
        form = AnnouncementForm(instance=announcement)
    return render(request, "announcement/announcement_edit.html", {"form": form, "announcement": announcement})


@login_required
@user_passes_test(is_hr)
def delete_announcement(request: HttpRequest, pk: int) -> HttpResponse:
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == "POST":
        announcement.delete()
        return redirect("main:dashboard")
    return render(request, "announcement/announcement_confirm_delete.html", {"announcement": announcement})


@login_required
def get_calendar_events(request):
    events = []

    attendances = Attendance.objects.filter(employee=request.user)
    for a in attendances:
        # Example: show "08:00 - 17:00"
        time_display = ""
        if a.time_in and a.time_out:
            time_display = f"{a.time_in.strftime('%H:%M')} - {a.time_out.strftime('%H:%M')}"
        elif a.time_in:
            time_display = f"IN: {a.time_in.strftime('%H:%M')}"
        elif a.time_out:
            time_display = f"OUT: {a.time_out.strftime('%H:%M')}"

        events.append({
            "title": time_display or "No Time Recorded",
            "start": a.date.strftime("%Y-%m-%d"),
            "allDay": True,
            "color": "#3b82f6",  # blue
        })

    return JsonResponse(events, safe=False)
