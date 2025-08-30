from django.shortcuts import render, get_object_or_404
from .models import Payslip
from users.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpRequest


@login_required
def my_payslips(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        # Should never happen because of @login_required
        return HttpResponse("Invalid user", status=400)

    payslips = Payslip.objects.filter(employee=user).order_by('-generated_at')
    return render(request, "payroll/my_payslips.html", {"payslips": payslips})


@login_required
def view_payslip(request: HttpRequest, payslip_id) -> HttpResponse:
    payslip = get_object_or_404(Payslip, id=payslip_id, employee=request.user)
    return render(request, "payroll/view_payslip.html", {"payslip": payslip})
