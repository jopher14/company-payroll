from decimal import Decimal
from typing import cast, Any, Optional, Union, IO
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from datetime import time
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse, HttpRequest
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import User, Leave, Attendance, Schedule, Overtime, ScheduleChangeRequest, EmployeeSchedule, Loan, Team
from .forms import LeaveForm, ScheduleForm, EmployeeUpdateForm, OvertimeForm, UserRegistrationForm, ScheduleChangeRequestForm, LoanForm, TeamForm, AttendanceCSVUploadForm
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.utils.timezone import now, localtime
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.utils.timezone import localdate
from dateutil.relativedelta import relativedelta
from django.db.models import Q
import csv
import io


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)  # Get the logged-in user
    return render(request, "users/profile.html", {"user": user})


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
    # Get all users except superusers/admins (optional)
    employees = User.objects.exclude(is_superuser=True).select_related().prefetch_related(
        'teams', 'supervised_teams', 'managed_teams'
    )

    # Combine all possible team relationships
    for emp in employees:
        emp.all_teams = (  # type: ignore[attr-defined]
            emp.teams.all() |
            emp.supervised_teams.all() |
            emp.managed_teams.all()
        ).distinct()

    return render(request, 'users/employee_list.html', {'employees': employees})


# --- EMPLOYEE ---
@login_required
def file_leave(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

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
                status__in=["Pending", "Approved"],  # 👈 ignores Rejected/Cancelled
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

            # ✅ Save if no conflict
            leave.save()
            messages.success(request, "✅ Leave request submitted successfully.")
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
    user = cast(User, request.user)
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

            # ✅ Save
            updated_leave.save()
            messages.success(request, "✅ Leave request updated successfully.")
            return redirect("users:my_leaves")
    else:
        form = LeaveForm(instance=leave)

    return render(request, "leave/edit_leaves.html", {"form": form, "edit": True, "leave": leave})


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


# --- SUPERVISOR ---
def is_supervisor(user):
    return user.role == "supervisor" or user.is_superuser


@login_required
def pending_leaves(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    if user.role == "manager":
        # Manager sees supervisor + employee requests
        leaves = Leave.objects.filter(
            employee__role__in=["supervisor", "employee"], status="Pending"
        )
    elif user.role == "supervisor":
        # Supervisor sees employee requests
        leaves = Leave.objects.filter(
            employee__role="employee", status="Pending"
        )
    else:
        # Employees only see their own leave requests
        leaves = Leave.objects.filter(employee=user, status="Pending")

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
    form = EmployeeUpdateForm(request.POST or None, request.FILES or None, instance=employee)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect('users:employee_list')

    # Get team whether employee, supervisor, or manager
    teams = employee.teams.all() | employee.supervised_teams.all() | employee.managed_teams.all()

    return render(request, 'users/update_employee.html', {
        'form': form,
        'employee': employee,
        'teams': teams.distinct(),
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
        # Supervisor sees pending requests from their team (employees)
        overtime = Overtime.objects.filter(employee__role="employee", status="pending").order_by("-date")
        # History shows only supervisor's own reviewed requests
        history_overtime = Overtime.objects.filter(employee=user).exclude(status="pending").order_by("-date")

    elif user.role == "manager":
        # Manager sees pending requests from both employees and supervisors
        overtime = Overtime.objects.filter(employee__role__in=["employee", "supervisor"], status="pending").order_by("-date")
        # History shows approved/rejected requests from employees and supervisors
        history_overtime = Overtime.objects.filter(employee__role__in=["employee", "supervisor"]).exclude(status="pending").order_by("-date")

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
        return HttpResponse("Invalid user", status=400)

    # 🚫 Restrict to Supervisor & Employee only
    if user.role not in ["supervisor", "employee"]:
        messages.error(request, "You are not allowed to file overtime requests.")
        return redirect("users:my_pending_overtime")

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
                overtime.hours = round(diff.total_seconds() / 3600, 2)

            overtime.overtime_type = form.cleaned_data.get("overtime_type", "ordinary")

            overtime.save()
            messages.success(request, "✅ Overtime request submitted successfully!")
            return redirect("users:my_pending_overtime")
    else:
        form = OvertimeForm()

    return render(request, "overtime/overtime_request.html", {"form": form})


@login_required
def my_pending_overtime(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    # Pending requests
    pending_overtime = Overtime.objects.filter(employee=user, status="pending").order_by("-date")

    # History (approved or rejected)
    history_overtime = Overtime.objects.filter(employee=user).exclude(status="pending").order_by("-date")

    context = {
        "pending_overtime": pending_overtime,
        "history_overtime": history_overtime,
    }

    return render(request, "overtime/my_pending_overtime.html", context)


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
        return HttpResponse("Invalid user", status=400)

    if user.role != "supervisor":
        return redirect("main:dashboard")

    # Separate pending and history
    pending_overtimes = Overtime.objects.filter(
        employee__role="employee",
        status="pending"
    )
    history_overtimes = Overtime.objects.filter(
        employee__role="employee"
    ).exclude(status="pending")

    return render(
        request,
        "overtime/pending_overtime.html",
        {
            "pending_overtimes": pending_overtimes,
            "history_overtimes": history_overtimes,
        }
    )


@login_required
def overtime_edit(request: HttpRequest, pk: int) -> HttpResponse:
    overtime = get_object_or_404(Overtime, pk=pk)

    if request.method == "POST":
        form = OvertimeForm(request.POST, instance=overtime)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Overtime request updated successfully!")
            return redirect("users:my_pending_overtime")
    else:
        form = OvertimeForm(instance=overtime)

    return render(request, "overtime/overtime_edit.html", {"form": form})


@login_required
def overtime_delete(request: HttpRequest, pk: int) -> HttpResponse:
    overtime = get_object_or_404(Overtime, pk=pk)

    if request.method == "POST":
        overtime.delete()
        messages.success(request, "🗑️ Overtime request deleted successfully!")
        return redirect("users:my_pending_overtime")

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

            # 1️⃣ Check for a date-specific schedule
            date_schedule = EmployeeSchedule.objects.filter(employee=user, date=date_obj).first()
            if date_schedule:
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
            messages.success(request, "✅ Schedule Change request successfully!")
            return redirect("users:my_pending_schedule_change")
        else:
            print(form.errors)
    else:
        form = ScheduleChangeRequestForm(employee=user)

    # ✅ Fetch pending requests and history based on role
    if user.role == "manager":
        # Manager sees own + all supervisor requests
        pending_requests = ScheduleChangeRequest.objects.filter(
            employee__role__in=["supervisor", "manager"]
        ).order_by("-created_at")
        history = ScheduleChangeRequest.objects.filter(
            employee__role__in=["supervisor", "manager"],
            status__in=["approved", "rejected"]
        ).order_by("-created_at")
    elif user.role == "supervisor":
        # Supervisor sees own + all employee requests
        pending_requests = ScheduleChangeRequest.objects.filter(
            employee__role__in=["employee", "supervisor"]
        ).order_by("-created_at")
        history = ScheduleChangeRequest.objects.filter(
            employee__role__in=["employee", "supervisor"],
            status__in=["approved", "rejected"]
        ).order_by("-created_at")
    else:
        # Employee sees only their own requests
        pending_requests = ScheduleChangeRequest.objects.filter(employee=user).order_by("-created_at")
        history = ScheduleChangeRequest.objects.filter(employee=user, status__in=["approved", "rejected"]).order_by("-created_at")

    context = {
        "form": form,
        "pending_requests": pending_requests,
        "history": history,
    }
    return render(request, "attendance/request_schedule_change.html", context)


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

    # Pending requests
    if user.role == "employee":
        # Employees see only their own pending requests
        approval_requests = ScheduleChangeRequest.objects.filter(employee=user, status="pending")
    elif user.role == "supervisor":
        # Supervisors see pending requests from employees
        approval_requests = ScheduleChangeRequest.objects.filter(employee__role="employee", status="pending")
    elif user.role == "manager":
        # Managers see pending requests from both supervisors and employees
        approval_requests = ScheduleChangeRequest.objects.filter(
            employee__role__in=["employee", "supervisor"],
            status="pending"
        )
    else:
        approval_requests = ScheduleChangeRequest.objects.none()

    # History of approved/rejected requests
    if user.role in ["employee", "supervisor"]:
        # Employee and supervisor see only their own history
        history = ScheduleChangeRequest.objects.filter(
            employee=user,
            status__in=["approved", "rejected"]
        ).order_by('-created_at')
    elif user.role == "manager":
        # Manager sees history of both employees and supervisors
        history = ScheduleChangeRequest.objects.filter(
            employee__role__in=["employee", "supervisor"],
            status__in=["approved", "rejected"]
        ).order_by('-created_at')
    else:
        history = ScheduleChangeRequest.objects.none()

    context = {
        "user": user,
        "approval_requests": approval_requests,
        "history": history,
    }
    return render(request, "attendance/pending_schedule_changes.html", context)


@login_required
def my_pending_schedule_change(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)

    # Get only the pending schedule change requests of the logged-in user
    pending_requests = ScheduleChangeRequest.objects.filter(employee=user, status='pending').order_by('-created_at')

    context = {
        'pending_requests': pending_requests,
    }
    return render(request, 'attendance/my_pending_schedule_change.html', context)


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


@login_required
def delete_attendance(request: HttpRequest, attendance_id=None) -> HttpResponse:
    """Delete attendance record"""
    attendance = get_object_or_404(Attendance, pk=attendance_id)
    attendance.delete()
    messages.success(request, "Attendance deleted successfully.")
    return redirect("users:manage_attendance")


# ✅ check if user is HR or superuser
def is_hr_or_admin(user: Union[AbstractBaseUser, AnonymousUser]) -> bool:
    return getattr(user, "is_superuser", False) or getattr(user, "role", None) == "human_resources"


@login_required
@user_passes_test(is_hr_or_admin)
def manage_loans(request):
    loans = Loan.objects.select_related("employee").all().order_by("-start_date")
    return render(request, "loans/manage_loans.html", {"loans": loans})


@login_required
@user_passes_test(is_hr_or_admin)
def create_loan(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)

            # Make sure deduction amount is valid
            loan.loan_deduct = Decimal(request.POST.get("loan_deduct", "0"))
            if not loan.loan_deduct or loan.loan_deduct <= 0:
                loan.loan_deduct = loan.loan_amount  # fallback if empty

            # ✅ Initialize properly
            loan.balance = loan.loan_amount
            loan.is_active = True
            loan.status = "OPEN"

            # Auto compute end date
            if loan.start_date and loan.term_months:
                loan.end_date = loan.start_date + relativedelta(months=loan.term_months)

            loan.save()
            messages.success(request, f"Loan for {loan.employee.get_full_name()} created successfully.")
            return redirect("users:manage_loans")
    else:
        form = LoanForm()

    return render(request, "loans/loan_form.html", {"form": form, "title": "➕ Add Loan"})


@login_required
@user_passes_test(is_hr_or_admin)
def edit_loan(request: HttpRequest, pk: int) -> HttpResponse:
    loan = get_object_or_404(Loan, pk=pk)

    if request.method == "POST":
        form = LoanForm(request.POST, instance=loan)
        if form.is_valid():
            loan = form.save(commit=False)

            # recalc end_date when term or start_date changes
            if loan.start_date and loan.term_months:
                loan.end_date = loan.start_date + relativedelta(months=loan.term_months)

            loan.save()
            messages.success(request, "Loan updated successfully.")
            return redirect("users:manage_loans")
    else:
        form = LoanForm(instance=loan)

    return render(request, "loans/loan_form.html", {"form": form, "title": "✏️ Edit Loan"})


@login_required
@user_passes_test(is_hr_or_admin)
def delete_loan(request: HttpRequest, pk: int) -> HttpResponse:
    loan = get_object_or_404(Loan, pk=pk)
    if request.method == "POST":
        loan.delete()
        messages.success(request, "Loan deleted successfully.")
        return redirect("users:manage_loans")
    return render(request, "loans/confirm_delete.html", {"loan": loan})


@login_required
@user_passes_test(is_hr)
def team_list(request: HttpRequest) -> HttpResponse:
    teams = Team.objects.all().order_by('-created_at')
    return render(request, "team/team_list.html", {"teams": teams})


@login_required
@user_passes_test(is_hr)
def create_team(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            team.created_by = request.user
            team.save()
            form.save_m2m()
            messages.success(request, f"Team '{team.name}' created successfully!")
            return redirect("users:team_list")
    else:
        form = TeamForm()
    return render(request, "team/create_team.html", {"form": form})


@login_required
@user_passes_test(is_hr)
def edit_team(request: HttpRequest, pk: int) -> HttpResponse:
    team = get_object_or_404(Team, pk=pk)
    if request.method == "POST":
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            messages.success(request, f"Team '{team.name}' updated successfully!")
            return redirect("users:team_list")
    else:
        form = TeamForm(instance=team)
    return render(request, "team/edit_team.html", {"form": form, "team": team})


@login_required
@user_passes_test(is_hr)
def delete_team(request: HttpRequest, pk: int) -> HttpResponse:
    team = get_object_or_404(Team, pk=pk)
    if request.method == "POST":
        team.delete()
        messages.success(request, "Team deleted successfully!")
        return redirect("users:team_list")
    return render(request, "team/delete_team.html", {"team": team})


@login_required
def my_current_team(request: HttpRequest) -> HttpResponse:
    user = request.user

    # Get all teams where the user is a member (employee, supervisor, or manager)
    teams = Team.objects.filter(
        Q(employees=user) | Q(supervisor=user) | Q(manager=user)
    ).distinct()

    return render(request, "team/my_current_team.html", {"teams": teams})


@login_required
def upload_attendance_csv(request: HttpRequest) -> HttpResponse:
    """
    Upload a CSV with columns: date,time_in,time_out
    Saves records to Attendance for the logged-in employee.
    Header format must be: date,time_in,time_out
    """
    if request.method == "POST":
        form = AttendanceCSVUploadForm(request.POST, request.FILES)

        # ✅ Check if a file was actually selected
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            messages.error(request, "⚠️ Please select a CSV file before uploading.")
            return render(request, "attendance/upload_csv.html", {"form": form})

        if form.is_valid():
            try:
                # ✅ Tell mypy this is a binary IO stream
                binary_stream = cast(IO[bytes], uploaded_file.file)
                file = io.TextIOWrapper(binary_stream, encoding="utf-8")

                reader = csv.DictReader(file)

                # ✅ Validate headers
                expected_headers = {"date", "time_in", "time_out"}
                if not reader.fieldnames or set(reader.fieldnames) != expected_headers:
                    messages.error(
                        request,
                        f"❌ Invalid CSV headers. Expected: {', '.join(expected_headers)}.",
                    )
                    return render(request, "attendance/upload_csv.html", {"form": form})

                added_count = 0

                for row in reader:
                    try:
                        date = datetime.strptime(row["date"], "%d/%m/%Y").date()
                        time_in = datetime.strptime(row["time_in"], "%H:%M:%S").time()
                        time_out = datetime.strptime(row["time_out"], "%H:%M:%S").time()

                        attendance, created = Attendance.objects.update_or_create(
                            employee=request.user,
                            date=date,
                            defaults={"time_in": time_in, "time_out": time_out},
                        )
                        if created:
                            added_count += 1
                    except ValueError:
                        messages.error(
                            request,
                            "❌ Invalid date or time format in CSV. Use DD/MM/YYYY and HH:MM:SS.",
                        )
                        return render(request, "attendance/upload_csv.html", {"form": form})

                messages.success(
                    request,
                    f"✅ {added_count} attendance records uploaded successfully.",
                )
                return redirect("main:dashboard")

            except Exception:
                messages.error(
                    request, "❌ Unable to read the uploaded file. Make sure it's a valid CSV."
                )
                return render(request, "attendance/upload_csv.html", {"form": form})

    else:
        form = AttendanceCSVUploadForm()

    return render(request, "attendance/upload_csv.html", {"form": form})
