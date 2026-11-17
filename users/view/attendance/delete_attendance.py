from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from ...models import Attendance
from ...decorators import hr_required


@login_required
@hr_required
@require_POST
def delete_attendance(request: HttpRequest, attendance_id=None) -> HttpResponse:
    """Delete attendance record"""
    attendance = get_object_or_404(Attendance, pk=attendance_id)
    attendance.delete()
    messages.success(request, "Attendance deleted successfully.")
    return redirect("users:manage_attendance")
