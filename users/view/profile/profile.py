from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from ..utils import castUser


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    user = castUser(request)  # Get the logged-in user
    return render(request, "users/profile.html", {"user": user})
