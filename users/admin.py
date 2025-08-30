from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Leave, Attendance, Schedule, Overtime


class UserAdmin(BaseUserAdmin):
    # Fields to display in admin list view
    list_display = ("username", "email", "role", "employee_id", "is_staff", "is_superuser")
    list_filter = ("role", "is_staff", "is_superuser")
    search_fields = ("username", "email", "employee_id")
    ordering = ("username",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Exclude superusers (admin accounts)
        return qs.exclude(is_superuser=True)

    # Fields to edit in admin form
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "employee_id")}),
        ("Permissions", {"fields": ("role", "is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "employee_id",
                "email",
                "role",
                "password1",
                "password2",
                "is_staff",
                "is_superuser"
            ),
        }),
    )


# Register the custom User model with the custom UserAdmin
admin.site.register(User, UserAdmin)


@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 'start_date', 'end_date', 'status', 'supervisor', 'reviewed_at', 'created_at'
    )
    list_filter = ('status', 'employee')
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
        "time_in",
        "time_out",
        "created_at",
        "updated_at",
    )
    list_filter = ("employee__role",)  # Filter by role
    search_fields = ("employee__username", "employee__employee_id")
    ordering = ("-created_at",)


@admin.register(Overtime)
class OvertimeAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "hours", "reason", "status", "get_approved_by")

    @admin.display(description="Approved By")
    def get_approved_by(self, obj):
        return obj.reviewed_by.get_full_name() if obj.reviewed_by else "—"
