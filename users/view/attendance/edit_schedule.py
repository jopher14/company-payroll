from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from ..utils import isHR
from ...models import Schedule, User
from ...forms import ScheduleForm


@login_required
@user_passes_test(isHR)
def edit_schedule(request: HttpRequest, pk: int) -> HttpResponse:
    employee = get_object_or_404(User, id=pk, role="employee")
    existing_schedule = Schedule.objects.filter(employee=employee).first()

    if request.method == "POST":
        form = ScheduleForm(request.POST, instance=existing_schedule)
        if form.is_valid():
            # Save form instance without committing
            schedule = form.save(commit=False)
            schedule.employee = employee
            schedule.time_in = form.cleaned_data["time_in"]
            schedule.time_out = form.cleaned_data["time_out"]
            schedule.save()  # save before setting ManyToMany

            # Set the selected days
            schedule.days_of_week.set(form.cleaned_data["days_of_week"])

            messages.success(request, f"✅ Schedule for {employee.get_full_name()} updated successfully!")
            return redirect("users:manage_schedule")
    else:
        # Prepare initial data for form
        initial_days = existing_schedule.days_of_week.all() if existing_schedule else []
        initial_time_in = existing_schedule.time_in if existing_schedule else None
        initial_time_out = existing_schedule.time_out if existing_schedule else None

        form = ScheduleForm(instance=existing_schedule, initial={
            "employee": employee,
            "days_of_week": initial_days,
            "time_in": initial_time_in,
            "time_out": initial_time_out,
        })

    return render(request, "attendance/schedule_form.html", {
        "form": form,
        "title": f"Edit Schedule - {employee.get_full_name()}",
    })
