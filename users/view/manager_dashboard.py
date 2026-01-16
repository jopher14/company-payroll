from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from ..models import User


@login_required
def manager_dashboard(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        return HttpResponseForbidden("You are not allowed to access this page.")

    if user.role != User.MANAGER:
        return HttpResponseForbidden("You are not allowed to access this page.")

    return render(request, "manager_dashboard.html", {"user": user})
