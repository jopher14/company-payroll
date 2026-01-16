from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from ...models import User, Leave


@login_required
def my_leaves(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        # This should never happen because of @login_required
        return HttpResponse("Invalid user", status=400)

    leaves = Leave.objects.filter(employee=user).order_by("-created_at")
    return render(request, "leave/my_leaves.html", {"leaves": leaves})
