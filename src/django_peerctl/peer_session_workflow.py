"""
Classes describing the workflow of setting up a peering session
"""

import fullctl.service_bridge.pdbctl as pdbctl
import reversion

from django_peerctl.email import send_mail_from_default
from django_peerctl.models import (
    AuditLog,
    EmailLog,
    EmailTemplate,
    Network,
    PeerNetwork,
    PeerPort,
    PeerSession,
    Port,
)


class PeerSessionWorkflow:
    """
    Base peer_session workflow class

    All workflows should extend this
    """

    def __init__(self, port, member):
        self.port = port
        self.member = member

    @reversion.create_revision()
    def peer_session(self, create=True, member=None, port=None):
        """
        Returns a peer_session object from port to member.

        Will create it if it does not exist yet
        """
        if not member:
            member = self.member
        if not port:
            port = self.port
        peer_port = PeerPort.get_or_create_from_members(port.port_info.ref, member)
        if create:
            peer_session = PeerSession.get_or_create(
                port, peer_port, create_status="pending"
            )
        else:
            try:
                peer_session = PeerSession.objects.get(port=port, peer_port=peer_port)
            except PeerSession.DoesNotExist:
                return None
        return peer_session

    @property
    def next_step(self):
        peer_session = self.peer_session(create=False)
        if not peer_session or peer_session.status == "deleted":
            return "peer-request"
        elif peer_session.status == "requested":
            return "peer-config-complete"
        elif peer_session.status == "configured":
            return "peer-session-live"
        return None

    @property
    def my_asn(self):
        return self.port.port_info.ref.asn

    @property
    def peer_asn(self):
        return self.member.asn

    def progress(self, *args, **kwargs):
        peer_session = self.peer_session(create=False)

        self.port.port_info.net.validate_limits()

        if not peer_session or peer_session.status == "deleted":
            return self.request(*args, **kwargs)
        elif peer_session.status == "requested":
            return self.config_complete(*args, **kwargs)
        elif peer_session.status == "configured":
            return self.finalize(*args, **kwargs)
        return [peer_session]

    @reversion.create_revision()
    def request(self, request_mutual=True, *args, **kwargs):
        """create/update peer_session object with status 'requested'"""
        peer_session = self.peer_session()
        peer_session.status = "requested"
        peer_session.save()

        if not request_mutual:
            return [peer_session]

        # automatically create peering sessions at
        # mutual locations
        mutual = self.port.port_info.net.get_mutual_locations(self.peer_asn)
        all_requested = [peer_session]
        for ixlan_id, members in list(mutual.items()):
            for member in members[self.my_asn]:
                for peer in members[self.peer_asn]:
                    if peer.id == self.member.id:
                        continue
                    other_peer_session = self.peer_session(
                        member=peer, port=Port.get_or_create(member)
                    )
                    if other_peer_session.status != "pending":
                        continue
                    other_peer_session.status = "requested"
                    other_peer_session.save()
                    all_requested.append(other_peer_session)

        return all_requested

    @reversion.create_revision()
    def config_complete(self, *args, **kwargs):
        """create/update peer_session object with status 'configured'"""
        peer_session = self.peer_session()
        peer_session.status = "configured"
        peer_session.save()
        return [peer_session]

    @reversion.create_revision()
    def finalize(self, *args, **kwargs):
        """create/update peer_session object with status 'ok'"""
        peer_session = self.peer_session()
        peer_session.status = "ok"
        peer_session.save()
        return [peer_session]


class PeerSessionEmailWorkflow(PeerSessionWorkflow):

    """
    Peer Session setup workflow with email
    notifications to the other party
    """

    @classmethod
    def contact_email(cls, member):
        """
        Returns the contact email address for peering requests associated
        with the specified member (through net.poc_set_active)

        Will return None if no suitable contact can be found.
        """

        poc = pdbctl.NetworkContact().first(
            asn=member.asn, require_email=True, role="Policy"
        )

        if not poc:
            return None
        return poc.email

    @property
    def reply_to_email(self):
        return self.port.port_info.net.peer_contact_email

    def render_email_body(self, email_template, required_type):
        if email_template.type != required_type:
            raise ValueError(
                f"Email template wrong type, '{required_type}' type required"
            )

        email_template.context["peer"] = self.member

        return email_template.render()

    def request(self, user, email_template, *args, **kwargs):
        my_asn = self.port.port_info.ref.asn
        peer_asn = self.member.asn

        subject = "Peering request to {} (AS{}) from {} (AS{})".format(
            self.member.name,
            self.member.asn,
            self.port.port_info.ref.name,
            self.port.port_info.ref.asn,
        )
        body = self.render_email_body(email_template, "peer-request")

        contact = self.contact_email(self.member)

        send_mail_from_default(
            subject,
            body,
            [contact],
            reply_to=self.reply_to_email,
            debug_address=user.email,
        )

        EmailLog.log_peer_session_workflow(
            my_asn, peer_asn, user, contact, subject, body
        )

        peer_session_list = super().request()

        for peer_session in peer_session_list:
            AuditLog.log_peer_session_request(peer_session, user)

        return peer_session_list

    def config_complete(self, user, email_template, *args, **kwargs):
        my_asn = self.port.port_info.ref.asn
        peer_asn = self.member.asn

        email_template.context["sessions"] = [self.peer_session()]

        subject = "Peering between {} (AS{}) and {} (AS{}) has been configured".format(
            self.member.name,
            self.member.asn,
            self.port.port_info.ref.name,
            self.port.port_info.ref.asn,
        )
        body = self.render_email_body(email_template, "peer-config-complete")

        contact = self.contact_email(self.member)

        send_mail_from_default(
            subject,
            body,
            [contact],
            reply_to=self.reply_to_email,
            debug_address=user.email,
        )

        EmailLog.log_peer_session_workflow(
            my_asn, peer_asn, user, contact, subject, body
        )

        peer_session_list = super().config_complete()
        for peer_session in peer_session_list:
            AuditLog.log_peer_session_mod(peer_session, user)
        return peer_session_list

    def finalize(self, user, email_template, *args, **kwargs):
        my_asn = self.port.port_info.ref.asn
        peer_asn = self.member.asn

        email_template.context["sessions"] = [self.peer_session()]

        subject = "Peering between {} (AS{}) and {} (AS{}) has been enabled".format(
            self.member.name,
            self.member.asn,
            self.port.port_info.ref.name,
            self.port.port_info.ref.asn,
        )
        body = self.render_email_body(email_template, "peer-session-live")
        contact = self.contact_email(self.member)
        send_mail_from_default(
            subject,
            body,
            [contact],
            reply_to=self.reply_to_email,
            debug_address=user.email,
        )

        EmailLog.log_peer_session_workflow(
            my_asn, peer_asn, user, contact, subject, body
        )

        peer_session_list = super().finalize()
        for peer_session in peer_session_list:
            AuditLog.log_peer_session_mod(peer_session, user)
        return peer_session_list