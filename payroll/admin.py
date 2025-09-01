from django.contrib import admin
from .models import Payroll


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "basic_salary",
        "allowances",
        "sss",
        "philhealth",
        "pagibig",
        "withholding_tax",
        "net_pay",
        "created_at",
    )
    search_fields = ("employee__username", "employee__first_name", "employee__last_name")
    list_filter = ("created_at",)
