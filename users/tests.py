from django.test import TestCase
from datetime import date, time, timedelta
from decimal import Decimal

from .models import User, Leave, Attendance, Day, Schedule, Overtime, Loan


class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="john",
            password="test123",
            first_name="John",
            last_name="Doe",
            role=User.EMPLOYEE,
            salary=Decimal("20000.00")
        )

    def test_user_string(self):
        self.assertEqual(str(self.user), "John (employee)")

    def test_refresh_leave_balance(self):
        leave = Leave.objects.create(
            employee=self.user,
            start_date=date.today(),
            end_date=date.today(),
            leave_type=Leave.WHOLE_DAY,
            reason="Vacation",
            status=Leave.APPROVED,
        )

        self.user.refresh_leave_balance()

        # ✅ Use `leave` to satisfy Flake8 and make test clearer
        self.assertTrue(Leave.objects.filter(pk=leave.pk, status=Leave.APPROVED).exists())
        self.assertLess(self.user.leave_count, Decimal("15.0"))


class AttendanceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mary", password="test123")
        self.day_mon = Day.objects.create(number=1, name="Mon")
        self.schedule = Schedule.objects.create(
            employee=self.user,
            time_in=time(8, 0),
            time_out=time(17, 0),
        )
        self.schedule.days_of_week.add(self.day_mon)

    def test_status_present(self):
        att = Attendance.objects.create(
            employee=self.user,
            date=date.today(),
            time_in=time(8, 0),
            time_out=time(17, 0)
        )
        self.assertEqual(att.status, "Present")

    def test_status_late(self):
        att = Attendance.objects.create(
            employee=self.user,
            date=date.today(),
            time_in=time(8, 30),
            time_out=time(17, 0)
        )
        self.assertEqual(att.status, "Late")
        self.assertGreater(att.late_hours, Decimal("0.00"))

    def test_compute_deduction_absent(self):
        att = Attendance.objects.create(employee=self.user, date=date.today())
        deduction = att.compute_deduction(daily_rate=Decimal("1000"))
        self.assertEqual(deduction, Decimal("1000"))


class LeaveModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="kate", password="123")
        self.leave = Leave.objects.create(
            employee=self.user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            leave_type=Leave.WHOLE_DAY,
            reason="Trip",
        )

    def test_total_days(self):
        self.assertEqual(self.leave.total_days(), 3.0)

    def test_half_day_leave(self):
        leave = Leave.objects.create(
            employee=self.user,
            start_date=date.today(),
            end_date=date.today(),
            leave_type=Leave.HALF_DAY,
            reason="Errand",
        )
        self.assertEqual(leave.total_days(), 0.5)


class OvertimeModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bob", password="pass123")
        self.ot = Overtime.objects.create(
            employee=self.user,
            date=date.today(),
            hours=Decimal("2.0"),
            overtime_type="ordinary"
        )

    def test_calculate_pay(self):
        pay = self.ot.calculate_pay(hourly_rate=100)
        self.assertEqual(pay, 250.0)  # 2 hrs * 100 * 1.25


class LoanModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="loan_user", password="abc123")

    def test_auto_fields_on_save(self):
        loan = Loan.objects.create(
            employee=self.user,
            loan_type="personal",
            loan_amount=Decimal("12000.00"),
            start_date=date(2025, 1, 1),
            term_months=12
        )
        self.assertEqual(loan.balance, Decimal("12000.00"))
        self.assertIsNotNone(loan.end_date)
        self.assertGreater(loan.loan_deduct, Decimal("0.00"))
