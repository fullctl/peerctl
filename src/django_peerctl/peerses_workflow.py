"""
Classes describing the workflow of setting up a peering session
"""

import reversion
import fullctl.service_bridge.pdbctl as pdbctl_bridge

from django_peerctl.email import send_mail_from_default

from django_peerctl.models import (
    Port,
    PeerPort,
    PeerSession,
    PeerNetwork,
    Network,
    EmailTemplate,
    AuditLog,
    EmailLog,
)


class PeerSessionWorkflow:
    """
    Base peerses workflow class

    All workflows should extend this
    """

    def __init__(self, port, netixlan):
        self.port = port
        self.netixlan = netixlan

    @reversion.create_revision()
    def peerses(self, create=True, netixlan=None, port=None):
        """
        Returns a peerses object from port to netixlan.

        Will create it if it does not exist yet
        """
        if not netixlan:
            netixlan = self.netixlan
        if not port:
            port = self.port
        peerport = PeerPort.get_or_create_from_netixlans(port.portinfo.pdb, netixlan)
        if create:
            peerses = PeerSession.get_or_create(port, peerport, create_status="pending")
        else:
            try:
                peerses = PeerSession.objects.get(port=port, peerport=peerport)
            except PeerSession.DoesNotExist:
                return None
        return peerses

    @property
    def next_step(self):
        peerses = self.peerses(create=False)
        if not peerses or peerses.status == "deleted":
            return "peer-request"
        elif peerses.status == "requested":
            return "peer-config-complete"
        elif peerses.status == "configured":
            return "peer-session-live"
        return None

    @property
    def my_asn(self):
        return self.port.portinfo.pdb.net.asn

    @property
    def peer_asn(self):
        return self.netixlan.net.asn

    def progress(self, *args, **kwargs):
        peerses = self.peerses(create=False)

        self.port.portinfo.net.validate_limits()

        if not peerses or peerses.status == "deleted":
            return self.request(*args, **kwargs)
        elif peerses.status == "requested":
            return self.config_complete(*args, **kwargs)
        elif peerses.status == "configured":
            return self.finalize(*args, **kwargs)
        return [peerses]

    @reversion.create_revision()
    def request(self, request_mutual=True, *args, **kwargs):
        """create/update peerses object with status 'requested'"""
        peerses = self.peerses()
        peerses.status = "requested"
        peerses.save()

        if not request_mutual:
            return [peerses]

        # automatically create peering sessions at
        # mutual locations
        mutual = self.port.portinfo.net.get_mutual_locations(self.peer_asn)
        all_requested = [peerses]
        for ixlan_id, netixlans in list(mutual.items()):
            for netixlan in netixlans[self.my_asn]:
                for peer in netixlans[self.peer_asn]:
                    if peer.id == self.netixlan.id:
                        continue
                    other_peerses = self.peerses(
                        netixlan=peer, port=Port.get_or_create(netixlan)
                    )
                    if other_peerses.status != "pending":
                        continue
                    other_peerses.status = "requested"
                    other_peerses.save()
                    all_requested.append(other_peerses)

        return all_requested

    @reversion.create_revision()
    def config_complete(self, *args, **kwargs):
        """create/update peerses object with status 'configured'"""
        peerses = self.peerses()
        peerses.status = "configured"
        peerses.save()
        return [peerses]

    @reversion.create_revision()
    def finalize(self, *args, **kwargs):
        """create/update peerses object with status 'ok'"""
        peerses = self.peerses()
        peerses.status = "ok"
        peerses.save()
        return [peerses]


class PeerSessionEmailWorkflow(PeerSessionWorkflow):

    """
    Peer Session setup workflow with email
    notifications to the other party
    """

    @classmethod
    def contact_email(cls, netixlan):
        """
        Returns the contact email address for peering requests associated
        with the specified netixlan (through net.poc_set_active)

        Will return None if no suitable contact can be found.
        """

        poc = pdbctl_bridge.NetworkContact().first(
            asn=netixlan.asn, require_email=True, role="Policy"
        )

        if not poc:
            return None
        return poc.email

    @property
    def reply_to_email(self):
        return self.port.portinfo.net.peer_contact_email

    def render_email_body(self, emltmpl, required_type):
        if emltmpl.type != required_type:
            raise ValueError(
                f"Email template wrong type, '{required_type}' type required"
            )

        emltmpl.context["peer"] = self.netixlan

        return emltmpl.render()

    def request(self, user, emltmpl, *args, **kwargs):
        my_asn = self.port.portinfo.pdb.net.asn
        peer_asn = self.netixlan.net.asn

        subject = "Peering request to {} (AS{}) from {} (AS{})".format(
            self.netixlan.net.name,
            self.netixlan.net.asn,
            self.port.portinfo.pdb.net.name,
            self.port.portinfo.pdb.net.asn,
        )
        body = self.render_email_body(emltmpl, "peer-request")

        contact = self.contact_email(self.netixlan)

        send_mail_from_default(
            subject,
            body,
            [contact],
            reply_to=self.reply_to_email,
            debug_address=user.email,
        )

        EmailLog.log_peerses_workflow(my_asn, peer_asn, user, contact, subject, body)

        peerses_list = super().request()

        for peerses in peerses_list:
            AuditLog.log_peerses_request(peerses, user)

        return peerses_list

    def config_complete(self, user, emltmpl, *args, **kwargs):
        my_asn = self.port.portinfo.pdb.net.asn
        peer_asn = self.netixlan.net.asn

        emltmpl.context["sessions"] = [self.peerses()]

        subject = "Peering between {} (AS{}) and {} (AS{}) has been configured".format(
            self.netixlan.net.name,
            self.netixlan.net.asn,
            self.port.portinfo.pdb.net.name,
            self.port.portinfo.pdb.net.asn,
        )
        body = self.render_email_body(emltmpl, "peer-config-complete")

        contact = self.contact_email(self.netixlan)

        send_mail_from_default(
            subject,
            body,
            [contact],
            reply_to=self.reply_to_email,
            debug_address=user.email,
        )

        EmailLog.log_peerses_workflow(my_asn, peer_asn, user, contact, subject, body)

        peerses_list = super().config_complete()
        for peerses in peerses_list:
            AuditLog.log_peerses_mod(peerses, user)
        return peerses_list

    def finalize(self, user, emltmpl, *args, **kwargs):
        my_asn = self.port.portinfo.pdb.net.asn
        peer_asn = self.netixlan.net.asn

        emltmpl.context["sessions"] = [self.peerses()]

        subject = "Peering between {} (AS{}) and {} (AS{}) has been enabled".format(
            self.netixlan.net.name,
            self.netixlan.net.asn,
            self.port.portinfo.pdb.net.name,
            self.port.portinfo.pdb.net.asn,
        )
        body = self.render_email_body(emltmpl, "peer-session-live")
        contact = self.contact_email(self.netixlan)
        send_mail_from_default(
            subject,
            body,
            [contact],
            reply_to=self.reply_to_email,
            debug_address=user.email,
        )

        EmailLog.log_peerses_workflow(my_asn, peer_asn, user, contact, subject, body)

        peerses_list = super().finalize()
        for peerses in peerses_list:
            AuditLog.log_peerses_mod(peerses, user)
        return peerses_list
