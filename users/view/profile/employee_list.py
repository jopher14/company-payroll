import json
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from ...models import User
from django.core.serializers.json import DjangoJSONEncoder


@login_required
def employee_list(request: HttpRequest) -> HttpResponse:

    # Fetch all employees except superuser
    employees_qs = (
        User.objects.exclude(is_superuser=True)
        .select_related()
        .prefetch_related("teams", "supervised_teams", "managed_teams")
        .distinct()
    )

    # Build the JSON list for React
    employees_json = json.dumps([
        {
            "id": emp.id,
            "full_name": emp.get_full_name() or emp.username,
            "role": emp.get_role_display(),
            "team": ", ".join({
                t.name
                for t in (
                    list(emp.teams.all())
                    + list(emp.supervised_teams.all())
                    + list(emp.managed_teams.all())
                )
            }) or "No Team Assigned",
            "status": emp.status,
        }
        for emp in employees_qs
    ], cls=DjangoJSONEncoder)

    return render(request, "users/employee_list.html", {
        "employees_json": employees_json
    })
