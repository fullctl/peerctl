from fullctl.django.management.commands.base import CommandInterface

from django_peerctl.models.peerctl import PeerSession


class Command(CommandInterface):
    """
    Sets the device field on a PeerSession to match the device field of the port

    devicectl needs to be running.
    """

    def run(self, *args, **kwargs):
        qset = PeerSession.objects.filter(device__isnull=True).exclude(
            port__isnull=True
        )

        if not qset:
            self.log_info("No PeerSessions without device")

        for session in qset:
            session.save()
            assert session.device
            self.log_info(f"Set device on {session}: {session.device}")
