from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Leave, Attendance, Schedule, Overtime, ScheduleChangeRequest, EmployeeSchedule, Loan
from payroll.models import Payroll


class UserAdmin(BaseUserAdmin):
    # Fields to display in the admin list view
    list_display = (
        "username", "email", "first_name", "last_name", "role", "status", "position", "is_staff", "is_superuser"
    )
    list_filter = ("role", "status", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    # Exclude superusers from the list
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(is_superuser=True)

    # Fields to edit in the admin form
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {
            "fields": (
                "first_name", "last_name", "email", "position", "photo", "birthday", "contact_number"
            )
        }),
        ("Permissions", {
            "fields": ("role", "status", "is_staff", "is_active", "is_superuser", "groups", "user_permissions")
        }),
        ("Salary & Benefits", {
            "fields": ("salary", "allowances", "sss", "tin", "pagibig", "philhealth", "leave_count")
        }),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "email", "role", "status", "password1", "password2", "is_staff", "is_superuser"
            ),
        }),
    )


# Register the custom User model with this admin
admin.site.register(User, UserAdmin)


@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'start_date',
        'end_date',
        'leave_type',
        'status',
        'supervisor',
        'reviewed_at',
        'created_at',
    )
    list_filter = ('status', 'employee', 'leave_type')
    search_fields = ('employee__username', 'employee__first_name', 'employee__last_name', 'reason')
    ordering = ('-created_at',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'time_in', 'time_out')
    list_filter = ('date', 'employee')
    search_fields = ('employee__username', 'employee__first_name', 'employee__last_name')
    ordering = ('-date',)


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "get_days_display",  # use method to display days
        "time_in",
        "time_out",
        "created_at",
        "updated_at",
    )

    # Custom filter for days (optional)
    list_filter = ("employee__role",)  # Can't filter by ManyToManyField directly

    search_fields = ("employee__username", "employee__first_name", "employee__last_name")
    ordering = ("-created_at",)


@admin.register(EmployeeSchedule)
class EmployeeScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "date",
        "time_in",
        "time_out",
        "created_at",
        "updated_at",
    )
    list_filter = ("employee__role", "date")
    search_fields = ("employee__username", "employee__first_name", "employee__last_name")
    ordering = ("-date",)


@admin.register(Overtime)
class OvertimeAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "hours", "reason", "status", "get_approved_by")

    @admin.display(description="Approved By")
    def get_approved_by(self, obj):
        return obj.reviewed_by.get_full_name() if obj.reviewed_by else "—"


class PayrollInline(admin.TabularInline):  # Or admin.StackedInline
    model = Payroll
    extra = 0
    fields = ("basic_salary", "sss", "philhealth", "pagibig", "withholding_tax", "net_pay", "created_at")
    readonly_fields = ("created_at",)


@admin.register(ScheduleChangeRequest)
class ScheduleChangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'schedule',
        'date',
        'requested_time_in',
        'requested_time_out',
        'status',
        'approved_by',
        'created_at',
    )
    list_filter = ('status', 'date', 'employee')
    search_fields = ('employee__username', 'employee__first_name', 'employee__last_name', 'reason')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "loan_type",
        "amount",
        "loan_deduct",
        "balance",
        "term_months",
        "start_date",
        "end_date",
        "is_active",
    )
    list_filter = (
        "loan_type",
        "is_active",
        "term_months",
        ("start_date", admin.DateFieldListFilter),
    )
    search_fields = (
        "employee__first_name",
        "employee__last_name",
        "loan_type__name",  # if loan_type is a FK
    )
    ordering = ("-start_date",)
    date_hierarchy = "start_date"
