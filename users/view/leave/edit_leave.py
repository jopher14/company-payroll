from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from ..utils import castUser
from ...models import Leave
from ...forms import LeaveForm


@login_required
def edit_leave(request: HttpRequest, pk) -> HttpResponse:
    user = castUser(request)
    leave = get_object_or_404(Leave, pk=pk, employee=user, status="Pending")

    if request.method == "POST":
        form = LeaveForm(request.POST, instance=leave)
        if form.is_valid():
            updated_leave = form.save(commit=False)

            # ensure employee and status are preserved
            updated_leave.employee = leave.employee
            updated_leave.status = leave.status

            # ✅ Half-day rule
            if updated_leave.leave_type == Leave.HALF_DAY:
                updated_leave.end_date = updated_leave.start_date

            # 🚫 Prevent overlap
            overlapping_leave = Leave.objects.filter(
                employee=user,
                status__in=["Pending", "Approved"],
                start_date__lte=updated_leave.end_date,
                end_date__gte=updated_leave.start_date
            ).exclude(pk=leave.pk).first()

            if overlapping_leave:
                messages.error(
                    request,
                    f"❌ Overlaps with your existing {overlapping_leave.status} leave "
                    f"from {overlapping_leave.start_date:%b %d, %Y} "
                    f"to {overlapping_leave.end_date:%b %d, %Y}."
                )
                return redirect("users:my_leaves")

            updated_leave.save()
            messages.success(request, "✅ Leave request updated successfully.")
            return redirect("users:my_leaves")
    else:
        form = LeaveForm(instance=leave)

    return render(request, "leave/edit_leaves.html", {"form": form, "edit": True, "leave": leave})
