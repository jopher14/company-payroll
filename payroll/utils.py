from collections import defaultdict
from calendar import monthrange
from decimal import Decimal
from users.models import Attendance, Overtime, Loan
from typing import Optional
from datetime import date


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


def compute_overtime_hours(employee, year: int, month: int, start_day: int, end_day: int) -> dict[str, Decimal]:
    """
    Fetch total approved overtime hours grouped by OT type for an employee in a cutoff period.
    Returns a dict like: {"ordinary": 5, "restday": 2, "special_holiday": 3}
    """
    last_day = monthrange(year, month)[1]
    start_date = date(year, month, min(start_day, last_day))
    end_date = date(year, month, min(end_day, last_day))

    overtime_logs = Overtime.objects.filter(
        employee=employee,
        date__range=(start_date, end_date),
        status="approved",
    )

    hours_by_type: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for ot in overtime_logs:
        ot_type = getattr(ot, "ot_type", "ordinary")  # default if no field
        hours_by_type[ot_type] += Decimal(ot.hours or 0)

    return hours_by_type


def compute_overtime_pay(hourly_rate: Decimal, hours: Decimal, multiplier: Decimal) -> Decimal:
    """Compute OT pay given hours, rate, and multiplier."""
    return (hours * hourly_rate * multiplier).quantize(Decimal("0.01"))


# 💡 Specialized computations
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


def compute_employee_overtime(
    employee,
    year: int,
    month: int,
    start_day: int,
    end_day: int,
    hourly_rate: Decimal,
) -> Decimal:
    """
    Compute total overtime pay for an employee in a cutoff period.
    Uses the OT type to apply correct multipliers.
    """
    hours_by_type = compute_overtime_hours(employee, year, month, start_day, end_day)

    total_pay = Decimal("0.00")

    total_pay += compute_ordinary_ot(hourly_rate, hours_by_type.get("ordinary", Decimal("0.00")))
    total_pay += compute_restday_ot(hourly_rate, hours_by_type.get("restday", Decimal("0.00")))
    total_pay += compute_special_holiday_ot(hourly_rate, hours_by_type.get("special_holiday", Decimal("0.00")))
    total_pay += compute_special_holiday_restday_ot(hourly_rate, hours_by_type.get("special_holiday_restday", Decimal("0.00")))
    total_pay += compute_regular_holiday_ot(hourly_rate, hours_by_type.get("regular_holiday", Decimal("0.00")))
    total_pay += compute_regular_holiday_restday_ot(hourly_rate, hours_by_type.get("regular_holiday_restday", Decimal("0.00")))
    total_pay += compute_double_holiday_ot(hourly_rate, hours_by_type.get("double_holiday", Decimal("0.00")))
    total_pay += compute_double_holiday_restday_ot(hourly_rate, hours_by_type.get("double_holiday_restday", Decimal("0.00")))

    return total_pay


def compute_total_attendance_deduction(
    employee,
    year: int,
    month: int,
    start_day: int,
    end_day: int,
    daily_rate: Decimal,
    hourly_rate: Decimal,
    holidays: Optional[set] = None,
) -> tuple[Decimal, list[dict]]:
    """
    Compute total attendance deductions for a given employee in a cutoff period.
    Rules:
      - Absent → 1 daily rate
      - Half Day → 0.5 daily rate
      - Late / Undertime → prorated per minute
      - Skips weekends & holidays
    """
    import calendar
    from datetime import date, datetime, timedelta

    # Clamp cutoff to valid month days
    last_day = calendar.monthrange(year, month)[1]
    start_day, end_day = min(start_day, last_day), min(end_day, last_day)
    start_date, end_date = date(year, month, start_day), date(year, month, end_day)

    total_deduction = Decimal("0.00")
    breakdown: list[dict] = []

    # Derived rates
    hourly_rate = hourly_rate or (daily_rate / Decimal("8")) if daily_rate > 0 else Decimal("0")
    per_minute_rate = hourly_rate / Decimal(60) if hourly_rate > 0 else Decimal("0")

    # Prefetch attendance
    attendances = {
        att.date: att
        for att in Attendance.objects.filter(employee=employee, date__range=(start_date, end_date))
    }

    def add_breakdown(day, reasons, amount):
        """Helper to append breakdown logs."""
        breakdown.append({
            "date": day.isoformat(),
            "reason": ", ".join(reasons),
            "deduction": str(amount.quantize(Decimal("0.01")))
        })

    # Loop through cutoff days
    for i in range((end_date - start_date).days + 1):
        day = start_date + timedelta(days=i)

        # Skip weekends & holidays
        if day.weekday() >= 5 or (holidays and day in holidays):
            continue

        att = attendances.get(day)
        day_total, reasons = Decimal("0.00"), []

        if not att or not att.time_in:
            # No attendance record or missing time_in → Absent
            day_total, reasons = daily_rate, ["Absent"]
        else:
            # Half day / missing time_out
            if getattr(att, "half_day", False) or not att.time_out:
                day_total += daily_rate / 2
                reasons.append("Half-day")

            # Late / Undertime
            if att.schedule:
                # Late
                if att.schedule.time_in and att.time_in:
                    scheduled_start = datetime.combine(att.date, att.schedule.time_in)
                    actual_start = datetime.combine(att.date, att.time_in)
                    if actual_start > scheduled_start:
                        minutes_late = (actual_start - scheduled_start).seconds // 60
                        if minutes_late > 0:
                            day_total += per_minute_rate * Decimal(minutes_late)
                            reasons.append(f"Late {minutes_late}m")

                # Undertime
                if att.schedule.time_out and att.time_out:
                    scheduled_out = datetime.combine(att.date, att.schedule.time_out)
                    actual_out = datetime.combine(att.date, att.time_out)
                    if actual_out < scheduled_out:
                        minutes_undertime = (scheduled_out - actual_out).seconds // 60
                        if minutes_undertime > 0:
                            day_total += per_minute_rate * Decimal(minutes_undertime)
                            reasons.append(f"Undertime {minutes_undertime}m")

        if day_total > 0:
            add_breakdown(day, reasons, day_total)
            total_deduction += day_total

    return total_deduction.quantize(Decimal("0.01")), breakdown


def compute_loan_deduction(employee, period):
    """
    Compute total personal loan deductions (split semi-monthly).
    Government loans are excluded from this calculation.

    Returns:
        total_deduction (Decimal)
        breakdown (dict)
        loan_type_summary (dict)
    """
    loans = Loan.objects.filter(employee=employee, is_active=True)
    total_deduction = Decimal("0.00")
    breakdown = {}
    loan_type_summary = {}

    for loan in loans:
        deduction = Decimal("0.00")
        reason = ""

        # Skip government loans
        if loan.loan_type.lower() in ["sss loan", "pag-ibig loan", "philhealth loan"]:
            continue

        if loan.loan_deduct and loan.loan_deduct > 0:
            # Split deduction for semi-monthly
            deduction = (loan.loan_deduct / Decimal("2.00")).quantize(Decimal("0.01"))
            reason = "Manual loan_deduct split (semi-monthly)"
        else:
            reason = "No deduction set"

        # Update loan balance
        loan.balance -= deduction
        if loan.balance <= Decimal("0.00"):
            loan.is_active = False
        loan.save(update_fields=["balance", "is_active"])

        total_deduction += deduction

        breakdown[loan.loan_type] = {
            "amount": float(deduction),
            "reason": reason,
        }

        loan_type_summary[loan.loan_type] = float(
            loan_type_summary.get(loan.loan_type, Decimal("0.00")) + deduction
        )

    return total_deduction, breakdown, loan_type_summary
