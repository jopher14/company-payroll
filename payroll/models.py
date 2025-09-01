from django.db import models
from users.models import User


class Payroll(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sss = models.DecimalField(max_digits=10, decimal_places=2)
    philhealth = models.DecimalField(max_digits=10, decimal_places=2)
    pagibig = models.DecimalField(max_digits=10, decimal_places=2)
    withholding_tax = models.DecimalField(max_digits=10, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # ✅ Automatically compute deductions and net pay
        self.total_deductions = (
            self.sss + self.philhealth + self.pagibig + self.withholding_tax
        )
        self.net_pay = self.basic_salary + self.allowances - self.total_deductions
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payroll: {self.employee.username} - {self.created_at.strftime('%B %Y')}"
