"""
Classes describing the workflow of setting up a peering session
"""

import fullctl.service_bridge.pdbctl as pdbctl
import reversion
from django.conf import settings

from django_peerctl.email import send_mail
from django_peerctl.models import (
    AuditLog,
    EmailLog,
    MutualLocation,
    Network,
    PeerPort,
    PeerRequest,
    PeerSession,
    PortInfo,
)


class PeerSessionWorkflow:
    """
    Base peer_session workflow class

    All workflows should extend this
    """

    def __init__(self, port, member):
        self.port = port
        self.member = member
        self.peer_asn = self.member.asn
        self.my_asn = self.port.port_info_object.ref.asn
        self.net = Network.objects.get(asn=self.my_asn)

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
        peer_port = PeerPort.get_or_create_from_members(
            port.port_info_object.ref, member
        )
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

    def peer_sessions(self):
        """
        Returns a list of all peer_session objects for this port
        """
        return PeerSession.objects.filter(
            peer_port__peer_net__net__asn=self.my_asn,
            peer_port__peer_net__peer__asn=self.peer_asn,
        )

    @property
    def next_step(self):
        sessions_requested = self.peer_sessions().filter(status="requested").exists()
        sessions_configured = self.peer_sessions().filter(status="configured").exists()

        if not sessions_requested and not sessions_configured:
            return "peer-request"
        elif sessions_requested:
            return "peer-config-complete"
        elif sessions_configured:
            return "peer-session-live"
        return None

    @property
    def requested_sessions(self):
        """
        Returns a list of all peer_session objects in status 'requested'
        """
        return self.peer_sessions().filter(status="requested")

    @property
    def configured_sessions(self):
        """
        Returns a list of all peer_session objects in status 'configured'
        """
        return self.peer_sessions().filter(status="configured")

    def progress(self, *args, **kwargs):
        sessions_requested = self.peer_sessions().filter(status="requested").exists()
        sessions_configured = self.peer_sessions().filter(status="configured").exists()

        if not sessions_requested and not sessions_configured:
            return self.request(*args, **kwargs)
        elif sessions_requested:
            return self.config_complete(*args, **kwargs)
        elif sessions_configured:
            return self.finalize(*args, **kwargs)
        return []

    @reversion.create_revision()
    def request(self, peer_request, *args, **kwargs):
        """create/update peer_session object with status 'requested'"""
        return self._ensure_sessions(peer_request, "requested")

    @reversion.create_revision()
    def config_complete(self, peer_request, *args, **kwargs):
        """create/update peer_session object with status 'configured'"""
        return self._ensure_sessions(peer_request, "configured")

    @reversion.create_revision()
    def finalize(self, peer_request, *args, **kwargs):
        """create/update peer_session object with status 'ok'"""
        return self._ensure_sessions(peer_request, "ok")

    def get_peer_request(self, type, status):
        peer_request = (
            PeerRequest.objects.filter(
                net=self.net,
                peer_asn=self.peer_asn,
                type=type,
                status=status,
            )
            .prefetch_related("locations")
            .first()
        )

        if peer_request:
            return peer_request

        return PeerRequest.objects.create(
            net=self.net,
            peer_asn=self.peer_asn,
            type=type,
            status=status,
        )

    def _ensure_sessions(self, peer_request, session_status):
        # automatically create peering sessions at
        # mutual locations
        mutual = self.net.get_mutual_locations(self.peer_asn)
        all_requested = []

        exchanges = []

        for location in peer_request.locations.all():
            if location.ixctl_ix_id:
                exchanges.append(f"ixctl:{location.ixctl_ix_id}")
            elif location.pdb_ix_id:
                exchanges.append(f"pdbctl:{location.pdb_ix_id}")

        for ix_id, members in list(mutual.items()):
            if exchanges and ix_id not in exchanges:
                continue

            if not members.get(self.my_asn):
                continue

            if not members.get(self.peer_asn):
                continue

            print("ensuring session at ix", ix_id)

            for member in members[self.my_asn]:
                for peer in members[self.peer_asn]:
                    try:
                        port = PortInfo.objects.get(ref_id=member.ref_id).port.object
                    except (PortInfo.DoesNotExist, AttributeError):
                        continue

                    if not port.ip_address_4 and not port.ip_address_6:
                        continue

                    session = self.peer_session(member=peer, port=port)
                    print(
                        "ensured session at mututal location",
                        ix_id,
                        "for",
                        member.ipaddr4,
                        peer.ipaddr4,
                        session.status,
                        session_status,
                    )
                    if session.status == "ok":
                        continue
                    session.status = session_status
                    session.save()
                    all_requested.append(session)

        return all_requested


