from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from ...models import Overtime
from ..utils import castUser


@login_required
def overtime_list(request: HttpRequest) -> HttpResponse:
    user = castUser(request)

    if user.role == "employee":
        # Employee sees their own requests
        overtime = Overtime.objects.filter(employee=user, status="pending").order_by("-date")
        history_overtime = Overtime.objects.filter(employee=user).exclude(status="pending").order_by("-date")

    elif user.role == "supervisor":
        # Supervisor sees pending requests from their team (employees)
        overtime = Overtime.objects.filter(employee__role="employee", status="pending").order_by("-date")
        # History shows only supervisor's own reviewed requests
        history_overtime = Overtime.objects.filter(employee=user).exclude(status="pending").order_by("-date")

    elif user.role == "manager":
        # Manager sees pending requests from both employees and supervisors
        overtime = Overtime.objects.filter(employee__role__in=["employee", "supervisor"], status="pending").order_by("-date")
        # History shows approved/rejected requests from employees and supervisors
        history_overtime = Overtime.objects.filter(employee__role__in=["employee", "supervisor"]).exclude(status="pending").order_by("-date")

    else:
        messages.error(request, "You are not allowed to view overtime requests.")
        return redirect("main:dashboard")

    context = {
        "overtime": overtime,
        "history_overtime": history_overtime,
    }
    return render(request, "overtime/overtime_list.html", context)
