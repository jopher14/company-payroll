from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from ...models import User, Attendance


@login_required
def manage_attendance(request: HttpRequest, attendance_id=None) -> HttpResponse:
    """
    Combined view for add/edit attendance.
    If attendance_id is provided, it's an edit; otherwise, add new.
    """
    attendance = None
    if attendance_id:
        attendance = get_object_or_404(Attendance, pk=attendance_id)

    if request.method == "POST":
        employee_id = request.POST.get("employee")
        date_str = request.POST.get("date")
        time_in_str = request.POST.get("time_in")
        time_out_str = request.POST.get("time_out")
        half_day = request.POST.get("half_day") == "on"

        if not employee_id or not date_str:
            messages.error(request, "Employee and Date are required.")
        else:
            employee = get_object_or_404(User, pk=employee_id)

            # Convert date string to date object
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

            # Convert time strings to time objects, if provided
            time_in_obj = datetime.strptime(time_in_str, "%H:%M").time() if time_in_str else None
            time_out_obj = datetime.strptime(time_out_str, "%H:%M").time() if time_out_str else None

            if attendance:
                # Edit existing record
                attendance.employee = employee
                attendance.date = date_obj
                attendance.time_in = time_in_obj
                attendance.time_out = time_out_obj
                attendance.half_day = half_day
                attendance.save()
                messages.success(request, "Attendance updated successfully.")
            else:
                # Create new record
                Attendance.objects.create(
                    employee=employee,
                    date=date_obj,
                    time_in=time_in_obj,
                    time_out=time_out_obj,
                    half_day=half_day
                )
                messages.success(request, "Attendance added successfully.")

            return redirect("users:manage_attendance")

    # views.py (only changed ordering)
    context = {
        "attendance": attendance,
        "employees": User.objects.filter(is_active=True, is_superuser=False),
        "attendance_list": Attendance.objects.select_related("employee").order_by("employee__last_name", "employee__first_name", "-date"),
    }
    return render(request, "attendance/add_edit_delete_attendance.html", context)
