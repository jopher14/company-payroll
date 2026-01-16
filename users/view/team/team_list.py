from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from ...models import Team
from ..utils import isHR


@login_required
@user_passes_test(isHR)
def team_list(request: HttpRequest) -> HttpResponse:
    teams = Team.objects.all().order_by('-created_at')
    return render(request, "team/team_list.html", {"teams": teams})
