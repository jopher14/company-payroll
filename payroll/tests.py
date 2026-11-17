from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from payroll.models import Payroll
from users.models import Attendance, Loan, Overtime, User


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class PayrollRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hr = User.objects.create_user(username="hr", role=User.HUMAN_RESOURCES)
        cls.employee = User.objects.create_user(username="employee", salary=Decimal("17600.00"))
        cls.other_employee = User.objects.create_user(username="other")

    def sign_in(self, user, client=None):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session["login_token"] = str(user.login_token)
        session.save()
        return client

    def add_loan(self, balance):
        return Loan.objects.create(
            employee=self.employee,
            loan_type="personal",
            loan_amount=Decimal("1200.00"),
            balance=Decimal(balance),
            start_date=date(2026, 1, 1),
        )

    def generate_payroll(self):
        with patch("payroll.views.timezone.localdate", return_value=date(2026, 1, 15)):
            return self.client.post(reverse("payroll:generate_payroll"), {"period": "first_half"})

    def test_generation_preserves_overtime_and_charges_loans_once(self):
        first_loan = self.add_loan("30.00")
        second_loan = self.add_loan("100.00")
        Overtime.objects.create(
            employee=self.employee,
            date=date(2026, 1, 9),
            hours=Decimal("2.00"),
            overtime_type="restday",
            status="approved",
        )
        self.sign_in(self.hr)
        self.assertRedirects(
            self.generate_payroll(), reverse("payroll:payroll_list"), fetch_redirect_response=False,
        )
        payroll = Payroll.objects.get(employee=self.employee)
        self.assertEqual(payroll.overtime_pay, Decimal("338.00"))
        self.assertEqual(payroll.loan_deduction, Decimal("80.00"))
        self.assertEqual(Decimal(payroll.loan_type_summary["personal"]), Decimal("80.00"))
        self.assertEqual(payroll.net_pay, payroll.gross_salary - payroll.total_deductions)

        self.generate_payroll()
        self.assertEqual(Payroll.objects.filter(employee=self.employee).count(), 1)
        self.sign_in(self.employee)
        detail = reverse("payroll:view_payslip", args=[payroll.pk])
        for _ in range(2):
            self.assertContains(self.client.get(detail), "338.00")
            self.assertEqual(self.client.get(reverse("payroll:my_payslips")).status_code, 200)

        first_loan.refresh_from_db()
        second_loan.refresh_from_db()
        self.assertEqual(first_loan.balance, Decimal("0.00"))
        self.assertFalse(first_loan.is_active)
        self.assertEqual(second_loan.balance, Decimal("50.00"))

    def test_generation_failure_rolls_back_loan_and_payroll(self):
        loan = self.add_loan("100.00")
        self.sign_in(self.hr)
        bulk_update = Loan.objects.bulk_update

        def fail_after_update(*args, **kwargs):
            bulk_update(*args, **kwargs)
            raise RuntimeError("Simulated failure after writing loans")

        with patch("payroll.views.Loan.objects.bulk_update", side_effect=fail_after_update):
            with self.assertRaisesMessage(RuntimeError, "Simulated failure"):
                self.generate_payroll()

        loan.refresh_from_db()
        self.assertEqual(loan.balance, Decimal("100.00"))
        self.assertFalse(Payroll.objects.exists())

    def test_payslip_requires_owner_or_hr(self):
        payroll = Payroll.objects.create(
            employee=self.employee, year=2026, month=1, period="first_half",
        )
        detail = reverse("payroll:view_payslip", args=[payroll.pk])
        self.sign_in(self.other_employee)
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.sign_in(self.employee)
        self.assertEqual(self.client.get(detail).status_code, 200)
        self.sign_in(self.hr)
        self.assertEqual(self.client.get(detail).status_code, 200)

    def test_registration_requires_hr(self):
        self.sign_in(self.employee)
        data = {
            "username": "new_hr",
            "email": "new-hr@example.com",
            "role": User.HUMAN_RESOURCES,
            "password1": "Secure-password-123",
            "password2": "Secure-password-123",
        }
        register = reverse("users:register")
        self.assertEqual(self.client.post(register, data).status_code, 403)
        self.assertFalse(User.objects.filter(username="new_hr").exists())
        self.sign_in(self.hr)
        self.assertEqual(self.client.post(register, data).status_code, 302)
        self.assertEqual(User.objects.get(username="new_hr").role, User.HUMAN_RESOURCES)

    def test_attendance_delete_requires_hr_post_and_csrf(self):
        attendance = Attendance.objects.create(
            employee=self.employee, date=date(2026, 1, 9), time_in=time(8), time_out=time(17),
        )
        delete = reverse("users:delete_attendance", args=[attendance.pk])
        manage = reverse("users:manage_attendance")
        self.sign_in(self.other_employee)
        self.assertEqual(self.client.post(delete).status_code, 403)
        self.assertEqual(self.client.post(manage).status_code, 403)

        client = self.sign_in(self.hr, Client(enforce_csrf_checks=True))
        self.assertEqual(client.get(delete).status_code, 405)
        self.assertEqual(client.post(delete).status_code, 403)
        self.assertTrue(Attendance.objects.filter(pk=attendance.pk).exists())
        self.assertEqual(client.get(manage).status_code, 200)
        token = client.cookies["csrftoken"].value
        self.assertRedirects(client.post(delete, {"csrfmiddlewaretoken": token}), manage)
        self.assertFalse(Attendance.objects.filter(pk=attendance.pk).exists())
