from django.shortcuts import redirect


class OneSessionPerUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            session_token = request.session.get("login_token")
            if not session_token or str(request.user.login_token) != session_token:
                from django.contrib.auth import logout
                logout(request)
                return redirect("users:multi_login_detected")  # new URL pattern
        return self.get_response(request)
