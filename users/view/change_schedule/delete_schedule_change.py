from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from ...models import ScheduleChangeRequest


@login_required
def delete_schedule_change(request: HttpRequest, pk: int) -> HttpResponse:
    change_request = get_object_or_404(ScheduleChangeRequest, pk=pk)

    # Only the request owner can delete
    if request.user != change_request.employee:
        messages.error(request, "You are not allowed to delete this request.")
        return redirect("users:my_pending_schedule_change")

    if request.method == "POST":
        change_request.delete()
        messages.success(request, "Schedule change request deleted successfully.")
        return redirect("users:my_pending_schedule_change")

    # Render confirmation page
    return render(
        request,
        "attendance/delete_schedule_change_confirm.html",
        {"object": change_request}  # standard Django naming for DeleteView compatibility
    )
