from django.urls import path
from . import views

app_name = "payroll"

urlpatterns = [
    path("my-payslips/", views.my_payslips, name="my_payslips"),
    path("payslip/<int:payslip_id>/", views.view_payslip, name="view_payslip"),
]