class PeerSessionEmailWorkflow(PeerSessionWorkflow):

    """
    Peer Session setup workflow with email
    notifications to the other party
    """

    cc = False
    test_mode = False

    def contact_email(self, member):
        """
        Returns the contact email address for peering requests associated
        with the specified member (through net.poc_set_active)

        Will return None if no suitable contact can be found.
        """

        if self.test_mode:
            return self.reply_to_email

        if getattr(self, "peer_contact_override", None):
            return self.peer_contact_override

        poc = pdbctl.NetworkContact().first(
            asn=member.asn, require_email=True, role="Policy"
        )

        if not poc:
            return None
        return poc.email

    @property
    def reply_to_email(self):
        return self.port.port_info_object.net.peer_contact_email

    @property
    def sender_email(self):
        override = self.port.port_info_object.net.from_email_override
        if override:
            return override
        return settings.PEER_REQUEST_FROM_EMAIL

    @property
    def cc_address(self):
        if not self.cc:
            return None
        return [self.reply_to_email]

    def render_email_body(self, email_template, required_type):
        if email_template.type != required_type:
            raise ValueError(
                f"Email template wrong type, '{required_type}' type required"
            )

        email_template.context["peer"] = self.member

        return email_template.render()

    def request(self, user, email_template, *args, **kwargs):
        my_asn = self.my_asn
        peer_asn = self.peer_asn

        subject = "Peering request to {} (AS{}) from {} (AS{})".format(
            self.member.name,
            self.member.asn,
            self.net.name,
            self.net.asn,
        )
        body = self.render_email_body(email_template, "peer-request")

        contact = self.contact_email(self.member)

        send_mail(
            subject,
            body,
            self.sender_email,
            [contact],
            reply_to=self.reply_to_email,
            debug_address=user.email,
            cc=self.cc_address,
        )

        EmailLog.log_peer_session_workflow(
            my_asn, peer_asn, user, contact, subject, body
        )

        if self.test_mode:
            return

        peer_request = self.get_peer_request("email", "pending")
        peer_session_list = super().request(peer_request)

        for peer_session in peer_session_list:
            print("Port", peer_session.port)
            peer_request.add_location(
                peer_session.port.object.port_info_object,
                port_id=int(peer_session.port) if peer_session.port else None,
                member_ref_id=peer_session.peer_port.port_info.ref_id,
            )
            AuditLog.log_peer_session_request(peer_session, user)

        return peer_session_list

    def config_complete(self, user, email_template, *args, **kwargs):
        my_asn = self.port.port_info_object.ref.asn
        peer_asn = self.member.asn

        email_template.context["sessions"] = self.peer_sessions()

        subject = "Peering between {} (AS{}) and {} (AS{}) has been configured".format(
            self.member.name,
            self.member.asn,
            self.port.port_info_object.ref.name,
            self.port.port_info_object.ref.asn,
        )
        body = self.render_email_body(email_template, "peer-config-complete")

        contact = self.contact_email(self.member)

        send_mail(
            subject,
            body,
            self.sender_email,
            [contact],
            reply_to=self.reply_to_email,
            debug_address=user.email,
            cc=self.cc_address,
        )

        EmailLog.log_peer_session_workflow(
            my_asn, peer_asn, user, contact, subject, body
        )

        if self.test_mode:
            return

        peer_request = self.get_peer_request("email", "pending")

        peer_session_list = super().config_complete(peer_request)
        for peer_session in peer_session_list:
            AuditLog.log_peer_session_mod(peer_session, user)
        return peer_session_list

    def finalize(self, user, email_template, *args, **kwargs):
        my_asn = self.port.port_info_object.ref.asn
        peer_asn = self.member.asn

        email_template.context["sessions"] = self.peer_sessions()

        subject = "Peering between {} (AS{}) and {} (AS{}) has been enabled".format(
            self.member.name,
            self.member.asn,
            self.port.port_info_object.ref.name,
            self.port.port_info_object.ref.asn,
        )
        body = self.render_email_body(email_template, "peer-session-live")
        contact = self.contact_email(self.member)
        send_mail(
            subject,
            body,
            self.sender_email,
            [contact],
            reply_to=self.reply_to_email,
            debug_address=user.email,
            cc=self.cc_address,
        )

        EmailLog.log_peer_session_workflow(
            my_asn, peer_asn, user, contact, subject, body
        )

        if self.test_mode:
            return

        peer_request = self.get_peer_request("email", "pending")
        peer_session_list = super().finalize(peer_request)
        for peer_session in peer_session_list:
            AuditLog.log_peer_session_mod(peer_session, user)

        peer_request.status = "completed"
        peer_request.locations.all().update(status="completed")
        peer_request.save()

        return peer_session_list


