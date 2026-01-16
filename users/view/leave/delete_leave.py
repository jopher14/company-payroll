from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from ...models import Leave


@login_required
def delete_leave(request: HttpRequest, pk) -> HttpResponse:
    try:
        leave = get_object_or_404(Leave, pk=pk, employee=request.user, status="Pending")
    except Leave.DoesNotExist:
        messages.error(request, "❌ You can only delete pending leave requests.")
        return redirect("users:my_leaves")

    if request.method == "POST":
        leave.delete()
        messages.success(request, "✅ Leave request deleted successfully.")
        return redirect("users:my_leaves")

    return render(request, "leave/delete_leaves.html", {"leave": leave})
