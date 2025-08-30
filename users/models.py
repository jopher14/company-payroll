from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):
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

    ACTIVE = "Active"
    INACTIVE = "INACTIVE"

    STATUS_CHOICES = [
        (ACTIVE, "Active"),
        (INACTIVE, "Inactive"),
    ]

    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=EMPLOYEE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    photo = models.ImageField(
        upload_to='photos/',
        blank=True,
        null=True,
        default='photos/default.png'  # 👈 default photo
    )

    # government IDs
    sss = models.CharField(max_length=20, blank=True, null=True)
    tin = models.CharField(max_length=20, blank=True, null=True)
    pagibig = models.CharField(max_length=20, blank=True, null=True)
    philhealth = models.CharField(max_length=20, blank=True, null=True)

    birthday = models.DateField(null=True, blank=True)
    contact_number = models.CharField(max_length=15, null=True, blank=True)

    @property
    def photoOrDefault(self):
        if self.photo:
            return self.photo.url
        return '/media/photos/default.png'

    def __str__(self):
        return f"{self.first_name} ({self.role})"


class Leave(models.Model):
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
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves"
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.username} - {self.start_date} to {self.end_date}"


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


class Schedule(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="schedule"
    )
    time_in = models.TimeField()
    time_out = models.TimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.username} - {self.time_in} to {self.time_out}"


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
