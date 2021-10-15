from allauth.account.signals import user_signed_up
from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from django_peerctl.email import send_mail_from_default
from django_peerctl.models import UserSession


# TODO: no longer needed?
# @receiver(user_signed_up, dispatch_uid="allauth.user_signed_up")
def allauth_signup(request, user, sociallogin=None, **kwargs):
    """
    When a new user is created through allauth we want to
    be able to deactivate them during alpha and beta phases

    So they will need manual activation
    """
    if getattr(settings, "PEERCTL_DEACTIVATE_NEW_USERS", True):
        user.is_active = False
        user.save()

    # notify of user signup
    if getattr(settings, "PEERCTL_NOTIFY_USER_SIGNUP", False):
        subject = f"New user: {user.username}"
        body = "Username: {}\nEmail: {}\nName: {} {}".format(
            user.username, user.email, user.first_name, user.last_name
        )
        send_mail_from_default(subject, body, [settings.WISH_NOTIFY_EMAIL], prefix=True)


@receiver(user_logged_in)
def set_user_session(sender, request, user, **kwargs):
    """
    When a user logs in, we want to record the session
    id and the user id - this allows us to count
    active client sessions for a user
    """

    UserSession.objects.get_or_create(user=user, session_id=request.session.session_key)


@receiver(user_logged_out)
def unset_user_session(sender, request, user, **kwargs):
    """
    When a user logs out we delete the client session
    to user relationship
    """

    UserSession.objects.filter(
        user=user, session_id=request.session.session_key
    ).delete()
