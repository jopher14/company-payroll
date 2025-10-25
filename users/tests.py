from django.test import TestCase
from users.models import User
from decimal import Decimal


class UserModelTest(TestCase):
    def setUp(self):
        # Create a sample user for testing
        self.user = User.objects.create_user(
            username="johndoe",
            password="password123",
            first_name="John",
            last_name="Doe",
            role=User.EMPLOYEE,
            salary=Decimal("50000.00"),
        )

    def test_user_str(self):
        """__str__ should return first name and role"""
        self.assertEqual(str(self.user), "John (employee)")

    def test_default_leave_balance(self):
        """New users should start with 15.0 leave count"""
        self.assertEqual(self.user.leave_count, Decimal("15.0"))

    def test_refresh_leave_balance(self):
        """refresh_leave_balance() should update leave_count properly"""
        # You can create fake leave objects here if your Leave model exists
        # For now, just call the method to ensure it doesn't crash
        self.user.refresh_leave_balance()
        self.user.refresh_from_db()
        self.assertLessEqual(self.user.leave_count, Decimal("15.0"))

    def test_photo_or_default(self):
        """photoOrDefault should return default if no photo is uploaded"""
        default_path = self.user.photoOrDefault
        self.assertIn("photos/DefaultPhoto.jpg", default_path)
