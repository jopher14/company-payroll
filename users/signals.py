from django.contrib.auth.signals import user_logged_in
from typing import Type
from django.dispatch import receiver
from django.http import HttpRequest
from django.contrib.sessions.models import Session
from users.models import User


@receiver(user_logged_in)
def kick_previous_session(sender: Type[User], request: HttpRequest, user: User, **kwargs):
    current_session_key = request.session.session_key
    if not current_session_key:
        request.session.save()
        current_session_key = request.session.session_key

    stored_session_key = getattr(user, "last_session_key", None)

    # If old session exists and it's not this one → mark old one for logout
    if stored_session_key and stored_session_key != current_session_key:
        try:
            old_session = Session.objects.get(session_key=stored_session_key)
            data = old_session.get_decoded()
            data["force_logout"] = True
            old_session.session_data = Session.objects.encode(data)
            old_session.save()
        except Session.DoesNotExist:
            pass

    # Update user’s active session key to the new one
    user.last_session_key = current_session_key
    user.save(update_fields=["last_session_key"])
