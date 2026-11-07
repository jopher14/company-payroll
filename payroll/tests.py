from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from users.models import Attendance, Loan, Overtime, User

from .models import Payroll


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class PayrollTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.employee = User.objects.create_user(username="employee", salary=Decimal("22000.00"))
        cls.coworker = User.objects.create_user(username="coworker", salary=Decimal("22000.00"))
        cls.hr = User.objects.create_user(username="hr", role=User.HUMAN_RESOURCES)

    def add_loan(self, balance, monthly_due):
        return Loan.objects.create(
            employee=self.employee,
            loan_amount=Decimal("1200.00"),
            balance=Decimal(balance),
            loan_deduct=Decimal(monthly_due),
            start_date=date(2026, 1, 1),
        )

    def generate(self, period="first_half"):
        self.client.force_login(self.hr)
        with patch("payroll.views.timezone.localdate", return_value=date(2026, 1, 31)):
            response = self.client.post(reverse("payroll:generate_payroll"), {"period": period})
        self.assertRedirects(response, reverse("payroll:payroll_list"), fetch_redirect_response=False)

    def test_employee_cannot_register_an_hr_user(self):
        self.client.force_login(self.employee)
        url = reverse("users:register")
        data = {
            "username": "new-hr",
            "email": "new-hr@example.com",
            "role": User.HUMAN_RESOURCES,
            "password1": "Strong-form-test-518!",
            "password2": "Strong-form-test-518!",
        }
        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertFalse(User.objects.filter(username="new-hr").exists())

        self.client.force_login(self.hr)
        self.assertRedirects(
            self.client.post(url, data), reverse("users:employee_list"), fetch_redirect_response=False
        )
        self.assertEqual(User.objects.get(username="new-hr").role, User.HUMAN_RESOURCES)

    def test_payslip_is_visible_only_to_owner_and_hr(self):
        slip = Payroll.objects.create(employee=self.employee, year=2026, month=1, period="first_half")
        url = reverse("payroll:view_payslip", args=[slip.pk])

        self.client.force_login(self.coworker)
        self.assertEqual(self.client.get(url).status_code, 404)

        for viewer in (self.employee, self.hr):
            with self.subTest(viewer=viewer):
                self.client.force_login(viewer)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["payslip"], slip)

    def test_generation_posts_one_capped_payment_per_loan(self):
        first = self.add_loan("1000.00", "100.01")
        second = self.add_loan("20.00", "100.00")
        self.generate()
        self.generate()

        slip = Payroll.objects.get(employee=self.employee, year=2026, month=1, period="first_half")
        self.assertEqual(slip.loan_deduction, Decimal("70.01"))
        self.assertEqual(slip.loan_type_summary, {"personal": 70.01})
        self.assertEqual(len(slip.loan_breakdown), 2)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.balance, Decimal("949.99"))
        self.assertEqual(second.balance, Decimal("0.00"))
        self.assertFalse(second.is_active)

        self.generate("second_half")
        first.refresh_from_db()
        self.assertEqual(first.balance, Decimal("899.99"))

    def test_payslip_reads_and_resaving_payroll_do_not_pay_loans(self):
        loan = self.add_loan("1000.00", "100.00")
        self.generate()
        slip = Payroll.objects.get(employee=self.employee)
        slip.save()
        self.client.force_login(self.employee)
        detail = reverse("payroll:view_payslip", args=[slip.pk])
        for url in (detail, reverse("payroll:my_payslips"), detail):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["payslip"].loan_deduction, Decimal("50.00"))
        loan.refresh_from_db()
        self.assertEqual(loan.balance, Decimal("950.00"))

    def test_generation_preserves_approved_overtime_and_worked_holiday_pay(self):
        for day in (date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 16)):
            Attendance.objects.create(employee=self.employee, date=day, time_in=time(8), time_out=time(17))
        for status in ("approved", "pending"):
            Overtime.objects.create(
                employee=self.employee,
                date=date(2026, 1, 1),
                hours=Decimal("2.00"),
                overtime_type="regular_holiday",
                status=status,
            )
        with patch("payroll.views.Philippines", return_value=dict.fromkeys([
            date(2026, 1, 1), date(2026, 1, 3), date(2026, 1, 16)
        ])):
            self.generate()

        slip = Payroll.objects.get(employee=self.employee)
        self.assertEqual(slip.daily_rate, Decimal("1000.00"))
        self.assertEqual(slip.overtime_pay, Decimal("650.00"))
        self.assertEqual(slip.holiday_pay, Decimal("1000.00"))
        self.assertEqual(slip.gross_salary, slip.basic_salary + slip.allowances + Decimal("1650.00"))
        self.assertEqual(slip.net_pay, slip.gross_salary - slip.total_deductions)
