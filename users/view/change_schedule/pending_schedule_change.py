from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from ..utils import castUser
from ...models import ScheduleChangeRequest


@login_required
def pending_schedule_change(request: HttpRequest) -> HttpResponse:
    user = castUser(request)

    # Pending requests
    if user.role == "employee":
        # Employees see only their own pending requests
        approval_requests = ScheduleChangeRequest.objects.filter(employee=user, status="pending")
    elif user.role == "supervisor":
        # Supervisors see pending requests from employees
        approval_requests = ScheduleChangeRequest.objects.filter(employee__role="employee", status="pending")
    elif user.role == "manager":
        # Managers see pending requests from both supervisors and employees
        approval_requests = ScheduleChangeRequest.objects.filter(
            employee__role__in=["employee", "supervisor"],
            status="pending"
        )
    else:
        approval_requests = ScheduleChangeRequest.objects.none()

    # History of approved/rejected requests
    if user.role in ["employee", "supervisor"]:
        # Employee and supervisor see only their own history
        history = ScheduleChangeRequest.objects.filter(
            employee=user,
            status__in=["approved", "rejected"]
        ).order_by('-created_at')
    elif user.role == "manager":
        # Manager sees history of both employees and supervisors
        history = ScheduleChangeRequest.objects.filter(
            employee__role__in=["employee", "supervisor"],
            status__in=["approved", "rejected"]
        ).order_by('-created_at')
    else:
        history = ScheduleChangeRequest.objects.none()

    context = {
        "user": user,
        "approval_requests": approval_requests,
        "history": history,
    }
    return render(request, "attendance/pending_schedule_changes.html", context)
