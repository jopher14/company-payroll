from typing import cast, Any, Optional
from datetime import time
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import User, Leave, Attendance, Schedule, Overtime, ScheduleChangeRequest, EmployeeSchedule
from django.http import HttpResponse, HttpRequest
from .forms import LeaveForm, ScheduleForm, EmployeeUpdateForm, OvertimeForm, UserRegistrationForm, ScheduleChangeRequestForm
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.utils.timezone import now, localtime
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.timezone import localdate


@login_required
def manager_dashboard(request: HttpRequest) -> HttpResponse:
    # Tell mypy that request.user is your User model
    user = request.user
    if not isinstance(user, User):
        return HttpResponseForbidden("You are not allowed to access this page.")

    if user.role != User.MANAGER:
        return HttpResponseForbidden("You are not allowed to access this page.")

    return render(request, "manager_dashboard.html", {"user": user})


@login_required
def register(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User: {user.username} registered successfully!")
            return redirect("users:employee_list")
    else:
        form = UserRegistrationForm()
    return render(request, "users/register.html", {"form": form})


def loginView(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("main:dashboard")
        else:
            messages.error(request, "Invalid credentials. Please try again.")
    else:
        form = AuthenticationForm()

    return render(request, "users/login.html", {"form": form})


def logoutView(request: HttpRequest) -> HttpResponse:
    logout(request)
    return render(request, 'users/logout.html')


@login_required
def employee_list(request: HttpRequest) -> HttpResponse:
    employees = User.objects.filter(is_superuser=False)  # only employees and exclude the super user
    return render(request, "users/employee_list.html", {"employees": employees})


# --- EMPLOYEE ---
@login_required
def file_leave(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    if request.method == "POST":
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = user

            # Ensure leave_type is valid
            if leave.leave_type not in dict(Leave.LEAVE_TYPE_CHOICES):
                messages.error(request, "Invalid leave type selected.")
                return redirect("users:file_leave")

            # Auto-set end_date for half-day leaves (same as start_date)
            if leave.leave_type == Leave.HALF_DAY:
                leave.end_date = leave.start_date

            leave.save()
            messages.success(request, "Leave request submitted successfully.")
            return redirect("users:my_leaves")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LeaveForm()

    return render(request, "leave/file_leave.html", {"form": form})


@login_required
def my_leaves(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        # This should never happen because of @login_required
        return HttpResponse("Invalid user", status=400)

    # Now mypy knows `user` is a User
    leaves = Leave.objects.filter(employee=user).order_by("-created_at")
    return render(request, "leave/my_leaves.html", {"leaves": leaves})


@login_required
def edit_leave(request: HttpRequest, pk) -> HttpResponse:
    leave = get_object_or_404(Leave, pk=pk, employee=request.user, status="pending")
    if request.method == "POST":
        form = LeaveForm(request.POST, instance=leave)
        if form.is_valid():
            form.save()
            return redirect("my_leaves")
    else:
        form = LeaveForm(instance=leave)
    return render(request, "leave/file_leave.html", {"form": form, "edit": True})


@login_required
def delete_leave(request: HttpRequest, pk) -> HttpResponse:
    leave = get_object_or_404(Leave, pk=pk, employee=request.user, status="pending")
    if request.method == "POST":
        leave.delete()
        return redirect("my_leaves")
    return render(request, "leave/delete_leave.html", {"leave": leave})


# --- SUPERVISOR ---
def is_supervisor(user):
    return user.role == "supervisor" or user.is_superuser


@login_required
def pending_leaves(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    if user.role == "manager":
        # Manager sees supervisor + employee requests
        leaves = Leave.objects.filter(
            employee__role__in=["supervisor", "employee"], status="pending"
        )
    elif user.role == "supervisor":
        # Supervisor sees employee requests
        leaves = Leave.objects.filter(
            employee__role="employee", status="pending"
        )
    else:
        # Employees only see their own leave requests
        leaves = Leave.objects.filter(employee=user)

    return render(request, "leave/pending_leaves.html", {"leaves": leaves})


@login_required
def process_leave(request: HttpRequest, pk: int, action: str) -> HttpResponse:
    """
    Process a leave request (approve or reject).
    """
    leave = get_object_or_404(Leave, pk=pk)
    reviewer = request.user

    if not isinstance(reviewer, User):
        return HttpResponse("Invalid user", status=400)

    # ✅ Approval hierarchy rules
    if leave.employee.role == "employee" and reviewer.role != "supervisor":
        return HttpResponse("Only supervisors can process employee leaves.", status=403)

    if leave.employee.role == "supervisor" and reviewer.role != "manager":
        return HttpResponse("Only managers can process supervisor leaves.", status=403)

    if leave.status != Leave.PENDING:
        messages.warning(request, "This leave request has already been processed.")
    else:
        if action == "approve":
            leave.status = Leave.APPROVED
            action_msg = "approved"
        elif action == "reject":
            leave.status = Leave.REJECTED
            action_msg = "rejected"
        else:
            return HttpResponse("Invalid action", status=400)

        leave.reviewed_by = reviewer
        leave.reviewed_at = now()
        leave.save()

        messages.success(
            request,
            f"Leave for {leave.employee.get_full_name() or leave.employee.username} {action_msg}."
        )

    return redirect("users:pending_leaves")


# ✅ Shortcut wrappers for URLs
@login_required
def approve_leave(request: HttpRequest, pk: int) -> HttpResponse:
    return process_leave(request, pk, "approve")


@login_required
def reject_leave(request: HttpRequest, pk: int) -> HttpResponse:
    return process_leave(request, pk, "reject")


# --- MANAGER ---
def is_manager(user):
    return user.role == "manager" or user.is_superuser


@login_required
def log_attendance(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        return HttpResponse("Invalid user", status=400)

    today = localdate()
    current_time = localtime(now())

    # ✅ Check for an approved schedule change for today
    approved_request = ScheduleChangeRequest.objects.filter(
        employee=user,
        date=today,
        status="approved"
    ).first()

    schedule_in: Optional[time] = None
    schedule_out: Optional[time] = None
    if approved_request:
        # Use the approved change schedule
        schedule_in = approved_request.requested_time_in
        schedule_out = approved_request.requested_time_out
    else:
        # Fall back to HR’s default schedule (recurring or date-specific)
        schedule = EmployeeSchedule.objects.filter(employee=user, date=today).first()
        if schedule:
            schedule_in, schedule_out = schedule.time_in, schedule.time_out
        else:
            default_schedule = Schedule.objects.filter(employee=user).first()
            schedule_in = default_schedule.time_in if default_schedule else None
            schedule_out = default_schedule.time_out if default_schedule else None

    # Get or create attendance record for today
    attendance, created = Attendance.objects.get_or_create(
        employee=user,
        date=today,
    )

    if request.method == "POST":
        if not attendance.time_in:
            attendance.time_in = current_time
        elif not attendance.time_out:
            attendance.time_out = current_time
        attendance.save()
        return redirect("users:log_attendance")

    return render(request, "attendance/log_attendance.html", {
        "attendance": attendance,
        "schedule_in": schedule_in,
        "schedule_out": schedule_out,
        "current_time": current_time,
    })


@login_required
def attendance_list(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        return HttpResponse("Invalid user", status=400)

    if user.role == "manager":
        attendances = Attendance.objects.select_related("employee").filter(
            employee__role__in=["supervisor", "employee"]
        ).order_by("-date")
    else:
        attendances = Attendance.objects.filter(
            employee=user,
            employee__role__in=["supervisor", "employee"]
        ).select_related("employee").order_by("-date")

    # Pagination (5 per page)
    paginator = Paginator(attendances, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # ✅ Add late/undertime flags for template
    for att in page_obj:
        att = cast(Any, att)
        schedule = att.employee.schedule.first() if hasattr(att.employee, "schedule") else None
        att.is_late = False
        att.is_undertime = False

        if schedule:
            if att.time_in and att.time_in > schedule.time_in:
                att.is_late = True
            if att.time_out and att.time_out < schedule.time_out:
                att.is_undertime = True

    return render(request, "attendance/attendance_list.html", {
        "page_obj": page_obj,
    })


# --- HR ---
def is_hr(user):
    return user.role == "human_resources" or user.is_superuser


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.role == "human_resources")
def manage_schedule(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "")

    # Get all employees, optionally filtered by search query
    employees = User.objects.filter(role__in=["employee", "supervisor"])
    if query:
        employees = employees.filter(first_name__icontains=query) | employees.filter(last_name__icontains=query)

    # Prepare a list of employee schedules
    schedules_grouped = []
    for employee in employees:
        # Get all schedules for this employee, ordered by time_in
        schedules = Schedule.objects.filter(employee=employee).order_by("time_in")
        if schedules.exists():
            schedules_grouped.append({
                "employee": employee,
                "schedules": schedules
            })

    context = {
        "schedules_grouped": schedules_grouped
    }
    return render(request, "attendance/manage_schedule.html", context)


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.role == "human_resources")
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


@login_required
@user_passes_test(is_hr)
def edit_schedule(request, pk):
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


@login_required
@user_passes_test(is_hr)
def update_employee(request: HttpRequest, pk) -> HttpResponse:
    employee = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        form = EmployeeUpdateForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            return redirect('users:employee_list')
    else:
        form = EmployeeUpdateForm(instance=employee)

    return render(request, 'users/update_employee.html', {
        'form': form,
        'employee': employee
    })


@login_required
@user_passes_test(is_hr)
def delete_employee(request: HttpRequest, pk) -> HttpResponse:
    employee = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        employee.delete()
        messages.success(request, "Employee deleted successfully.")
        return redirect("users:employee_list")

    messages.error(request, "Invalid request.")
    return redirect("users:employee_list")


@login_required
def overtime_list(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    if user.role == "employee":
        # Employee sees their own requests
        overtime = Overtime.objects.filter(employee=user, status="pending").order_by("-date")
        history_overtime = Overtime.objects.filter(employee=user).exclude(status="pending").order_by("-date")

    elif user.role == "supervisor":
        # Supervisor sees pending requests of their team (optional)
        # and only their reviewed requests in history
        overtime = Overtime.objects.filter(status="pending").order_by("-date")  # all pending
        history_overtime = Overtime.objects.filter(reviewed_by=user).exclude(status="pending").order_by("-date")

    else:
        messages.error(request, "You are not allowed to view overtime requests.")
        return redirect("main:dashboard")

    context = {
        "overtime": overtime,
        "history_overtime": history_overtime,
    }
    return render(request, "overtime/overtime_list.html", context)


@login_required
def overtime_request(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        # Should never happen because of @login_required
        return HttpResponse("Invalid user", status=400)

    # 🚫 Restrict to Supervisor & Employee only
    if user.role not in ["supervisor", "employee"]:
        messages.error(request, "You are not allowed to file overtime requests.")
        return redirect("users:overtime_list")

    if request.method == "POST":
        form = OvertimeForm(request.POST)
        if form.is_valid():
            overtime = form.save(commit=False)
            overtime.employee = user

            # ✅ Calculate hours safely in backend if time_in/out provided
            date = form.cleaned_data.get("date")
            time_in = form.cleaned_data.get("time_in")
            time_out = form.cleaned_data.get("time_out")

            if date and time_in and time_out:
                start_dt = datetime.combine(date, time_in)
                end_dt = datetime.combine(date, time_out)

                # Handle overnight shifts (e.g. 10PM → 2AM)
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)

                diff = end_dt - start_dt
                overtime.hours = round(diff.total_seconds() / 3600, 2)  # store as decimal hours

            # Overtime type comes directly from the form (default = ordinary)
            overtime.overtime_type = form.cleaned_data.get("overtime_type", "ordinary")

            overtime.save()
            messages.success(request, "✅ Overtime request submitted successfully!")
            return redirect("users:overtime_list")
    else:
        form = OvertimeForm()

    return render(request, "overtime/overtime_request.html", {"form": form})


@login_required
def overtime_approve(request: HttpRequest, pk) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        return HttpResponse("Invalid user", status=400)

    overtime = get_object_or_404(Overtime, pk=pk)

    # Approval logic
    if overtime.employee.role == "employee":
        if user.role in ["supervisor", "manager"]:
            overtime.status = "approved"
            overtime.reviewed_by = user
            overtime.save()
            messages.success(request, "Overtime approved successfully ✅")
        else:
            messages.error(request, "You are not authorized to approve this request ❌")

    elif overtime.employee.role == "supervisor":
        if user.role == "manager":
            overtime.status = "approved"
            overtime.reviewed_by = user
            overtime.save()
            messages.success(request, "Overtime approved successfully ✅")
        else:
            messages.error(request, "You are not authorized to approve this request ❌")

    elif overtime.employee.role == "manager":
        messages.error(request, "Manager's overtime cannot be approved ❌")

    return redirect("users:overtime_list")


@login_required
def overtime_reject(request: HttpRequest, pk) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        return HttpResponse("Invalid user", status=400)

    overtime = get_object_or_404(Overtime, pk=pk)

    # Rejection logic
    if overtime.employee.role == "employee":
        if user.role in ["supervisor", "manager"]:
            overtime.status = "rejected"
            overtime.reviewed_by = user
            overtime.save()
            messages.warning(request, "Overtime rejected ❌")
        else:
            messages.error(request, "You are not authorized to reject this request ❌")

    elif overtime.employee.role == "supervisor":
        if user.role == "manager":
            overtime.status = "rejected"
            overtime.reviewed_by = user
            overtime.save()
            messages.warning(request, "Overtime rejected ❌")
        else:
            messages.error(request, "You are not authorized to reject this request ❌")

    elif overtime.employee.role == "manager":
        messages.error(request, "Manager's overtime cannot be rejected ❌")

    return redirect("users:overtime_list")


@login_required
def overtime_action(request: HttpRequest, pk, action) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        # Should never happen due to @login_required
        return HttpResponse("Invalid user", status=400)

    overtime = get_object_or_404(Overtime, pk=pk)

    # Only supervisors should be allowed
    if user.role != "supervisor":
        messages.error(request, "You are not authorized to perform this action.")
        return redirect("users:overtime_list")

    if action == "approve":
        overtime.status = "approved"
        overtime.reviewed_by = user  # ✅ assign to the correct field
        overtime.save()
        messages.success(
            request,
            f"Overtime request from {overtime.employee.first_name} approved ✅"
        )
    elif action == "reject":
        overtime.status = "rejected"
        overtime.reviewed_by = user  # ✅ assign to the correct field
        overtime.save()
        messages.warning(
            request,
            f"Overtime request from {overtime.employee.first_name} rejected ❌"
        )
    else:
        messages.error(request, "Invalid action.")

    return redirect("users:overtime_list")


@login_required
def pending_overtimes(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        # Should never happen due to @login_required
        return HttpResponse("Invalid user", status=400)

    if user.role != "supervisor":
        return redirect("main:dashboard")

    pending_overtimes = Overtime.objects.filter(status="pending")
    return render(
        request,
        "overtime/pending_overtime.html",
        {"pending_overtimes": pending_overtimes}
    )


@login_required
def overtime_edit(request: HttpRequest, pk) -> HttpResponse:
    overtime = get_object_or_404(Overtime, pk=pk, employee=request.user)

    if overtime.status != "pending":
        messages.error(request, "You can only edit pending requests.")
        return redirect("users:overtime_list")

    if request.method == "POST":
        form = OvertimeForm(request.POST, instance=overtime)
        if form.is_valid():
            form.save()
            messages.success(request, "Overtime request updated successfully.")
            return redirect("users:overtime_list")
    else:
        form = OvertimeForm(instance=overtime)

    return render(request, "overtime/overtime_request.html", {"form": form})


@login_required
def overtime_delete(request: HttpRequest, pk) -> HttpResponse:
    overtime = get_object_or_404(Overtime, pk=pk, employee=request.user)

    if overtime.status != "pending":
        messages.error(request, "You can only delete pending requests.")
        return redirect("users:overtime_list")

    if request.method == "POST":
        overtime.delete()
        messages.success(request, "Overtime request deleted successfully.")
        return redirect("users:overtime_list")

    return render(request, "overtime/overtime_confirm_delete.html", {"overtime": overtime})


@login_required
def request_schedule_change(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    if request.method == "POST":
        form = ScheduleChangeRequestForm(request.POST, employee=user)
        if form.is_valid():
            change_request = form.save(commit=False)
            change_request.employee = user

            date_obj = form.cleaned_data["date"]
            day_number = date_obj.isoweekday()

            # 1️⃣ Check if there's a date-specific schedule
            date_schedule = EmployeeSchedule.objects.filter(employee=user, date=date_obj).first()
            if date_schedule:
                # Do not assign to schedule ForeignKey
                change_request.requested_time_in = date_schedule.time_in
                change_request.requested_time_out = date_schedule.time_out
            else:
                # 2️⃣ Fallback to recurring schedule
                recurring_schedule = Schedule.objects.filter(employee=user, days_of_week__in=[day_number]).first()
                change_request.schedule = recurring_schedule
                if recurring_schedule:
                    change_request.requested_time_in = recurring_schedule.time_in
                    change_request.requested_time_out = recurring_schedule.time_out

            change_request.save()
            return redirect("users:pending_schedule_changes")
        else:
            print(form.errors)  # Debug why form is invalid
    else:
        form = ScheduleChangeRequestForm(employee=user)

    return render(request, "attendance/request_schedule_change.html", {"form": form})


@login_required
def get_schedule_for_date(request: HttpRequest) -> HttpResponse:
    date_str = request.GET.get("date")
    if not date_str:
        return JsonResponse({"error": "No date provided"}, status=400)

    user = cast(User, request.user)
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    day_number = date_obj.isoweekday()  # Monday=1, Sunday=7

    schedule = Schedule.objects.filter(employee=user, days_of_week__in=[day_number]).first()
    if schedule:
        return JsonResponse({
            "time_in": schedule.time_in.strftime("%H:%M"),
            "time_out": schedule.time_out.strftime("%H:%M"),
        })
    return JsonResponse({"time_in": None, "time_out": None})


@login_required
def pending_schedule_changes(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    # --- Pending requests ---
    if user.role == "employee":
        # Employees see only their own pending requests
        requests = ScheduleChangeRequest.objects.filter(employee=user, status="pending")

    elif user.role == "supervisor":
        # Supervisors see their own + pending employee requests
        requests = ScheduleChangeRequest.objects.filter(
            Q(employee=user) | Q(employee__role="employee"),
            status="pending"
        )

    elif user.role == "manager":
        # Managers see only supervisor requests
        requests = ScheduleChangeRequest.objects.filter(
            employee__role="supervisor",
            status="pending"
        )
    else:
        requests = ScheduleChangeRequest.objects.none()

    # --- History (own requests only, approved/rejected) ---
    history = ScheduleChangeRequest.objects.filter(
        employee=user
    ).exclude(status="pending").order_by("-date")

    return render(
        request,
        "attendance/pending_schedule_changes.html",
        {"requests": requests, "history": history},
    )


@login_required
def approve_schedule_change(request: HttpRequest, pk: int) -> HttpResponse:
    user = cast(User, request.user)
    change_request = get_object_or_404(ScheduleChangeRequest, pk=pk)

    # Only supervisors can approve employees, managers can approve supervisors
    if (user.role == "supervisor" and change_request.employee.role == "employee") or \
       (user.role == "manager" and change_request.employee.role == "supervisor"):

        # Approve the request
        change_request.status = "approved"
        change_request.approved_by = user
        change_request.save()

        # Update or create schedule only for the requested date
        EmployeeSchedule.objects.update_or_create(
            employee=change_request.employee,
            date=change_request.date,
            defaults={
                "time_in": change_request.requested_time_in,
                "time_out": change_request.requested_time_out
            }
        )

    return redirect('users:pending_schedule_changes')


@login_required
def reject_schedule_change(request: HttpRequest, pk) -> HttpResponse:
    user = cast(User, request.user)
    change_request = get_object_or_404(ScheduleChangeRequest, pk=pk)

    if (user.role == "supervisor" and change_request.employee.role == "employee") or \
       (user.role == "manager" and change_request.employee.role == "supervisor"):

        change_request.status = "rejected"
        change_request.approved_by = user
        change_request.save()

    return redirect('users:pending_schedule_changes')


@login_required
def edit_schedule_change(request: HttpRequest, pk) -> HttpResponse:
    change_request = get_object_or_404(ScheduleChangeRequest, pk=pk)

    # Only allow the employee who created it to edit
    if request.user != change_request.employee:
        return redirect('users:pending_schedule_changes')

    if request.method == "POST":
        form = ScheduleChangeRequestForm(request.POST, instance=change_request, employee=request.user)
        if form.is_valid():
            form.save()
            return redirect('users:pending_schedule_changes')
    else:
        form = ScheduleChangeRequestForm(instance=change_request, employee=request.user)

    return render(request, "attendance/edit_schedule_change.html", {"form": form})


@login_required
def delete_schedule_change(request: HttpRequest, pk: int) -> HttpResponse:
    change_request = get_object_or_404(ScheduleChangeRequest, pk=pk)

    # Only the request owner can delete
    if request.user != change_request.employee:
        messages.error(request, "You are not allowed to delete this request.")
        return redirect("users:pending_schedule_changes")

    if request.method == "POST":
        change_request.delete()
        messages.success(request, "Schedule change request deleted successfully.")
        return redirect("users:pending_schedule_changes")

    # Render confirmation page
    return render(
        request,
        "attendance/delete_schedule_change_confirm.html",
        {"object": change_request}  # standard Django naming for DeleteView compatibility
    )
