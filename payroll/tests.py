# from decimal import Decimal
# from django.test import TestCase
# from django.contrib.auth import get_user_model
# from payroll.models import Payroll
# from users.models import Loan
# from payroll.views import compute_loan_deduction

# User = get_user_model()

# class PayslipLoanDeductionTests(TestCase):
#     def setUp(self):
#         # Create an employee
#         self.employee = User.objects.create_user(
#             username="employee1",
#             password="password123",
#             first_name="John",
#             last_name="Doe",
#             salary=Decimal("30000.00"),
#             role="employee"
#         )

#     def create_loan(self, loan_type, amount, loan_deduct, balance, is_active=True):
#         return Loan.objects.create(
#             employee=self.employee,
#             loan_type=loan_type,
#             amount=Decimal(amount),
#             loan_deduct=Decimal(loan_deduct),
#             balance=Decimal(balance),
#             term_months=12,
#             is_active=is_active
#         )

#     def test_no_loans(self):
#         loan_deduct, breakdown, summary = compute_loan_deduction(self.employee, {"month": "October", "year": 2025})
#         self.assertEqual(loan_deduct, 0.0)
#         self.assertEqual(breakdown, {})
#         self.assertEqual(summary, {})

#     def test_personal_loan_deduction(self):
#         self.create_loan("Personal Loan", "10000.00", "1000.00", "10000.00")
#         loan_deduct, breakdown, summary = compute_loan_deduction(self.employee, {"month": "October", "year": 2025})
#         self.assertAlmostEqual(loan_deduct, 500.0)
#         self.assertEqual(summary.get("Personal Loan"), 500.0)
#         self.assertIn("Personal Loan", breakdown)

#     def test_multiple_personal_loans(self):
#         self.create_loan("Personal Loan", "8000.00", "800.00", "8000.00")
#         self.create_loan("Personal Loan", "5000.00", "500.00", "5000.00")
#         loan_deduct, breakdown, summary = compute_loan_deduction(self.employee, {"month": "October", "year": 2025})
#         self.assertAlmostEqual(loan_deduct, 650.0)
#         self.assertEqual(summary.get("Personal Loan"), 650.0)

#     def test_government_loans_excluded(self):
#         self.create_loan("SSS Loan", "10000.00", "1000.00", "10000.00")
#         loan_deduct, breakdown, summary = compute_loan_deduction(self.employee, {"month": "October", "year": 2025})
#         self.assertEqual(loan_deduct, 500.0)
#         self.assertNotIn("SSS Loan", summary)
#         self.assertIn("Government Deductions", summary)

#     def test_both_personal_and_government_loans(self):
#         self.create_loan("Personal Loan", "10000.00", "1000.00", "10000.00")
#         self.create_loan("Pag-IBIG Loan", "5000.00", "500.00", "5000.00")
#         loan_deduct, breakdown, summary = compute_loan_deduction(self.employee, {"month": "October", "year": 2025})
#         self.assertAlmostEqual(loan_deduct, 750.0)
#         self.assertEqual(summary.get("Personal Loan"), 500.0)
#         self.assertEqual(summary.get("Government Deductions"), 250.0)

#     def test_loan_paid_off(self):
#         loan = self.create_loan("Personal Loan", "1000.00", "1000.00", "500.00")
#         loan_deduct, breakdown, summary = compute_loan_deduction(self.employee, {"month": "October", "year": 2025})
#         self.assertAlmostEqual(loan_deduct, 250.0)
#         loan.refresh_from_db()
#         self.assertFalse(loan.is_active)
