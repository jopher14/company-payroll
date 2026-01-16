from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from ..utils import castUser
from ...models import Leave
from ...forms import LeaveForm


@login_required
def file_leave(request: HttpRequest) -> HttpResponse:
    user = castUser(request)

    if request.method == "POST":
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = user

            # ✅ Validate leave_type
            if leave.leave_type not in dict(Leave.LEAVE_TYPE_CHOICES):
                messages.error(request, "Invalid leave type selected.")
                return redirect("users:file_leave")

            # ✅ Half-day: force end_date = start_date
            if leave.leave_type == Leave.HALF_DAY:
                leave.end_date = leave.start_date

            # 🚫 Prevent duplicate/overlap if Pending or Approved
            overlapping_leave = Leave.objects.filter(
                employee=user,
                status__in=["Pending", "Approved"],
                start_date__lte=leave.end_date,
                end_date__gte=leave.start_date
            ).first()

            if overlapping_leave:
                messages.error(
                    request,
                    f"❌ Overlaps with your existing {overlapping_leave.status} leave "
                    f"from {overlapping_leave.start_date.strftime('%b %d, %Y')} "
                    f"to {overlapping_leave.end_date.strftime('%b %d, %Y')}."
                )
                return redirect("users:my_leaves")

            leave.save()
            messages.success(request, "✅ Leave request submitted successfully.")
            return redirect("users:my_leaves")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LeaveForm()

    return render(request, "leave/file_leave.html", {"form": form})
