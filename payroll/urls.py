from django.urls import path
from . import views

app_name = "payroll"

urlpatterns = [
    path(route="", view=views.payroll_list, name="payroll_list"),
    path(route="my-payslips/", view=views.my_payslips, name="my_payslips"),
    path(route="generate/", view=views.generate_payroll, name="generate_payroll"),
    path(route='payslip/<int:pk>/', view=views.view_payslip, name='view_payslip'),

]
