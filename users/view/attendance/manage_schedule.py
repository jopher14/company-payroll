from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from ..utils import isHR
from ...models import Schedule, User


@login_required
@user_passes_test(isHR)
def manage_schedule(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "")

    # Get all employees, optionally filtered by search query
    employees = User.objects.filter(role__in=["employee", "supervisor"])
    if query:
        employees = employees.filter(first_name__icontains=query) | employees.filter(last_name__icontains=query)

    # Prepare a list of employee schedules
    schedules_grouped = []
    for employee in employees:
        # Get all schedules for this employee, ordered by time_in
        schedules = Schedule.objects.filter(employee=employee).order_by("time_in")
        if schedules.exists():
            schedules_grouped.append({
                "employee": employee,
                "schedules": schedules
            })

    context = {
        "schedules_grouped": schedules_grouped
    }
    return render(request, "attendance/manage_schedule.html", context)
