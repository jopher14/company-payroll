from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import User, Leave, Attendance
from django.http import HttpResponse, HttpRequest
from .forms import UserRegistrationForm, LeaveForm, AttendanceForm, ScheduleForm, EmployeeUpdateForm
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.timezone import now, localtime
from django.utils import timezone
from datetime import datetime, time, date
from django.core.paginator import Paginator



@login_required
def manager_dashboard(request: HttpRequest) -> HttpResponse:
    if request.user.role != User.MANAGER:
        return HttpResponseForbidden("You are not allowed to access this page.")
    return render("Welcome Manager!")


def register(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "User registered successfully!")
            return redirect("employee_list")
    else:
        form = UserRegistrationForm()
    return render(request, "users/register.html", {"form": form})


def loginView(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        username = request.POST.get("username")
        employee_id = request.POST.get("employee_id")
        password = request.POST.get("password")

        try:
            user = User.objects.get(username=username, employee_id=employee_id)
        except User.DoesNotExist:
            messages.error(request, "Invalid username or employee ID")
            return redirect("login")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid credentials")

    return render(request, "users/login.html")


def logoutView(request: HttpRequest) -> HttpResponse:
    logout(request)
    return render(request, 'users/logout.html')


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
    leaves = Leave.objects.filter(employee=request.user).order_by("-created_at")
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
def pending_leaves(request):
    leaves = Leave.objects.filter(status="Pending").order_by("created_at")
    return render(request, "leave/pending_leaves.html", {"leaves": leaves})


@login_required
@user_passes_test(is_supervisor)
def approve_leave(request, pk):
    leave = get_object_or_404(Leave, pk=pk)
    if leave.status != "Pending":
        messages.warning(request, "This leave request has already been processed.")
    else:
        leave = get_object_or_404(Leave, pk=pk, status="Pending")
        leave.status = "Approved"
        leave.supervisor = request.user
        leave.reviewed_at = now()
        leave.save()
    return redirect("users:pending_leaves")


@login_required
@user_passes_test(is_supervisor)
def reject_leave(request, pk):
    leave = get_object_or_404(Leave, pk=pk, status="Pending")
    leave.status = "Approved"
    leave.supervisor = request.user
    leave.reviewed_at = timezone.now()
    leave.save()

    messages.success(request, f"Leave for {leave.employee.get_full_name() or leave.employee.username} approved.")
    return redirect("users:pending_leaves")


# --- MANAGER ---
def is_manager(user):
    return user.role == "manager" or user.is_superuser

@login_required
@user_passes_test(is_manager)
def set_schedule(request):
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('users:set_schedule')  # Or wherever you want
    else:
        form = ScheduleForm()
    return render(request, 'users/set_schedule.html', {'form': form})


@login_required
def log_attendance(request):
    # Get today's attendance record or create a new one
    attendance, created = Attendance.objects.get_or_create(
        employee=request.user,
        date=localtime(now()).date()  # Manila date
    )

    if request.method == "POST":
        # Log Time In if not set
        if not attendance.time_in:
            attendance.time_in = localtime(now())  # Manila time
        # Log Time Out if Time In exists and Time Out is not set
        elif not attendance.time_out:
            attendance.time_out = localtime(now())
        attendance.save()
        return redirect('users:log_attendance')

    # Send current Manila time to template for display
    current_time = localtime(now())
    return render(request, "users/log_attendance.html", {
        "attendance": attendance,
        "current_time": current_time,
    })


@login_required
def attendance_list(request):
    if request.user.role == "manager":
        # Manager sees all supervisors and employees (exclude managers)
        attendances = Attendance.objects.select_related("employee").filter(
            employee__role__in=["supervisor", "employee"]
        ).order_by("-date")
    else:
        # Employee/supervisor sees only their own
        attendances = Attendance.objects.filter(
            employee=request.user
        ).select_related("employee").order_by("-date")

    # ✅ Pagination (5 per page)
    paginator = Paginator(attendances, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "users/attendance_list.html", {"page_obj": page_obj})


# --- HR ---
def is_hr(user):
    return user.role == "human_resources" or user.is_superuser

@login_required
@user_passes_test(is_hr)
def update_employee(request, pk):
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
