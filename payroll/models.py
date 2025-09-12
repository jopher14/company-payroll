from django.db import models
from django.conf import settings
from decimal import Decimal
import calendar

User = settings.AUTH_USER_MODEL


class Payroll(models.Model):
    PERIOD_CHOICES = [
        ("first_half", "1st Half"),
        ("second_half", "2nd Half"),
    ]

    OVERTIME_TYPE_CHOICES = [
        ("ordinary", "Ordinary Day"),
        ("restday", "Rest Day"),
        ("special_holiday", "Special Holiday"),
        ("special_holiday_restday", "Special Holiday + Rest Day"),
        ("regular_holiday", "Regular Holiday"),
        ("regular_holiday_restday", "Regular Holiday + Rest Day"),
        ("double_holiday", "Double Holiday"),
        ("double_holiday_restday", "Double Holiday + Rest Day"),
    ]

    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    employee = models.ForeignKey(User, on_delete=models.CASCADE)

    # Salary components
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Overtime
    overtime_type = models.CharField(max_length=50, choices=OVERTIME_TYPE_CHOICES, null=True, blank=True)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    overtime_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Holidays
    holiday_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Deductions
    sss = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    philhealth = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    pagibig = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    withholding_tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Final net pay
    net_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Rates
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "month", "year", "period"],
                name="unique_payroll_per_employee_per_period"
            )
        ]

    def __str__(self):
        return f"Payroll for {self.employee} - {self.month}/{self.year}"

    def month_name(self):
        return calendar.month_name[self.month]

    # ✅ Compute overtime pay automatically
    def compute_overtime(self) -> Decimal:
        from payroll.utils import (  # assuming your OT functions are in payroll/utils.py
            compute_ordinary_ot,
            compute_restday_ot,
            compute_special_holiday_ot,
            compute_special_holiday_restday_ot,
            compute_regular_holiday_ot,
            compute_regular_holiday_restday_ot,
            compute_double_holiday_ot,
            compute_double_holiday_restday_ot,
        )

        if not self.overtime_type or self.overtime_hours <= 0:
            return Decimal("0.00")

        mapping = {
            "ordinary": compute_ordinary_ot,
            "restday": compute_restday_ot,
            "special_holiday": compute_special_holiday_ot,
            "special_holiday_restday": compute_special_holiday_restday_ot,
            "regular_holiday": compute_regular_holiday_ot,
            "regular_holiday_restday": compute_regular_holiday_restday_ot,
            "double_holiday": compute_double_holiday_ot,
            "double_holiday_restday": compute_double_holiday_restday_ot,
        }

        func = mapping.get(self.overtime_type)
        if func:
            return func(self.hourly_rate, self.overtime_hours)

        return Decimal("0.00")
