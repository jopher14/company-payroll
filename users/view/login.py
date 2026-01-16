from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


def loginView(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("main:dashboard")
        else:
            messages.error(request, "Invalid credentials. Please try again.")
    else:
        form = AuthenticationForm()

    return render(request, "users/login.html", {"form": form})
