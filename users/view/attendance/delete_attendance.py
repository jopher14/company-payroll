from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from ...models import Attendance


@login_required
def delete_attendance(request: HttpRequest, attendance_id=None) -> HttpResponse:
    """Delete attendance record"""
    attendance = get_object_or_404(Attendance, pk=attendance_id)
    attendance.delete()
    messages.success(request, "Attendance deleted successfully.")
    return redirect("users:manage_attendance")
