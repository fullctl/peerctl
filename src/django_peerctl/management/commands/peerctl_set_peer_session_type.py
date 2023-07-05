from fullctl.django.management.commands.base import CommandInterface

from django_peerctl.models.peerctl import PeerSession, Port


class Command(CommandInterface):
    """
    Sets the device field on a PeerSession to match the device field of the port

    devicectl needs to be running.
    """

    def run(self, *args, **kwargs):
        qset = PeerSession.objects

        for session in qset:
            port = Port().first(id=session.port.id)
            if port.is_ixi:
                session.peer_session_type = "ixp"
            else:
                session.peer_session_type = "transit"
