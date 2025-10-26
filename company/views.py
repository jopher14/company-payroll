from django.http import JsonResponse
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def chrome_devtools_config(request: HttpRequest) -> HttpResponse:
    # Return empty JSON to stop 404 log spam
    return JsonResponse({}, status=200)


@ensure_csrf_cookie
def set_csrf_token(request: HttpRequest) -> HttpResponse:
    return JsonResponse({"message": "CSRF cookie set"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_view(request):
    return Response({"message": f"Welcome, {request.user.username}!"})
