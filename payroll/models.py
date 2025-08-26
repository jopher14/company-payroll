from django.db import models
from django.conf import settings

class Payslip(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="payslips"
    )
    month = models.CharField(max_length=20)  # e.g., "August 2025"
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.net_salary = self.basic_salary + self.allowances - self.deductions
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payslip: {self.employee.username} - {self.month}"
