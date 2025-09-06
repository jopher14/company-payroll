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
    leave_count = models.PositiveIntegerField(default=15)

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


class Leave(models.Model):
    HALF_DAY = "half_day"
    WHOLE_DAY = "whole_day"

    LEAVE_TYPE_CHOICES = [
        (HALF_DAY, "Half Day"),
        (WHOLE_DAY, "Whole Day"),
    ]

    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leaves"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=10, choices=LEAVE_TYPE_CHOICES, default=WHOLE_DAY)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Approved", "Approved"),
            ("Rejected", "Rejected")
        ],
        default="Pending"
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_leaves"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def leave_hours(self):
        """Return hours: 4 for half-day, 8 for whole-day"""
        return 4 if self.leave_type == self.HALF_DAY else 8

    def deduct_leave(self):
        """Deduct leave_count from employee"""
        days_to_deduct = 0.5 if self.leave_type == self.HALF_DAY else 1
        self.employee.leave_count = max(self.employee.leave_count - days_to_deduct, 0)
        self.employee.save()

    def save(self, *args, **kwargs):
        # Only deduct if the status changed to APPROVED
        if self.pk:  # existing record
            old = Leave.objects.get(pk=self.pk)
            if old.status != self.APPROVED and self.status == self.APPROVED:
                self.deduct_leave()
        super().save(*args, **kwargs)


class Attendance(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)

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
        (1, "Sun"),
        (2, "Mon"),
        (3, "Tue"),
        (4, "Wed"),
        (5, "Thu"),
        (6, "Fri"),
        (7, "Sat"),
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
        days = ", ".join(day.name for day in self.days_of_week.all())
        return f"{self.employee.username} - {days} ({self.time_in} - {self.time_out})"


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
