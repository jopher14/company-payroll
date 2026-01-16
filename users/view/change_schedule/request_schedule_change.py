from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.shortcuts import render, redirect
from ..utils import castUser
from ...models import EmployeeSchedule, Schedule, ScheduleChangeRequest
from ...forms import ScheduleChangeRequestForm


@login_required
def request_schedule_change(request: HttpRequest) -> HttpResponse:
    user = castUser(request)

    if request.method == "POST":
        form = ScheduleChangeRequestForm(request.POST, employee=user)
        if form.is_valid():
            change_request = form.save(commit=False)
            change_request.employee = user

            date_obj = form.cleaned_data["date"]
            day_number = date_obj.isoweekday()

            # 1️⃣ Check for a date-specific schedule
            date_schedule = EmployeeSchedule.objects.filter(employee=user, date=date_obj).first()
            if date_schedule:
                change_request.requested_time_in = date_schedule.time_in
                change_request.requested_time_out = date_schedule.time_out
            else:
                # 2️⃣ Fallback to recurring schedule
                recurring_schedule = Schedule.objects.filter(employee=user, days_of_week__in=[day_number]).first()
                change_request.schedule = recurring_schedule
                if recurring_schedule:
                    change_request.requested_time_in = recurring_schedule.time_in
                    change_request.requested_time_out = recurring_schedule.time_out

            change_request.save()
            messages.success(request, "✅ Schedule Change request successfully!")
            return redirect("users:my_pending_schedule_change")
        else:
            print(form.errors)
    else:
        form = ScheduleChangeRequestForm(employee=user)

    # ✅ Fetch pending requests and history based on role
    if user.role == "manager":
        # Manager sees own + all supervisor requests
        pending_requests = ScheduleChangeRequest.objects.filter(
            employee__role__in=["supervisor", "manager"]
        ).order_by("-created_at")
        history = ScheduleChangeRequest.objects.filter(
            employee__role__in=["supervisor", "manager"],
            status__in=["approved", "rejected"]
        ).order_by("-created_at")
    elif user.role == "supervisor":
        # Supervisor sees own + all employee requests
        pending_requests = ScheduleChangeRequest.objects.filter(
            employee__role__in=["employee", "supervisor"]
        ).order_by("-created_at")
        history = ScheduleChangeRequest.objects.filter(
            employee__role__in=["employee", "supervisor"],
            status__in=["approved", "rejected"]
        ).order_by("-created_at")
    else:
        # Employee sees only their own requests
        pending_requests = ScheduleChangeRequest.objects.filter(employee=user).order_by("-created_at")
        history = ScheduleChangeRequest.objects.filter(employee=user, status__in=["approved", "rejected"]).order_by("-created_at")

    context = {
        "form": form,
        "pending_requests": pending_requests,
        "history": history,
    }
    return render(request, "attendance/request_schedule_change.html", context)
