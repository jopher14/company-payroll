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
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)

    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    overtime_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    holiday_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    sss = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    philhealth = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    pagibig = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    withholding_tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    net_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

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
