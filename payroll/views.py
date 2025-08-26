from django.shortcuts import render, get_object_or_404
from .models import Payslip
from django.contrib.auth.decorators import login_required

@login_required
def my_payslips(request):
    payslips = Payslip.objects.filter(employee=request.user).order_by('-generated_at')
    return render(request, "payroll/my_payslips.html", {"payslips": payslips})

@login_required
def view_payslip(request, payslip_id):
    payslip = get_object_or_404(Payslip, id=payslip_id, employee=request.user)
    return render(request, "payroll/view_payslip.html", {"payslip": payslip})
