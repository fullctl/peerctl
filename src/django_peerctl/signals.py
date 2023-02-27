from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from django_peerctl.models import UserSession


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
