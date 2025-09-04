from django import forms


class PayrollGenerationForm(forms.Form):
    PERIOD_CHOICES = [
        ("1st Half", "1st Half (1–15)"),
        ("2nd Half", "2nd Half (16–end)"),
    ]
    period = forms.ChoiceField(choices=PERIOD_CHOICES, label="Payroll Period")
