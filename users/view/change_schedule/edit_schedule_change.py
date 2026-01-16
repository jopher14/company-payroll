from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from ...models import ScheduleChangeRequest
from ...forms import ScheduleChangeRequestForm


@login_required
def edit_schedule_change(request: HttpRequest, pk) -> HttpResponse:
    change_request = get_object_or_404(ScheduleChangeRequest, pk=pk)

    # Only allow the employee who created it to edit
    if request.user != change_request.employee:
        return redirect('users:my_pending_schedule_change')

    if request.method == "POST":
        form = ScheduleChangeRequestForm(request.POST, instance=change_request, employee=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Schedule Change request updated successfully!")
            return redirect('users:my_pending_schedule_change')
    else:
        form = ScheduleChangeRequestForm(instance=change_request, employee=request.user)

    return render(request, "attendance/edit_schedule_change.html", {"form": form})
