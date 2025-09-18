from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
import uuid


@receiver(user_logged_in)
def update_login_token(sender, request, user, **kwargs):
    user.login_token = uuid.uuid4()  # generate new token
    user.save(update_fields=["login_token"])
    request.session["login_token"] = str(user.login_token)


user_logged_in.connect(update_login_token)
