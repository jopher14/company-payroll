from django.http import HttpRequest, HttpResponse
from django.contrib.auth import logout
from django.shortcuts import render


def logoutView(request: HttpRequest) -> HttpResponse:
    logout(request)
    return render(request, 'users/logout.html')
