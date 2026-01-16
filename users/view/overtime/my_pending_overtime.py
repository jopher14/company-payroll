from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from ...models import Overtime
from ..utils import castUser


@login_required
def my_pending_overtime(request: HttpRequest) -> HttpResponse:
    user = castUser(request)

    # Pending requests
    pending_overtime = Overtime.objects.filter(employee=user, status="pending").order_by("-date")

    # History (approved or rejected)
    history_overtime = Overtime.objects.filter(employee=user).exclude(status="pending").order_by("-date")

    context = {
        "pending_overtime": pending_overtime,
        "history_overtime": history_overtime,
    }

    return render(request, "overtime/my_pending_overtime.html", context)
