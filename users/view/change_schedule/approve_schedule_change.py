from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from ...models import ScheduleChangeRequest, EmployeeSchedule
from ..utils import castUser


@login_required
def approve_schedule_change(request: HttpRequest, pk: int) -> HttpResponse:
    user = castUser(request)
    change_request = get_object_or_404(ScheduleChangeRequest, pk=pk)

    # Only supervisors can approve employees, managers can approve supervisors
    if (user.role == "supervisor" and change_request.employee.role == "employee") or \
       (user.role == "manager" and change_request.employee.role == "supervisor"):

        # Approve the request
        change_request.status = "approved"
        change_request.approved_by = user
        change_request.save()

        # Update or create schedule only for the requested date
        EmployeeSchedule.objects.update_or_create(
            employee=change_request.employee,
            date=change_request.date,
            defaults={
                "time_in": change_request.requested_time_in,
                "time_out": change_request.requested_time_out
            }
        )

    return redirect('users:pending_schedule_changes')
