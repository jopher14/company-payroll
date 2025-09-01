from decimal import Decimal
from users.models import User
from .models import Payroll


def compute_payroll(user: User) -> Payroll:
    salary = user.salary or Decimal("0.00")

    # Simplified PH contributions (sample only)
    sss = salary * Decimal("0.045")   # 4.5%
    philhealth = salary * Decimal("0.03")  # 3%
    pagibig = min(salary * Decimal("0.02"), Decimal("100.00"))  # 2% capped at 100
    withholding_tax = salary * Decimal("0.10")  # assume flat 10% for demo

    total_deductions = sss + philhealth + pagibig + withholding_tax
    net_pay = salary - total_deductions

    payroll = Payroll.objects.create(
        employee=user,
        basic_salary=salary,
        sss=sss,
        philhealth=philhealth,
        pagibig=pagibig,
        withholding_tax=withholding_tax,
        net_pay=net_pay,
    )
    return payroll
