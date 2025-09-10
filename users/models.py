from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from decimal import Decimal
from django.templatetags.static import static


class User(AbstractUser):
    # Roles
    ADMIN = 'admin'
    HUMAN_RESOURCES = 'human_resources'
    MANAGER = 'manager'
    SUPERVISOR = 'supervisor'
    EMPLOYEE = 'employee'

    ROLE_CHOICES = [
        (ADMIN, "Admin"),
        (HUMAN_RESOURCES, "Human Resources"),
        (MANAGER, "Manager"),
        (SUPERVISOR, "Supervisor"),
        (EMPLOYEE, "Employee"),
    ]

    # Status
    ACTIVE = "Active"
    INACTIVE = "Inactive"

    STATUS_CHOICES = [
        (ACTIVE, "Active"),
        (INACTIVE, "Inactive"),
    ]

    # Basic info
    position = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=EMPLOYEE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)

    # Photo
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)

    # Government IDs and salary info
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sss = models.CharField(max_length=20, blank=True, null=True)
    tin = models.CharField(max_length=20, blank=True, null=True)
    pagibig = models.CharField(max_length=20, blank=True, null=True)
    philhealth = models.CharField(max_length=20, blank=True, null=True)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Leave
    leave_count = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("15.0")
    )

    # Contact
    birthday = models.DateField(null=True, blank=True)
    contact_number = models.CharField(max_length=15, null=True, blank=True)

    @property
    def photoOrDefault(self):
        if self.photo and self.photo.name:
            return self.photo.url
        return static('photos/DefaultPhoto.jpg')

    def __str__(self):
        return f"{self.first_name} ({self.role})"

    def refresh_leave_balance(self):
        """Recalculate leave balance from approved leaves."""
        from users.models import Leave  # inline import to avoid circular import

        base_entitlement = Decimal("15.0")  # default yearly entitlement

        approved_leaves = Leave.objects.filter(employee=self, status=Leave.APPROVED)

        total_deducted = Decimal("0.0")
        for leave in approved_leaves:
            total_deducted += Decimal(str(leave.total_days()))

        self.leave_count = max(base_entitlement - total_deducted, Decimal("0.0"))
        self.save()


class Leave(models.Model):
    # Leave types
    HALF_DAY = "half_day"
    WHOLE_DAY = "whole_day"
    LEAVE_TYPE_CHOICES = [
        (HALF_DAY, "Half Day"),
        (WHOLE_DAY, "Whole Day"),
    ]

    # Status choices
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    # Fields
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="leaves",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(
        max_length=20,
        choices=LEAVE_TYPE_CHOICES,
        default=WHOLE_DAY,
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
    )

    # Tracking approver/reviewer
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_leaves",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    # --- Business Logic ---

    def total_days(self) -> float:
        """Return number of leave days deducted."""
        days = (self.end_date - self.start_date).days + 1
        if self.leave_type == self.HALF_DAY and days == 1:
            return 0.5
        return float(days)

    def leave_days(self) -> float:
        """Return leave days (0.5 for half-day, else full days inclusive)."""
        if self.leave_type == self.HALF_DAY:
            return 0.5
        return (self.end_date - self.start_date).days + 1

    def leave_hours(self) -> int:
        """Return leave hours: 4 for half-day, else 8h * days."""
        if self.leave_type == self.HALF_DAY:
            return 4
        return int(self.leave_days() * 8)

    def deduct_leave(self) -> None:
        """Deduct leave_count from employee (ensure not below 0)."""
        days_to_deduct = Decimal(str(self.leave_days()))
        self.employee.leave_count = max(
            self.employee.leave_count - days_to_deduct, Decimal("0.0")
        )
        self.employee.save()

    def save(self, *args, **kwargs):
        old_status = None
        if self.pk:
            old_status = Leave.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        # Recalculate leave balance if status changed
        if (old_status != self.APPROVED and self.status == self.APPROVED) or \
           (old_status == self.APPROVED and self.status != self.APPROVED):
            self.employee.refresh_leave_balance()

    def __str__(self) -> str:
        return f"{self.employee} | {self.get_leave_type_display()} | {self.status}"


class Attendance(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    half_day = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.employee.username} - {self.date}"

    @property
    def schedule(self):
        return Schedule.objects.filter(employee=self.employee).first()

    @property
    def status(self):
        """Return a readable status for attendance"""
        if self.time_in and self.time_out:
            return "Present"
        elif self.time_in and not self.time_out:
            return "Half Day"
        else:
            return "Absent"


class Day(models.Model):
    DAYS = [
        (0, "Sun"),
        (1, "Mon"),
        (2, "Tue"),
        (3, "Wed"),
        (4, "Thu"),
        (5, "Fri"),
        (6, "Sat"),
    ]
    number = models.IntegerField(choices=DAYS)
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Schedule(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="schedule"
    )
    days_of_week = models.ManyToManyField(Day)  # <-- add this field
    time_in = models.TimeField()
    time_out = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_days_display(self):
        return ", ".join(day.name for day in self.days_of_week.all())

    def __str__(self):
        days = self.days_of_week.all().order_by("id")  # order Mon-Sun if Day model uses id for that
        schedule_lines = [f"{day.name} {self.time_in.strftime('%H:%M')}-{self.time_out.strftime('%H:%M')}" for day in days]
        return "\n".join(schedule_lines)


class EmployeeSchedule(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="date_schedules"
    )
    date = models.DateField()
    time_in = models.TimeField()
    time_out = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'date')  # Ensure only one schedule per employee per date

    def __str__(self):
        return f"{self.employee.username} - {self.date} ({self.time_in} - {self.time_out})"


class Overtime(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected")
        ],
        default="pending")
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_overtime"
    )

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.status})"


class ScheduleChangeRequest(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    schedule = models.ForeignKey(
        "Schedule", on_delete=models.CASCADE, null=True, blank=True, related_name="change_requests"
    )
    date = models.DateField()

    # ✅ Use model fields, not form fields
    requested_time_in = models.TimeField()
    requested_time_out = models.TimeField()

    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="approved_schedule_changes",
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def approve(self, approver):
        """Approve request and update the schedule"""
        self.status = self.APPROVED
        self.approved_by = approver
        self.save()

        # Update the actual schedule
        self.schedule.time_in = self.requested_time_in
        self.schedule.time_out = self.requested_time_out
        self.schedule.save()

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.status})"
