from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from users.forms import UserRegistrationForm


@login_required
def register(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User: {user.username} registered successfully!")
            return redirect("users:employee_list")
    else:
        form = UserRegistrationForm()
    return render(request, "users/register.html", {"form": form})
