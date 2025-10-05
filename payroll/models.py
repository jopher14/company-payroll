from django.db import models
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
import calendar
from datetime import date, timedelta
from users.models import Attendance, Loan

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

    # 💰 Salary components
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # ⏱️ Overtime
    overtime_type = models.CharField(max_length=50, choices=OVERTIME_TYPE_CHOICES, null=True, blank=True)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    overtime_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # 🎉 Holiday pay
    holiday_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # 🧾 Deductions
    attendance_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    loan_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    loan_breakdown = models.JSONField(default=dict, blank=True)  # structured data
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    loan_type_summary = models.JSONField(default=dict, blank=True, null=True)

    sss = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    philhealth = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    pagibig = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    withholding_tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # 💵 Final net pay
    net_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # 📊 Rates
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # 🧮 JSON field for attendance details
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
        return f"Payroll for {self.employee} - {self.month_name()} {self.year} ({self.get_period_display()})"

    # 📅 Utility
    def month_name(self):
        return calendar.month_name[self.month]

    # 🧮 Rounding helper
    def q(self, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # 🕒 Overtime computation
    def compute_overtime(self) -> Decimal:
        from payroll.utils import (
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
        return self.q(func(self.hourly_rate, self.overtime_hours)) if func else Decimal("0.00")

    # 📆 Attendance deduction
    def compute_attendance_deduction(self):
        holidays = getattr(settings, "HOLIDAYS", set())

        # Cutoff period
        if self.period == "first_half":
            start_date, end_date = date(self.year, self.month, 1), date(self.year, self.month, 15)
        else:
            last_day = calendar.monthrange(self.year, self.month)[1]
            start_date, end_date = date(self.year, self.month, 16), date(self.year, self.month, last_day)

        attendance_map = {
            att.date: att
            for att in Attendance.objects.filter(employee=self.employee, date__range=[start_date, end_date])
        }

        total_salary_deduction = Decimal("0.00")
        total_allowance_deduction = Decimal("0.00")
        breakdown = {}

        daily_allowance = self.q(self.allowances / Decimal(26))
        day_count = (end_date - start_date).days + 1

        for i in range(day_count):
            day = start_date + timedelta(days=i)
            if day.weekday() >= 5 or (holidays and day in holidays):
                continue

            att = attendance_map.get(day)
            if not att or not att.time_in:
                salary_deduction, allowance_deduction, reason = self.daily_rate, daily_allowance, "Absent"
            else:
                salary_deduction = att.compute_deduction(self.daily_rate, self.hourly_rate)
                allowance_deduction, reason = Decimal("0.00"), att.get_deduction_reason()

            total_salary_deduction += salary_deduction
            total_allowance_deduction += allowance_deduction

            if salary_deduction > 0 or allowance_deduction > 0:
                breakdown[str(day)] = {
                    "Salary Deduction": str(self.q(salary_deduction)),
                    "Allowance Deduction": str(self.q(allowance_deduction)),
                    "reason": reason,
                }

        return self.q(total_salary_deduction), self.q(total_allowance_deduction), breakdown

    # 💳 Loan deduction
    def compute_loan_deduction(self):
        active_loans = Loan.objects.filter(employee=self.employee, is_active=True)
        total_loan_deduction = Decimal("0.00")

        for loan in active_loans:
            if loan.term_months <= 0:
                continue

            monthly_due = loan.loan_amount / Decimal(loan.term_months)
            monthly_due = self.q(monthly_due)

            new_balance = max(Decimal("0.00"), loan.balance - monthly_due)
            loan.balance = new_balance
            loan.is_active = new_balance > 0
            loan.save(update_fields=["balance", "is_active"])

            total_loan_deduction += monthly_due

        return self.q(total_loan_deduction)

    # 💾 Save method with all computations
    def save(self, *args, **kwargs):
        # Rates
        if self.basic_salary > 0:
            self.daily_rate = self.q(self.basic_salary / Decimal(26))
            self.hourly_rate = self.q(self.daily_rate / Decimal(8))

        # Attendance
        salary_ded, allowance_ded, breakdown = self.compute_attendance_deduction()
        self.attendance_deduction = salary_ded
        self.attendance_breakdown = breakdown

        # Overtime + Loans
        self.overtime_pay = self.compute_overtime()
        self.loan_deduction = self.compute_loan_deduction()

        # Total deductions
        self.total_deductions = self.q(
            self.attendance_deduction
            + self.loan_deduction
            + self.sss
            + self.philhealth
            + self.pagibig
            + self.withholding_tax
        )

        # Gross and net pay
        gross_pay = self.q(self.basic_salary + self.allowances + self.overtime_pay + self.holiday_pay)
        self.net_pay = self.q(gross_pay - self.total_deductions)

        super().save(*args, **kwargs)
