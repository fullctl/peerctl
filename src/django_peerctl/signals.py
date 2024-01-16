from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import pre_save
from django.dispatch import receiver

from django_peerctl.models import (
    DeviceTemplate,
    EmailTemplate,
    PeerSession,
    UserSession,
)


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


@receiver(pre_save, sender=PeerSession)
def set_session_device(sender, **kwargs):
    """
    Before a PeerSession is saved we want to update the
    device field to match the device field of the port
    """

    session = kwargs.get("instance")

    if not session:
        return

    if not session.port:
        # no port set, nothing to do
        return

    try:
        if session.device == session.port.object.device_id:
            # device already set, nothing to do
            return
    except AttributeError:
        # port reference does not exist, nothing to do
        # TODO: raise?
        return

    session.device = session.port.object.device_id


@receiver(pre_save, sender=EmailTemplate)
def change_default_email_template(sender, **kwargs):
    """
    Before a EmailTemplate is saved we want to update the
    default field to False for all other EmailTemplates of
    the same type
    """

    email_template = kwargs.get("instance")

    if not email_template:
        return

    if email_template.default:
        EmailTemplate.objects.filter(type=email_template.type).exclude(
            pk=email_template.pk
        ).update(default=False)


@receiver(pre_save, sender=DeviceTemplate)
def change_default_device_template(sender, **kwargs):
    """
    Before a DeviceTemplate is saved we want to update the
    default field to False for all other DeviceTemplates of
    the same type
    """

    device_template = kwargs.get("instance")

    if not device_template:
        return

    if device_template.default:
        DeviceTemplate.objects.filter(type=device_template.type).exclude(
            pk=device_template.pk
        ).update(default=False)
