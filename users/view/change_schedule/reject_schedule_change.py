from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from ..utils import castUser
from ...models import ScheduleChangeRequest


@login_required
def reject_schedule_change(request: HttpRequest, pk) -> HttpResponse:
    user = castUser(request)
    change_request = get_object_or_404(ScheduleChangeRequest, pk=pk)

    if (user.role == "supervisor" and change_request.employee.role == "employee") or \
       (user.role == "manager" and change_request.employee.role == "supervisor"):

        change_request.status = "rejected"
        change_request.approved_by = user
        change_request.save()

    return redirect('users:pending_schedule_changes')
