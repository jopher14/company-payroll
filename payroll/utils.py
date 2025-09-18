from decimal import Decimal
from users.models import Attendance


def compute_sss(salary: Decimal) -> Decimal:
    if salary < Decimal("3250"):
        return Decimal("135.00")
    elif salary < Decimal("24750"):
        return salary * Decimal("0.045")  # 4.5%
    else:
        return Decimal("1125.00")


def compute_philhealth(salary: Decimal) -> Decimal:
    base = min(max(salary, Decimal("10000")), Decimal("90000"))
    return (base * Decimal("0.05")) / Decimal("2")


def compute_pagibig(salary: Decimal) -> Decimal:
    return min(salary * Decimal("0.02"), Decimal("100.00"))


# ✅ Adjusted to include overtime pay
def compute_withholding_tax(salary: Decimal, overtime_pay: Decimal = Decimal("0.00")) -> Decimal:
    taxable_income = salary + overtime_pay

    if taxable_income <= Decimal("20833"):
        return Decimal("0.00")
    elif taxable_income <= Decimal("33332"):
        return (taxable_income - Decimal("20833")) * Decimal("0.15")
    elif taxable_income <= Decimal("66666"):
        return Decimal("1875") + (taxable_income - Decimal("33333")) * Decimal("0.20")
    elif taxable_income <= Decimal("166666"):
        return Decimal("8541.80") + (taxable_income - Decimal("66667")) * Decimal("0.25")
    elif taxable_income <= Decimal("666666"):
        return Decimal("33541.80") + (taxable_income - Decimal("166667")) * Decimal("0.30")
    else:
        return Decimal("183541.80") + (taxable_income - Decimal("666667")) * Decimal("0.35")


# ✅ Daily & Hourly Rate
def compute_daily_rate(salary: Decimal, workdays_per_month: int = 22) -> Decimal:
    if workdays_per_month <= 0:
        raise ValueError("workdays_per_month must be greater than 0")
    return (salary / Decimal(workdays_per_month)).quantize(Decimal("0.01"))


def compute_hourly_rate(salary: Decimal, workdays_per_month: int = 22, hours_per_day: int = 8) -> Decimal:
    daily_rate = compute_daily_rate(salary, workdays_per_month)
    if hours_per_day <= 0:
        raise ValueError("hours_per_day must be greater than 0")
    return (daily_rate / Decimal(hours_per_day)).quantize(Decimal("0.01"))


# ✅ Overtime Computations (PH rules)
def compute_overtime_pay(hourly_rate: Decimal, hours: Decimal, multiplier: Decimal) -> Decimal:
    return (hourly_rate * hours * multiplier).quantize(Decimal("0.01"))


def compute_ordinary_ot(hourly_rate: Decimal, hours: Decimal) -> Decimal:
    return compute_overtime_pay(hourly_rate, hours, Decimal("1.25"))


def compute_restday_ot(hourly_rate: Decimal, hours: Decimal) -> Decimal:
    return compute_overtime_pay(hourly_rate, hours, Decimal("1.69"))


def compute_special_holiday_ot(hourly_rate: Decimal, hours: Decimal) -> Decimal:
    return compute_overtime_pay(hourly_rate, hours, Decimal("1.69"))


def compute_special_holiday_restday_ot(hourly_rate: Decimal, hours: Decimal) -> Decimal:
    return compute_overtime_pay(hourly_rate, hours, Decimal("1.95"))


def compute_regular_holiday_ot(hourly_rate: Decimal, hours: Decimal) -> Decimal:
    return compute_overtime_pay(hourly_rate, hours, Decimal("2.60"))


def compute_regular_holiday_restday_ot(hourly_rate: Decimal, hours: Decimal) -> Decimal:
    return compute_overtime_pay(hourly_rate, hours, Decimal("3.38"))


def compute_double_holiday_ot(hourly_rate: Decimal, hours: Decimal) -> Decimal:
    return compute_overtime_pay(hourly_rate, hours, Decimal("3.90"))


def compute_double_holiday_restday_ot(hourly_rate: Decimal, hours: Decimal) -> Decimal:
    return compute_overtime_pay(hourly_rate, hours, Decimal("5.07"))


def compute_total_attendance_deduction(employee, year: int, month: int, start_day: int, end_day: int,
                                       daily_rate: Decimal, hourly_rate: Decimal) -> Decimal:
    """
    Compute total attendance deductions for a given employee in a cutoff period.
    Includes:
    - Absent → 1 daily rate
    - Half Day → 0.5 daily rate
    - Late → prorated hourly rate
    """
    attendance_logs = Attendance.objects.filter(
        employee=employee,
        date__year=year,
        date__month=month,
        date__day__gte=start_day,
        date__day__lte=end_day,
    )

    total_deduction = Decimal("0.00")
    for att in attendance_logs:
        total_deduction += att.compute_deduction(daily_rate, hourly_rate)

    return total_deduction
