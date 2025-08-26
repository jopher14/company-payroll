from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Leave, Attendance, Schedule


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2", "role")  # include role


class EmployeeRegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.EMPLOYEE  # auto-assign role
        if commit:
            user.save()
        return user


class UserRegistrationForm(UserCreationForm):
    """For HR creating users with Employee ID"""
    employee_id = forms.CharField(
        max_length=20,
        required=True,
        label="Employee ID",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Employee ID"})
    )

    class Meta:
        model = User
        fields = ["employee_id", "username", "email", "role", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})

    def clean_employee_id(self):
        """Ensure employee_id is unique"""
        employee_id = self.cleaned_data.get("employee_id")
        if User.objects.filter(employee_id=employee_id).exists():
            raise forms.ValidationError("This Employee ID is already registered.")
        return employee_id


class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ["start_date", "end_date", "reason"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ["time_in", "time_out"]
        widgets = {
            "time_in": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "time_out": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
        }


TIME_CHOICES = [(f"{h:02d}:{m:02d}", f"{h:02d}:{m:02d}") for h in range(0, 24) for m in (0, 30)]

class ScheduleForm(forms.ModelForm):
    time_in = forms.ChoiceField(choices=TIME_CHOICES, label="Time In")
    time_out = forms.ChoiceField(choices=TIME_CHOICES, label="Time Out")
    class Meta:
        model = Schedule
        fields = ['employee', 'time_in', 'time_out']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only Supervisors and Employees in dropdown
        self.fields['employee'].queryset = User.objects.filter(role__in=['supervisor', 'employee'], is_superuser=False)


class EmployeeUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'role', 'birthday', 'contact_number',
            'status', 'employee_id', 'photo',
            'sss', 'tin', 'pagibig', 'philhealth'
        ]
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'birthday': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),

            'sss': forms.TextInput(attrs={'class': 'form-control'}),
            'tin': forms.TextInput(attrs={'class': 'form-control'}),
            'pagibig': forms.TextInput(attrs={'class': 'form-control'}),
            'philhealth': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude admin role
        self.fields['role'].choices = [
            (role, label) for role, label in self.fields['role'].choices if role != 'admin'
        ]
