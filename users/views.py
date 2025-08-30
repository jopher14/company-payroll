from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import User, Leave, Attendance, Schedule, Overtime
from django.http import HttpResponse, HttpRequest
from .forms import LeaveForm, ScheduleForm, EmployeeUpdateForm, OvertimeForm
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.utils.timezone import now, localtime
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator


@login_required
def manager_dashboard(request: HttpRequest) -> HttpResponse:
    # Tell mypy that request.user is your User model
    user = request.user
    if not isinstance(user, User):
        return HttpResponseForbidden("You are not allowed to access this page.")

    if user.role != User.MANAGER:
        return HttpResponseForbidden("You are not allowed to access this page.")

    return render(request, "manager_dashboard.html", {"user": user})


def loginView(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("dashboard")  # change to your home/dashboard
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
    if request.method == "POST":
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = request.user
            leave.save()
            return redirect("users:my_leaves")
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
    leave = get_object_or_404(Leave, pk=pk, employee=request.user, status="Pending")
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
    leave = get_object_or_404(Leave, pk=pk, employee=request.user, status="Pending")
    if request.method == "POST":
        leave.delete()
        return redirect("my_leaves")
    return render(request, "leave/delete_leave.html", {"leave": leave})


# --- SUPERVISOR ---
def is_supervisor(user):
    return user.role == "supervisor" or user.is_superuser


@login_required
@user_passes_test(is_supervisor)
def pending_leaves(request: HttpRequest) -> HttpResponse:
    leaves = Leave.objects.filter(status="Pending").order_by("created_at")
    return render(request, "leave/pending_leaves.html", {"leaves": leaves})


@login_required
@user_passes_test(is_supervisor)
def approve_leave(request: HttpRequest, pk) -> HttpResponse:
    leave = get_object_or_404(Leave, pk=pk)

    if leave.status != "Pending":
        messages.warning(request, "This leave request has already been processed.")
    else:
        leave = get_object_or_404(Leave, pk=pk, status="Pending")
        leave.status = "Approved"

        # Tell mypy that request.user is a User
        supervisor = request.user
        if not isinstance(supervisor, User):
            # This should never happen due to @login_required and is_supervisor
            return HttpResponse("Invalid user", status=400)

        leave.supervisor = supervisor
        leave.reviewed_at = now()
        leave.save()

    return redirect("users:pending_leaves")


@login_required
@user_passes_test(is_supervisor)
def reject_leave(request: HttpRequest, pk) -> HttpResponse:
    leave = get_object_or_404(Leave, pk=pk, status="Pending")
    leave.status = "Rejected"

    # Tell mypy that request.user is a User
    supervisor = request.user
    if not isinstance(supervisor, User):
        # This should never happen due to decorators
        return HttpResponse("Invalid user", status=400)

    leave.supervisor = supervisor
    leave.reviewed_at = timezone.now()
    leave.save()

    messages.success(
        request,
        f"Leave for {leave.employee.get_full_name() or leave.employee.username} rejected."
    )
    return redirect("users:pending_leaves")


# --- MANAGER ---
def is_manager(user):
    return user.role == "manager" or user.is_superuser


@login_required
@user_passes_test(is_manager)
def set_schedule(request: HttpRequest) -> HttpResponse:
    employee_id_str = request.GET.get("employee")
    employee_id: int | None = None
    instance = None

    if employee_id_str:
        try:
            employee_id = int(employee_id_str)
        except ValueError:
            employee_id = None  # invalid id, ignore

    if employee_id is not None:
        # If employee already has a schedule, fetch it
        instance = Schedule.objects.filter(employee_id=employee_id).first()

    if request.method == "POST":
        form = ScheduleForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect("users:set_schedule")
    else:
        form = ScheduleForm(instance=instance)

    return render(request, "users/set_schedule.html", {"form": form})


@login_required
def log_attendance(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        # This should never happen because of @login_required
        return HttpResponse("Invalid user", status=400)

    today = localtime(now()).date()
    current_time = localtime(now())

    # Get schedule for this user
    schedule = Schedule.objects.filter(employee=user).first()

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
        "schedule": schedule,
        "current_time": current_time,
    })


@login_required
def attendance_list(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        # Should never happen due to @login_required
        return HttpResponse("Invalid user", status=400)

    if user.role == "manager":
        # Manager sees all supervisors and employees (exclude managers)
        attendances = Attendance.objects.select_related("employee").filter(
            employee__role__in=["supervisor", "employee"]
        ).order_by("-date")
    else:
        # Employee/supervisor sees only their own
        attendances = Attendance.objects.filter(
            employee=user,
            employee__role__in=["supervisor", "employee"]
        ).select_related("employee").order_by("-date")

    # Pagination (5 per page)
    paginator = Paginator(attendances, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "attendance/attendance_list.html", {
        "page_obj": page_obj,
    })


# --- HR ---
def is_hr(user):
    return user.role == "human_resources" or user.is_superuser


@login_required
@user_passes_test(is_hr)
def update_employee(request: HttpRequest, pk) -> HttpResponse:
    employee = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        form = EmployeeUpdateForm(request.POST, request.FILES, instance=employee)  # ✅ include request.FILES
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
def overtime_list(request):
    user = request.user

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

            # ✅ Calculate hours safely in backend
            date = form.cleaned_data.get("date")
            time_in = form.cleaned_data.get("time_in")
            time_out = form.cleaned_data.get("time_out")

            if date and time_in and time_out:
                start_dt = datetime.combine(date, time_in)
                end_dt = datetime.combine(date, time_out)

                # Handle overnight (if end time is earlier than start)
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)

                diff = end_dt - start_dt
                overtime.hours = round(diff.total_seconds() / 3600, 2)  # store as decimal hours

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
        # Should never happen because of @login_required
        return HttpResponse("Invalid user", status=400)

    if user.role == "manager":
        overtime = get_object_or_404(Overtime, pk=pk)
        overtime.status = "approved"
        overtime.save()
        messages.success(request, "Overtime approved successfully ✅")

    return redirect("users:overtime_list")


@login_required
def overtime_reject(request: HttpRequest, pk) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        # Should never happen because of @login_required
        return HttpResponse("Invalid user", status=400)

    if user.role == "manager":
        overtime = get_object_or_404(Overtime, pk=pk)
        overtime.status = "rejected"
        overtime.save()
        messages.warning(request, "Overtime rejected ❌")

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
