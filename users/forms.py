from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Leave, Attendance, Schedule, Overtime


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "role")  # include role


class EmployeeRegistrationForm(UserCreationForm):
    class Meta:
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

    class Meta:
        model = User
        fields = ["username", "email", "role", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


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
            'status', 'photo',
            'sss', 'tin', 'pagibig', 'philhealth', 'salary'
        ]
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'birthday': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),

            'sss': forms.TextInput(attrs={'class': 'form-control'}),
            'tin': forms.TextInput(attrs={'class': 'form-control'}),
            'pagibig': forms.TextInput(attrs={'class': 'form-control'}),
            'philhealth': forms.TextInput(attrs={'class': 'form-control'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

    def clean_salary(self):
        salary = self.cleaned_data.get('salary')
        if isinstance(salary, str):
            salary = salary.replace(',', '')
        return salary

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude admin role
        self.fields['role'].choices = [
            (role, label) for role, label in self.fields['role'].choices if role != 'admin'
        ]


class OvertimeForm(forms.ModelForm):
    class Meta:
        model = Overtime
        fields = ["date", "hours", "reason"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "hours": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.25",
                "placeholder": "Enter total hours (e.g., 1.5, 2, 4.25)"
            }),
            "reason": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter reason for overtime"
            }),
        }
