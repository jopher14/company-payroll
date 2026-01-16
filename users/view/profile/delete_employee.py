from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from ..utils import isHR
from ...models import User


@login_required
@user_passes_test(isHR)
def delete_employee(request: HttpRequest, pk) -> HttpResponse:
    employee = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        employee.delete()
        messages.success(request, "Employee deleted successfully.")
        return redirect("users:employee_list")

    messages.error(request, "Invalid request.")
    return redirect("users:employee_list")
