# payroll/utils.py
from decimal import Decimal


def compute_sss(salary: Decimal) -> Decimal:
    # Example: fixed range contribution
    if salary < Decimal("3250"):
        return Decimal("135.00")
    elif salary < Decimal("24750"):
        return salary * Decimal("0.045")  # 4.5%
    else:
        return Decimal("1125.00")


def compute_philhealth(salary: Decimal) -> Decimal:
    # 5% monthly premium split employee/employer (2024 rate)
    base = min(max(salary, Decimal("10000")), Decimal("90000"))
    return (base * Decimal("0.05")) / Decimal("2")


def compute_pagibig(salary: Decimal) -> Decimal:
    # 2% capped at ₱100 for employee share
    return min(salary * Decimal("0.02"), Decimal("100.00"))


def compute_withholding_tax(salary: Decimal) -> Decimal:
    # Simplified BIR TRAIN table (monthly)
    if salary <= Decimal("20833"):
        return Decimal("0.00")
    elif salary <= Decimal("33332"):
        return (salary - Decimal("20833")) * Decimal("0.15")
    elif salary <= Decimal("66666"):
        return Decimal("1875") + (salary - Decimal("33333")) * Decimal("0.20")
    elif salary <= Decimal("166666"):
        return Decimal("8541.80") + (salary - Decimal("66667")) * Decimal("0.25")
    elif salary <= Decimal("666666"):
        return Decimal("33541.80") + (salary - Decimal("166667")) * Decimal("0.30")
    else:
        return Decimal("183541.80") + (salary - Decimal("666667")) * Decimal("0.35")
