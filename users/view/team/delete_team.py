from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from ...models import Team
from ..utils import isHR


@login_required
@user_passes_test(isHR)
def delete_team(request: HttpRequest, pk: int) -> HttpResponse:
    team = get_object_or_404(Team, pk=pk)
    if request.method == "POST":
        team.delete()
        messages.success(request, "Team deleted successfully!")
        return redirect("users:team_list")
    return render(request, "team/delete_team.html", {"team": team})
