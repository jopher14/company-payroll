from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest


class OneSessionPerUserMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest):
        if not request.user.is_authenticated:
            return

        # Flag old session dynamically
        setattr(request, "force_logout", request.session.get("force_logout", False))
