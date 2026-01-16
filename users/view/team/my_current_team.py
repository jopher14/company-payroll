from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from ...models import Team
from django.db.models import Q


@login_required
def my_current_team(request: HttpRequest) -> HttpResponse:
    user = request.user

    # Get all teams where the user is a member (employee, supervisor, or manager)
    teams = Team.objects.filter(
        Q(employees=user) | Q(supervisor=user) | Q(manager=user)
    ).distinct()

    return render(request, "team/my_current_team.html", {"teams": teams})
