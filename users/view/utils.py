from typing import cast
from ..models import User
from django.http import HttpRequest


def isHR(user):
    return user.role == "human_resources" or user.is_superuser


def castUser(request: HttpRequest) -> User:
    return cast(User, request.user)