class PeerRequestToAsnWorkflow(PeerSessionEmailWorkflow):

    """
    Peer Session setup workflow with email
    notifications to the other party
    """

    cc = False
    test_mode = False

    def __init__(self, my_asn, their_asn, exchanges):
        self.net = Network.objects.get(asn=my_asn)
        self.other_net = pdbctl.Network().first(asn=their_asn)
        self.exchanges = exchanges or []
        self.member = pdbctl.NetworkIXLan().first(asn=their_asn)
        self.peer_asn = int(their_asn)
        self.my_asn = int(my_asn)

    def contact_email(self, asn):
        """
        Returns the contact email address for peering requests associated
        with the specified member (through net.poc_set_active)

        Will return None if no suitable contact can be found.
        """

        if self.test_mode:
            return self.reply_to_email

        if getattr(self, "peer_contact_override", None):
            return self.peer_contact_override

        poc = pdbctl.NetworkContact().first(asn=asn, require_email=True, role="Policy")

        if not poc:
            return None
        return poc.email

    @property
    def reply_to_email(self):
        return self.net.peer_contact_email

    @property
    def sender_email(self):
        override = self.net.from_email_override
        if override:
            return override
        return settings.PEER_REQUEST_FROM_EMAIL

    def render_email_body(self, email_template, required_type):
        if email_template.type != required_type:
            raise ValueError(
                f"Email template wrong type, '{required_type}' type required"
            )

        if self.member:
            email_template.context["peer"] = self.member.__dict__
        elif self.other_net:
            email_template.context["peer"] = {
                "asn": self.other_net.asn,
                "company_name": self.other_net.name,
            }
        else:
            email_template.context["peer"] = {
                "asn": self.peer_asn,
                "company_name": f"AS{self.peer_asn}",
            }

        if self.exchanges:
            email_template.context["selected_exchanges"] = list(
                MutualLocation(ix, self.net, self.other_net) for ix in self.exchanges
            )

        return email_template.render()

    @reversion.create_revision()
    def request(self, user, email_template, *args, **kwargs):
        my_asn = self.net.asn
        peer_asn = self.other_net.asn

        subject = "Peering request to {} (AS{}) from {} (AS{})".format(
            self.other_net.name,
            peer_asn,
            self.net.name,
            my_asn,
        )
        body = self.render_email_body(email_template, "peer-request")

        contact = self.contact_email(peer_asn)

        send_mail(
            subject,
            body,
            self.sender_email,
            [contact],
            reply_to=self.reply_to_email,
            debug_address=user.email,
            cc=self.cc_address,
        )

        EmailLog.log_peer_session_workflow(
            my_asn, peer_asn, user, contact, subject, body
        )

        if self.test_mode:
            return

        peer_request = self.get_peer_request("email", "pending")

        for ix in self.exchanges:
            if ix.source == "pdbctl":
                peer_request.add_pdb_location(ix.id)
            elif ix.source == "ixctl":
                peer_request.add_ixctl_location(ix.id, ix.pdb_id)

        peer_session_list = PeerSessionWorkflow.request(self, peer_request)

        for peer_session in peer_session_list:
            AuditLog.log_peer_session_request(peer_session, user)

        return peer_session_list

    @property
    def next_step(self):
        return "peer-request"
