from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from ...models import Team
from ...forms import TeamForm
from ..utils import isHR


@login_required
@user_passes_test(isHR)
def edit_team(request: HttpRequest, pk: int) -> HttpResponse:
    team = get_object_or_404(Team, pk=pk)
    if request.method == "POST":
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            messages.success(request, f"Team '{team.name}' updated successfully!")
            return redirect("users:team_list")
    else:
        form = TeamForm(instance=team)
    return render(request, "team/edit_team.html", {"form": form, "team": team})
