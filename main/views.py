import json
from typing import cast
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from .forms import AnnouncementForm
from .models import Announcement
from users.models import Attendance
from users.forms import User


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)
    attendance = Attendance.objects.filter(employee=user).order_by('-date')

    # Build calendar events
    attendance_events = []
    for att in attendance:
        if att.status == "Present":
            color = "#28a745"  # green
        elif att.status == "Absent":
            color = "#dc3545"  # red
        else:
            color = "#ffc107"  # yellow

        attendance_events.append({
            "title": att.status,
            "start": att.date.strftime("%Y-%m-%d"),
            "color": color,
        })

    return render(request, "main/dashboard.html", {
        "attendance": attendance,
        "attendance_events": json.dumps(attendance_events),  # pass as JSON
    })


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
