from django.http import JsonResponse
from django.http import HttpRequest, HttpResponse


def chrome_devtools_config(request: HttpRequest) -> HttpResponse:
    # Return empty JSON to stop 404 log spam
    return JsonResponse({}, status=200)
