from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from ...forms import TeamForm
from ..utils import isHR


@login_required
@user_passes_test(isHR)
def create_team(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            team.created_by = request.user
            team.save()
            form.save_m2m()
            messages.success(request, f"Team '{team.name}' created successfully!")
            return redirect("users:team_list")
    else:
        form = TeamForm()
    return render(request, "team/create_team.html", {"form": form})
