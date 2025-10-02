from django.db import models
from django.conf import settings
from decimal import Decimal
import calendar
from datetime import date, timedelta
from users.models import Attendance

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
    attendance_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

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

    # ✅ JSON field to store per-day attendance logs
    attendance_breakdown = models.JSONField(default=list, blank=True, null=True)

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

    def compute_attendance_deduction(self):
        """Compute attendance deductions (salary + allowance separately) and build breakdown logs."""
        holidays = getattr(settings, "HOLIDAYS", set())  # or pass from utils

        # cutoff dates
        if self.period == "first_half":
            start_date = date(self.year, self.month, 1)
            end_date = date(self.year, self.month, 15)
        else:
            last_day = calendar.monthrange(self.year, self.month)[1]
            start_date = date(self.year, self.month, 16)
            end_date = date(self.year, self.month, last_day)

        # prefetch attendance
        attendance_map = {
            att.date: att
            for att in Attendance.objects.filter(employee=self.employee, date__range=[start_date, end_date])
        }

        total_salary_deduction = Decimal("0.00")
        total_allowance_deduction = Decimal("0.00")
        breakdown = {}

        # compute per-day allowance (spread across 26 workdays)
        daily_allowance = (self.allowances / Decimal(26)).quantize(Decimal("0.01"))

        day_count = (end_date - start_date).days + 1
        for i in range(day_count):
            day = start_date + timedelta(days=i)

            # skip weekends & holidays
            if day.weekday() >= 5 or (holidays and day in holidays):
                continue

            att = attendance_map.get(day)

            if not att or not att.time_in:  # completely absent
                salary_deduction = self.daily_rate
                allowance_deduction = daily_allowance
                reason = "Absent"
            else:  # Present but late/half-day
                salary_deduction = att.compute_deduction(self.daily_rate, self.hourly_rate)
                allowance_deduction = Decimal("0.00")
                reason = att.get_deduction_reason()

            # accumulate totals
            total_salary_deduction += salary_deduction
            total_allowance_deduction += allowance_deduction

            # store breakdown
            if salary_deduction > 0 or allowance_deduction > 0:
                breakdown[str(day)] = {
                    "Salary Deduction": str(salary_deduction.quantize(Decimal("0.01"))),
                    "Allowance Deduction": str(allowance_deduction.quantize(Decimal("0.01"))),
                    "reason": reason,
                }

        return total_salary_deduction, total_allowance_deduction, breakdown

    def save(self, *args, **kwargs):
        # ✅ Auto-compute rates
        if self.basic_salary > 0:
            self.daily_rate = self.basic_salary / Decimal(26)
            self.hourly_rate = self.daily_rate / Decimal(8)

        # ✅ Attendance deductions with breakdown
        salary_ded, allowance_ded, breakdown = self.compute_attendance_deduction()
        self.total_salary_deduction = salary_ded
        self.total_allowance_deduction = allowance_ded

        # keep attendance_deduction as SALARY-only (optional, or you can drop it)
        self.attendance_deduction = salary_ded

        # requires a JSONField in Payroll model
        if hasattr(self, "attendance_breakdown"):
            self.attendance_breakdown = breakdown

        # ✅ Overtime
        self.overtime_pay = self.compute_overtime()

        # ✅ Total deductions
        self.total_deductions = (
            self.attendance_deduction
            + self.sss
            + self.philhealth
            + self.pagibig
            + self.withholding_tax
        )

        # ✅ Net pay
        gross_pay = self.basic_salary + self.allowances + self.overtime_pay + self.holiday_pay
        self.net_pay = gross_pay - self.total_deductions

        super().save(*args, **kwargs)
