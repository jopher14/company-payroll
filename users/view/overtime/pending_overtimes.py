from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from ...models import Overtime
from ..utils import castUser


@login_required
def pending_overtimes(request: HttpRequest) -> HttpResponse:
    user = castUser(request)

    if user.role != "supervisor":
        return redirect("main:dashboard")

    # Separate pending and history
    pending_overtimes = Overtime.objects.filter(
        employee__role="employee",
        status="pending"
    )
    history_overtimes = Overtime.objects.filter(
        employee__role="employee"
    ).exclude(status="pending")

    return render(
        request,
        "overtime/pending_overtime.html",
        {
            "pending_overtimes": pending_overtimes,
            "history_overtimes": history_overtimes,
        }
    )
