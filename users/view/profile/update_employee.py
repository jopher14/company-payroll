from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from ..utils import isHR
from ...models import User
from ...forms import EmployeeUpdateForm


@login_required
@user_passes_test(isHR)
def update_employee(request: HttpRequest, pk) -> HttpResponse:
    employee = get_object_or_404(User, pk=pk)
    form = EmployeeUpdateForm(request.POST or None, request.FILES or None, instance=employee)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect('users:employee_list')

    # Get team whether employee, supervisor, or manager
    teams = employee.teams.all() | employee.supervised_teams.all() | employee.managed_teams.all()

    return render(request, 'users/update_employee.html', {
        'form': form,
        'employee': employee,
        'teams': teams.distinct(),
    })
