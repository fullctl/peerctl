import re

from fullctl.django.management.commands.base import CommandInterface

from django_peerctl.models.peerctl import PeerSession, Port


class Command(CommandInterface):
    """
    Sets the peer_session_type of a PeerSession based on the ports properties
    """

    def run(self, *args, **kwargs):
        qset = PeerSession.objects.all()

        for session in qset:
            port = Port().first(id=session.port.id)
            if not port or port.id == 0:
                continue

            pni_regex = re.compile(r"\bPNI\b", re.IGNORECASE)
            new_peer_session_type = ""
            if port.is_ixi:
                new_peer_session_type = "ixp"
            # if "PNI" or "pni" in port.virtual_port_description:
            elif port.virtual_port_description and pni_regex.search(
                port.virtual_port_description
            ):
                new_peer_session_type = "pni"
            else:
                new_peer_session_type = "transit"

            if new_peer_session_type != session.peer_session_type:
                self.log_info(
                    f"Changing peer_session_type of {session} from {session.peer_session_type} to {new_peer_session_type}"
                )
                session.peer_session_type = new_peer_session_type
                session.save()

            session.peer_session_type
            session.save()
