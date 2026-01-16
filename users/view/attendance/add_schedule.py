from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.shortcuts import render, redirect
from ..utils import isHR
from ...forms import ScheduleForm


@login_required
@user_passes_test(isHR)
def add_schedule(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ScheduleForm(request.POST)
        if form.is_valid():
            # Save the form instance without committing to handle ManyToManyField
            schedule = form.save(commit=False)
            schedule.employee = form.cleaned_data["employee"]
            schedule.time_in = form.cleaned_data["time_in"]
            schedule.time_out = form.cleaned_data["time_out"]
            schedule.save()  # must save before setting ManyToManyField

            # Set the selected days
            schedule.days_of_week.set(form.cleaned_data["days_of_week"])

            # Success message
            messages.success(request, f"✅ Schedule for {schedule.employee.get_full_name()} saved successfully!")

            return redirect("users:manage_schedule")
    else:
        form = ScheduleForm()

    return render(request, "attendance/schedule_form.html", {
        "form": form,
        "title": "Add Schedule"
    })
