import collections
import datetime
import ipaddress
import json
import logging
import os.path

import fullctl.service_bridge.devicectl as devicectl
import fullctl.service_bridge.ixctl as ixctl
import fullctl.service_bridge.pdbctl as pdbctl
import fullctl.service_bridge.sot as sot
import reversion
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from django_countries.fields import CountryField
from django_grainy.decorators import grainy_model
from django_inet.models import ASNField
from fullctl.django.fields.service_bridge import ReferencedObjectField
from fullctl.django.models.abstract import HandleRefModel, meta
from fullctl.django.models.concrete import Instance, Organization  # noqa
from fullctl.django.validators import ip_address_string
from fullctl.service_bridge.data import Relationships
from jinja2 import DictLoader, Environment, FileSystemLoader
from netfields import InetAddressField, MACAddressField, NetManager

from django_peerctl import const
from django_peerctl.email import send_mail_from_default
from django_peerctl.exceptions import TemplateRenderError, UsageLimitError
from django_peerctl.helpers import get_best_policy, get_peer_contact_email
from django_peerctl.meta import PeerSessionSchema
from django_peerctl.models.tasks import SyncIsRsPeer, SyncMacAddress, SyncRouteServerMD5
from django_peerctl.templating import make_variable_name

# naming::
# handleref tag $model_$model
# matching fks should use the tag (even tho it would usually be done as _)

STATUS_CHOICES = (
    ("open", "open"),
    ("closed", "closed"),
)

DEVICE_TYPE_CHOICES = const.DEVICE_TYPES

EMAIL_TEMPLATE_TYPES = (
    ("peer-request", "Peering Request"),
    ("peer-config-complete", "Peering Configuration Complete"),
    ("peer-session-live", "Peering Session Live"),
)


class DescriptionField(models.CharField):
    """
    description field for use with devices
    will need template replacement and valid char checking
    """

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 255
        kwargs["blank"] = True
        kwargs["null"] = True
        super().__init__(*args, **kwargs)


class URLField(models.URLField):
    """
    local defaults for URLField
    """

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 255
        super().__init__(*args, **kwargs)


class UTC(datetime.tzinfo):
    """
    UTC+0 tz for tz aware datetime fields
    """

    def utcoffset(self, d):
        return datetime.timedelta(seconds=0)


class ref_fallback:

    """
    use to decorate the value getter method targeted
    by a SerializerMethodField with a default value
    if the pdb object is not found
    """

    def __init__(self, value):
        self.value = value

    def __call__(self, fn):
        value = self.value

        def wrapped(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except (
                AttributeError,
                sot.ReferenceNotFoundError,
                sot.ReferenceNotSetError,
                ObjectDoesNotExist,
            ):
                if isinstance(value, collections.abc.Callable):
                    return value(*args)
                return value

        wrapped.__name__ = fn.__name__

        return wrapped


class Base(HandleRefModel):
    notes_public = models.TextField(null=True, blank=True, help_text="public notes")
    notes_private = models.TextField(null=True, blank=True, help_text="private notes")

    class Meta:
        abstract = True


@reversion.register
class Policy(Base):
    net = models.ForeignKey("Network", on_delete=models.CASCADE, related_name="+")
    name = models.CharField(max_length=255, unique=False)
    import_policy = models.CharField(max_length=1024, unique=False)
    export_policy = models.CharField(max_length=1024, unique=False)
    # TODO - add MED, localpref to django_inet
    localpref = models.IntegerField(null=True, blank=True)
    med = models.IntegerField(null=True, blank=True)
    peer_group = models.CharField(max_length=255, null=True, blank=True)

    class HandleRef:
        tag = "policy"

    class Meta:
        db_table = "peerctl_policy"
        verbose_name_plural = "Policies"

    @property
    def is_global4(self):
        return self.net.policy4_id == self.id

    @property
    def is_global6(self):
        return self.net.policy6_id == self.id

    @property
    def count_peers(self):
        count = 0
        for peer_session in self.net.peer_session_at_ix(ix_id=None):
            if get_best_policy(peer_session, 4) == self:
                count += 1
            elif get_best_policy(peer_session, 6) == self:
                count += 1
        return count

    def __str__(self):
        return f"Policy({self.id}): {self.name}"


class PolicyHolderMixin(models.Model):
    policy4 = models.ForeignKey(
        Policy, null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    policy6 = models.ForeignKey(
        Policy, null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )

    class Meta:
        abstract = True

    @property
    def policy_parents(self):
        """
        Returns the models that are next in the policy inheritance
        chain in a list.
        """
        return []

    @property
    def policy4_inherited(self):
        """
        Returns whether or not the ipv4 policy for this model
        comes from inhertance
        """
        if not self.policy4_id:
            return True
        return False

    @property
    def policy6_inherited(self):
        """
        Returns whether or not the ipv6 policy for this model
        comes from inheritance
        """
        if not self.policy6_id:
            return True
        return False

    def set_policy(self, policy, ip_version, save=True):
        """
        Set a policy on this instance

        Arguments:
            - policy <Policy>
            - ip_version <int>: 4 or 6

        Keyword Arguments:
            - save <bool=True>: automatically save
        """
        if int(ip_version) not in [4, 6]:
            raise ValueError("Invalid ip version")

        if policy and not isinstance(policy, Policy):
            raise TypeError("policy needs to be a Policy object")

        field_name = f"policy{ip_version}"

        setattr(self, field_name, policy)

        if save:
            self.save()


class UsageLimitMixin(models.Model):
    max_sessions = models.PositiveIntegerField(
        help_text=_("maximum amount of peering sessions allowed "), default=0
    )

    class Meta:
        abstract = True


@grainy_model(
    namespace="verified.asn", namespace_instance="{namespace}.{instance.asn}.?"
)
@reversion.register
class Network(PolicyHolderMixin, UsageLimitMixin, Base):
    org = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="net_set",
    )

    # non editable
    asn = ASNField(unique=True, db_index=True)

    as_set_override = models.CharField(null=True, blank=True, max_length=255)
    prefix4_override = models.PositiveIntegerField(null=True, blank=True)
    prefix6_override = models.PositiveIntegerField(null=True, blank=True)

    network_type_override = models.CharField(
        choices=const.NET_TYPES,
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Network type"),
    )

    ratio_override = models.CharField(
        choices=const.RATIOS, max_length=255, null=True, blank=True
    )
    scope_override = models.CharField(
        choices=const.SCOPES, max_length=255, null=True, blank=True
    )
    traffic_override = models.CharField(
        choices=const.TRAFFIC, max_length=255, null=True, blank=True
    )
    unicast_override = models.BooleanField(null=True, blank=True)
    multicast_override = models.BooleanField(null=True, blank=True)
    never_via_route_servers_override = models.BooleanField(null=True, blank=True)

    email_override = models.EmailField(
        null=True,
        blank=True,
        help_text=_(
            "Will override the reply-to: address for email communications from this network"
        ),
    )

    from_email_override = models.EmailField(
        null=True,
        blank=True,
        help_text=_(
            "Will override the from: address for email communications from this network"
        ),
    )

    class HandleRef:
        tag = "net"

    class Meta:
        db_table = "peerctl_net"

    def __str__(self):
        return f"AS{self.asn}"

    @classmethod
    @reversion.create_revision()
    def get_or_create(cls, asn, org):
        """get or create a network object from an ASN"""
        try:
            if org:
                obj = cls.objects.get(asn=asn, org=org)
            else:
                obj = cls.objects.get(asn=asn)

        except cls.DoesNotExist:
            obj = cls.objects.create(asn=asn, org=org, status="ok")

            # create global policy owned by network
            global_policy = Policy.objects.create(name="Global", status="ok", net=obj)

            # assign global policy as network policy
            obj.policy4 = global_policy
            obj.policy6 = global_policy
            obj.save()

        return obj

    @property
    def ref(self):
        if not hasattr(self, "_ref"):
            self._ref = pdbctl.Network().first(asn=self.asn)
        return self._ref

    @property
    @ref_fallback("")
    def peer_contact_email(self):
        """returns email address suitable for peering requests"""
        return self.email_override or get_peer_contact_email(self.asn)

    @property
    def peer_contact_email_no_override(self):
        """returns email address suitable for peering requests (ignores email_override)"""
        return get_peer_contact_email(self.asn)

    @property
    @ref_fallback(lambda x: f"{x}")
    def name(self):
        return self.ref.name

    @property
    @ref_fallback("")
    def website(self):
        return self.ref.website

    @property
    @ref_fallback("")
    def info_type(self):
        return self.ref.info_type

    @property
    @ref_fallback({})
    def contacts(self):
        contacts = {}
        for poc in pdbctl.NetworkContact().objects(asn=self.asn):
            role = poc.role.lower()
            if poc.email and role not in contacts:
                contacts[role] = poc.email
        return contacts

    @property
    @ref_fallback("")
    def as_set(self):
        if not self.as_set_override:
            return self.ref.irr_as_set or ""
        return self.as_set_override

    @property
    @ref_fallback(0)
    def prefix4(self):
        if not self.prefix4_override:
            return self.ref.info_prefixes4
        return self.prefix4_override

    @property
    @ref_fallback(0)
    def prefix6(self):
        if not self.prefix6_override:
            return self.ref.info_prefixes6
        return self.prefix6_override

    @property
    def network_type(self):
        if not self.network_type_override:
            return self.ref.info_type
        return self.network_type_override

    @property
    def ratio(self):
        if not self.ratio_override:
            return self.ref.info_ratio
        return self.ratio_override

    @property
    def scope(self):
        if not self.scope_override:
            return self.ref.info_scope
        return self.scope_override

    @property
    def traffic(self):
        if not self.traffic_override:
            return self.ref.info_traffic
        return self.traffic_override

    @property
    @ref_fallback(False)
    def unicast(self):
        if not self.unicast_override:
            return self.ref.info_unicast
        return self.unicast_override

    @property
    @ref_fallback(False)
    def multicast(self):
        if not self.multicast_override:
            return self.ref.info_multicast
        return self.multicast_override

    @property
    @ref_fallback(False)
    def never_via_route_servers(self):
        if not self.never_via_route_servers_override:
            return self.ref.info_never_via_route_servers
        return self.never_via_route_servers_override

    @property
    def is_route_server(self):
        return self.network_type and self.network_type.lower() == "route server"

    @property
    def as_set_source(self):
        if self.as_set_override:
            return "peerctl"
        if self.ref.irr_as_set:
            return "pdbctl"
        return None

    @property
    def devices(self):
        try:
            return devicectl.Device().objects(org=self.org.permission_id)
        except AttributeError:
            return []

    @property
    def peer_session_set(self):
        """
        returns all peer sessions owned by this network
        """
        return PeerSession.objects.filter(peer_port__peer_net__net=self)

    @property
    def peer_net_set(self):
        """
        returns all PeerNetworks owned by this network
        """
        return PeerNetwork.objects.filter(net=self).select_related("net", "peer")

    def peer_nets_at_ix(self, ix_id=None):
        """
        returns all PeerNetworks owned by this network at the specified
        exchange
        """
        qset = self.peer_net_set
        if ix_id:
            exchange = InternetExchange.objects.get(id=ix_id)
            ref_source, ref_id = exchange.ref_parts
            members = [
                n.ref_id for n in PortInfo.ref_bridge(ref_source).objects(ix=ref_id)
            ]
            peer_port_qset = PeerPort.objects.filter(port_info__ref_id__in=members)
            ids = [peer_port.peer_net_id for peer_port in peer_port_qset]
            qset = qset.filter(id__in=ids)
        return qset

    def peer_session_at_ix(self, ix_id=None):
        qset = self.peer_session_set

        if ix_id:
            exchange = InternetExchange.objects.get(id=ix_id)
            ref_source, ref_id = exchange.ref_parts
            members = [
                n.ref_id for n in PortInfo.ref_bridge(ref_source).objects(ix=ref_id)
            ]
            qset = qset.filter(peer_port__port_info__ref_id__in=members)

        return qset

    def get_max_sessions(self):
        """
        Returns max sessions allowed for this network

        Will first check if there is a limit set on the organization
        and if so return that limit instead

        If neither the organization nor the network has a limit
        defined the free usage limit will be returned
        """

        # TODO aaactl metered / plans
        return 99999

        # if self.org_id and self.org.max_sessions:
        #     return self.org.max_sessions
        # return self.max_sessions or settings.FREE_LIMITS.get("MAX_PEERSES")

    def validate_limits(self):
        maxses = self.get_max_sessions()
        if self.peer_session_set.count() + 1 > maxses:
            raise UsageLimitError(f"{maxses} sessions")

    def get_peer(self, asn):
        """get or create a peer network object from an ASN"""
        peer = Network.get_or_create(asn)

        try:
            obj = PeerNetwork.objects.get(net_id=self.id, peer_id=peer.id)

        except PeerNetwork.DoesNotExist:
            obj = PeerNetwork.objects.create(
                net=self,
                peer=peer,
                status="ok",
            )

        return obj

    def get_mutual_locations(self, other_asn, exclude=None):
        asns = [self.asn, other_asn]

        exchanges = {}

        for member in sot.InternetExchangeMember().objects(asns=asns):
            source = member.source
            ix_ref_id = f"{source}:{member.ix_id}"

            if exclude and ix_ref_id in exclude:
                continue

            if ix_ref_id not in exchanges:
                exchanges[ix_ref_id] = {self.asn: [], other_asn: []}

            exchanges[ix_ref_id][member.asn].append(member)

        mutual = {}

        for ix_id, members in list(exchanges.items()):
            if members[self.asn] and members[other_asn]:
                mutual[ix_id] = members
        return mutual

    def get_peer_contacts(self, ix_id=None, role="policy"):
        peer_session_qset = (
            self.peer_session_at_ix(ix_id)
            .filter(status="ok")
            .select_related(
                "peer_port", "peer_port__peer_net", "peer_port__peer_net__peer"
            )
        )
        r = list(
            {
                peer_session.peer_port.peer_net.peer.contacts.get(role)
                for peer_session in peer_session_qset
            }
        )
        try:
            r.remove(None)
        except Exception:
            pass
        return r

    def set_as_set(self, as_set):
        self.as_set_override = as_set
        self.save()


@reversion.register
class PeerNetwork(PolicyHolderMixin, Base):
    """preferences and policy for specific peer network"""

    # owner network
    net = models.ForeignKey(Network, on_delete=models.CASCADE, related_name="+")
    peer = models.ForeignKey(Network, on_delete=models.CASCADE, related_name="+")
    md5 = models.CharField(max_length=255, null=True, blank=True)

    # allow override of max prefix numbers
    info_prefixes4 = models.PositiveIntegerField(null=True, blank=True)
    info_prefixes6 = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("net", "peer")
        db_table = "peerctl_peer_net"
        verbose_name = "Network to Peer Relationship"
        verbose_name_plural = "Network to Peer Relationships"

    class HandleRef:
        tag = "peer_net"

    @classmethod
    @reversion.create_revision()
    def get_or_create(cls, net, peer):
        try:
            obj = PeerNetwork.objects.get(net_id=net.id, peer_id=peer.id)

        except cls.DoesNotExist:
            obj = cls.objects.create(
                status="ok",
                net=net,
                peer=peer,
            )

        return obj

    @property
    def peer_sessions(self):
        peer_ports = PeerPort.objects.filter(peer_net=self)
        peer_sessions = PeerSession.objects.filter(peer_port__in=peer_ports)

        return peer_sessions

    @ref_fallback(0)
    def info_prefixes(self, ip_version):
        field_name = f"info_prefixes{ip_version}"
        if getattr(self, field_name, None) is not None:
            return getattr(self, field_name)
        return getattr(self.peer.ref, field_name, 0)

    def set_info_prefixes(self, value, ip_version, save=True):
        if int(ip_version) not in [4, 6]:
            raise ValueError(f"Invalid ip version: {ip_version}")

        setattr(self, f"info_prefixes{ip_version}", int(value))

        if save:
            self.full_clean()
            self.save()

    def policy_parents(self):
        return [self.net]

    def set_route_server_md5(self, md5):
        self.md5 = md5
        self.save()
        self.sync_route_server_md5()

    def sync_route_server_md5(self):
        for session in self.peer_sessions.select_related(
            "peer_port", "peer_port__port_info"
        ):
            if not session.port:
                continue

            port_info = session.port.object.port_info_object

            if not port_info.is_rs_peer:
                continue

            peer_port_info = session.peer_port.port_info
            SyncRouteServerMD5.create_task(
                port_info.net.asn, self.md5, port_info.ipaddr4, peer_port_info.ipaddr4
            )


@reversion.register
class InternetExchange(sot.ReferenceMixin, Base):
    """
    Internet Exchange model, references a PDB ix_lan
    """

    # short_name for config gen
    name = models.CharField(max_length=64)
    name_long = models.CharField(max_length=254, blank=True)
    country = CountryField()

    ref_id = models.CharField(max_length=64, blank=True, null=True, unique=True)

    class HandleRef:
        tag = "ix"

    class Meta:
        db_table = "peerctl_ix"

    @classmethod
    @reversion.create_revision()
    def get_or_create(cls, ix, source):
        if isinstance(ix, int):
            ix = cls.ref_bridge(source).object(ix)

        try:
            obj = cls.objects.get(ref_id=ix.ref_id)

        except cls.DoesNotExist:
            obj = cls.objects.create(
                status="ok",
                # concat ix name and lan name
                name=f"{ix.name}".strip(),
                name_long=getattr(ix, "name_long", ix.name),
                # TODO: ixctl needs to provide country for source of truth
                # exchanges
                country=getattr(ix, "country", "US"),
                ref_id=ix.ref_id,
            )

        return obj

    def __str__(self):
        return f"InternetExchange({self.id}): {self.name}"


class MutualLocation:

    """
    Reperesents a mutual location between two networks
    """

    def __init__(self, ix, net, peer_net):
        """
        Arguments:

            ix (InternetExchange): InternetExchange object
            net (Network): Network object
            peer_net (PeerNetwork): PeerNetwork object
        """

        self.ix = ix
        self.net = net
        self.peer_net = peer_net

    @property
    def name(self):
        """
        Internet exchange name
        """

        return self.ix.name

    @property
    def name_long(self):
        """
        Internet exchange name (long)
        """

        return self.ix.name_long

    @property
    def country(self):
        """
        Internet exchange country code
        """

        return self.ix.country

    @property
    def ip4(self):
        """
        String of IPv4 addresses for this mutual location, delimited by ','
        """

        return ", ".join([str(ip) for ip in self.ip4s])

    @property
    def ip6(self):
        """
        String of IPv6 addresses for this mutual location, delimited by ','
        """

        return ", ".join([str(ip) for ip in self.ip6s])

    @property
    def ip4s(self):
        """
        List of IPv4 addresses for this mutual location
        """

        return [info.ipaddr4 for info in self.port_infos if info.ipaddr4]

    @property
    def ip6s(self):
        """
        List of IPv6 addresses for this mutual location
        """

        return [info.ipaddr6 for info in self.port_infos if info.ipaddr6]

    @property
    def port_infos(self):
        """
        Caches and returns a list of PortInfo objects for this mutual location that
        have an IPv4 or IPv6 address
        """

        if hasattr(self, "_portinfos"):
            return self._portinfos

        self._portinfos = []

        for port_info in self.net.port_info_qs.all():
            if not port_info.ipaddr4 and not port_info.ipaddr6:
                continue

            if port_info.ref_ix_id and port_info.ref_ix_id == self.ix.ref_id:
                self._portinfo = port_info
                self._portinfos.append(port_info)

        return self._portinfos


class PortPolicy(PolicyHolderMixin, Base):
    port = models.PositiveIntegerField(unique=True)

    class Meta:
        db_table = "peerctl_port_policy"

    class HandleRef:
        tag = "port_policy"


class PortObject(devicectl.DeviceCtlEntity, PolicyHolderMixin):
    # TODO PortPolicy schema to allow setting policy per port
    # again

    policy4 = None
    policy6 = None
    policy4_id = None
    policy6_id = None

    class Meta:
        abstract = True

    @property
    def port_policy(self):
        if not hasattr(self, "_port_policy"):
            self._port_policy, _ = PortPolicy.objects.get_or_create(port=self.id)
            self._port_policy._object = self
        return self._port_policy

    @property
    def port_info_object(self):
        if not hasattr(self, "_port_info"):
            self._port_info = PortInfo.objects.filter(port=self.id).first()
            if self._port_info:
                self._port_info.port._object = self
        return self._port_info

    @property
    def policy_parents(self):
        return [self.port_policy, self.port_info_object.net]

    @property
    def devices(self):
        """
        Return device for the port
        """
        if self.device:
            return [self.device]
        if not hasattr(self, "_devices"):
            self._devices = [devicectl.Device().object(self.device_id)]
        return self._devices

    @ref_fallback([])
    def get_available_peers(self):
        """
        Returns queryset for all available peers at
        this port
        """

        ref_source, ref_id = self.port_info_object.ref_parts

        query = self.port_info_object.ref_objects(peers=ref_id)

        peers = [peer for peer in query]

        Relationships.preload("net", peers)

        return peers

    @property
    def mac_address(self):
        # TODO: fallback to read from ixctl?
        return self.port_info_object.mac_address

    @property
    def is_route_server_peer(self):
        return self.port_info_object.is_rs_peer

    @property
    def asn(self):
        try:
            return PortInfo.objects.get(port=self.id).net.asn
        except PortInfo.DoesNotExist:
            return None

    @property
    def peer_session_qs_prefetched(self):
        """
        Returns an instance of the peer_session_qs set that has peer_port
        and port_info preselected for performance.
        """
        # FIXME: should see if there is a way to tell django to automatically
        # do that for a set.
        if not hasattr(self, "_peer_session_qs_prefetched"):
            peer_sessions = PeerSession.objects.filter(port=self.pk)
            self._peer_session_qs_prefetched = peer_sessions.select_related(
                "peer_port", "peer_port__port_info", "peer_port__peer_net"
            ).exclude(status="deleted")
        return self._peer_session_qs_prefetched

    @property
    def is_ixi(self):
        """
        Returns True if the port is an IXI port
        """
        if self.port_info_object and self.port_info_object.ref_id:
            return True
        return False

    def set_policy(self, *args, **kwargs):
        return self.port_policy.set_policy(*args, **kwargs)

    def set_mac_address(self, mac_address):
        self.port_info_object.mac_address = mac_address
        self.port_info_object.save()

        if self.asn:
            SyncMacAddress.create_task(
                self.asn, self.port_info_object.ipaddr4, mac_address
            )

    def set_route_server_md5(self, md5):
        """
        Sets and syncs the route server md5 to ixctl

        Arguments:

            md5 (str): md5 password to set
        """

        # only route server peers can set route server md5s

        if not self.is_route_server_peer:
            return

        # retrieve route server session

        route_server_member = self.get_route_server_member()

        if not route_server_member:
            return

        peer_port = PeerPort.get_or_create_from_members(
            self.port_info_object.ref, route_server_member
        )

        peer_port.peer_net.set_route_server_md5(md5)

    def set_is_route_server_peer(self, is_route_server_peer):
        self.port_info_object.is_route_server_peer = is_route_server_peer
        self.port_info_object.save()

        # TODO: sync to ixctl?

    def get_peer_session(self, member):
        """
        Returns the peering session for this port
        and a member
        """
        try:
            for peer_session in self.peer_session_qs_prefetched:
                try:
                    if (
                        ipaddress.ip_interface(member.ipaddr4).ip
                        == ipaddress.ip_interface(
                            peer_session.peer_port.port_info.ipaddr4
                        ).ip
                    ):
                        return peer_session
                except ValueError:
                    pass

                try:
                    if (
                        ipaddress.ip_interface(member.ipaddr6).ip
                        == ipaddress.ip_interface(
                            peer_session.peer_port.port_info.ipaddr6
                        ).ip
                    ):
                        return peer_session
                except ValueError:
                    pass

        except PeerSession.DoesNotExist:
            return None
        return None

    def get_route_server_member(self):
        """
        Returns the route server member for this port
        """

        ref_source = self.port_info_object.ref_source

        # if source ix ixctl we can get the route server member
        # directly from there

        if ref_source == "ixctl":
            return self.get_route_server_member_ixctl()

        # if source is pdbctl we need to check network member

        if ref_source == "pdbctl":
            return self.get_route_server_member_pdbctl()

    def get_route_server_member_ixctl(self):
        """
        Returns the route server member for this port when the source is ixctl
        """
        port_info = self.port_info_object

        for routeserver in ixctl.Routeserver().objects(
            ix=port_info.ref_ix_id.split(":")[1]
        ):
            return ixctl.InternetExchangeMember().first(ip=routeserver.router_id)

    def get_route_server_member_pdbctl(self):
        """
        Returns the route server member for this port when the source is pdbctl
        """
        port_info = self.port_info_object
        return pdbctl.NetworkIXLan().first(
            ix=port_info.ref_ix_id.split(":")[1], routeserver=1
        )

    def get_route_server_peer_net(self):
        """
        Returns the route server peer for this port
        """

        ref_source = self.port_info_object.ref_source

        # if source ix ixctl we can get the route server peer
        # directly from there

        if ref_source == "ixctl":
            return self.get_route_server_peer_net_ixctl()

        # if source is pdbctl we need to check network type

        if ref_source == "pdbctl":
            return self.get_route_server_peer_net_pdbctl()

    def get_route_server_peer_net_ixctl(self):
        """
        Returns the route server peers for this port when the source is ixctl
        """
        port_info = self.port_info_object

        for routeserver in ixctl.Routeserver().objects(
            ix=port_info.ref_ix_id.split(":")[1]
        ):
            try:
                return PeerNetwork.objects.get(
                    net__asn=self.asn, peer__asn=routeserver.asn
                )
            except PeerNetwork.DoesNotExist:
                pass

    def get_route_server_peer_net_pdbctl(self):
        """
        Returns the route server peers for this port when the source is pdbctl
        """
        port_info = self.port_info_object
        for routeserver in pdbctl.NetworkIXlan().objects(
            ix=port_info.ref_ix_id.split(":")[1], routeserver=1
        ):
            try:
                return PeerNetwork.objects.get(
                    net__asn=self.asn, peer__asn=routeserver.asn
                )
            except PeerNetwork.DoesNotExist:
                pass

    def __str__(self):
        return "Port"


class Port(devicectl.Port):
    DoesNotExist = Exception

    class Meta(devicectl.Port.Meta):
        data_object_cls = PortObject

    @classmethod
    def in_same_subnet(cls, org, device, ip):
        """
        Will return all ports on the device that are in the same subnet as the given ip
        """

        ports = cls().objects(device=device, org_slug=org.slug)

        ip = ip.split("/")[0]

        candidates = []

        for port in ports:
            if not port.ip_address_4:
                continue

            port_ip = ipaddress.ip_interface(port.ip_address_4)
            peer_ip = ipaddress.ip_interface(f"{ip}/{port_ip.network.prefixlen}")

            # check if peer_ip and port_ip4 are in the same subnet
            # with prefix length specified in prefixlen
            if peer_ip.network.network_address == port_ip.network.network_address:
                candidates.append(port)

        return candidates

    @classmethod
    def preload(cls, org, asn, port_ids, filter_device=None):
        """
        Preloads ixctl and pdbctl member reference (port_info ref)

        Arguments:

            org: org object
            asn: asn
            port_ids: list of port ids - only include ports with these ids
            filter_device: device id to filter on, will ignore port_ids if set

        Returns:

            list of PortObject instances
        """

        # load ports

        instances = [
            port
            for port in Port().objects(org=org.remote_id, join="device", status="ok")
            if (filter_device or port.id in port_ids)
            and (not filter_device or port.device_id == int(filter_device))
            and (port.ip_address_4 or port.ip_address_6)
            # and (not port.name or not port.name.startswith("peerctl:"))
        ]

        # prefetch netixlans/ixctl members

        for member in sot.InternetExchangeMember().objects(asn=asn):
            for port in instances:
                # PNI ports may not have a port_info_object yet and can be skipped

                if not hasattr(port, "port_info_object") or not port.port_info_object:
                    continue

                if port.port_info_object.ref_id == member.ref_id:
                    port.port_info_object._ref = member

        return instances

    @classmethod
    def augment_ix(cls, ixi_ports, asn):
        """
        Augments list of intnernet exchange PortObject instances for a network

        Will add prefix4, prefix6, mtu and route server md5

        This takes into consideration whether the exchange has its source
        of truth in ixctl or pdbctl (peeringdb) and will also augment data
        from both datasets if necessary
        """

        net = Network.objects.get(asn=asn)

        # will hold pdbctl internet exchange objects, keyed by id
        pdbctl_ix = {}

        # will hold ixctl internet exchange objects, keyed by id
        ixctl_ix = {}

        for ixi_port in ixi_ports:
            source, ix_id = ixi_port.port_info_object.ref_ix_id.split(":")

            ix_id = int(ix_id)

            ixi_port.source = source
            ixi_port.remote_ix_id = ix_id

            if source == "pdbctl":
                pdbctl_ix[ix_id] = None
            elif source == "ixctl":
                ixctl_ix[ix_id] = None

        # now get ixctl internet exchange objects

        if ixctl_ix:
            ix_ix = ixctl.InternetExchange().objects(ids=list(ixctl_ix.keys()))
            for ix in ix_ix:
                ixctl_ix[ix.id] = ix

                # if ixctl ix has a peeringdb reference, mark
                # it so it also gets fetched

                if ix.pdb_id:
                    pdbctl_ix[ix.pdb_id] = None

        # now get pdbctl internet exchange objects

        if pdbctl_ix:
            pdb_ix = pdbctl.InternetExchange().objects(ids=list(pdbctl_ix.keys()))
            for ix in pdb_ix:
                pdbctl_ix[ix.id] = ix

        # now augment data from both sources

        for ixi_port in ixi_ports:
            mtu = None

            if ixi_port.source == "ixctl":
                # port has SoT in ixctl

                ix = ixctl_ix[ixi_port.remote_ix_id]

                # ixctl ix has a peeringdb reference, so we can
                # join in MTU from there as ixctl has no MTU field
                # yet.

                pdb_ix_id = ix.pdb_id

                if pdb_ix_id:
                    mtu = pdbctl_ix[pdb_ix_id].mtu
            else:
                # port has SoT in pdbctl

                ix = pdbctl_ix[ixi_port.remote_ix_id]

                mtu = ix.mtu

            ixi_port.prefix4 = net.prefix4
            ixi_port.prefix6 = net.prefix6
            ixi_port.mtu = mtu


@reversion.register
class PortInfo(sot.ReferenceMixin, Base):
    """
    ix member abstraction to allow for private peering
    if ref id is set, uses all fields from that, if not uses local_
    to add private peering, we will probably need to define facility as well, and abstract to this

    ref_id may either point to a pdbctl netixlan object or a ixctl member object
    """

    net = models.ForeignKey(
        Network, on_delete=models.CASCADE, related_name="port_info_qs"
    )

    ref_id = models.CharField(max_length=64, null=True, blank=True)
    # ip_addr

    port = ReferencedObjectField(bridge=Port)

    ip_address_4 = InetAddressField(
        blank=True,
        null=True,
        help_text=_(
            "manually set the ip6 address of this port info - used for manual peer session"
        ),
    )
    ip_address_6 = InetAddressField(
        blank=True,
        null=True,
        help_text=_(
            "manually set the ip4 address of this port info - used for manual peer session"
        ),
    )

    is_route_server_peer = models.BooleanField(null=True)

    mac_address = MACAddressField(null=True, blank=True)

    objects = NetManager()

    class HandleRef:
        tag = "port_info"

    class Meta:
        db_table = "peerctl_port_info"
        verbose_name = "Port Information"
        verbose_name_plural = "Port Information"

    @classmethod
    def require_for_pdb_netixlan(cls, network, port_id, member):
        """
        makes sure a portinfo instance exists for a peeringdb networkixlan
        or fullctl ixctl member object.

        this expects a devicectl port id reference to be passed in

        if the portinfo instance already exists, but the port id is different,
        it will migrate the port info to the new port id

        if the portinfo instance already exists, but the port id is the same,
        it will return the existing port info instance

        if the portinfo instance does not exist, it will create it

        Arguments:

            network (Network): network object
            port_id (int): devicectl port id
            member (pdbctl.InternetExchangeMember or ixctl.InternetExchangeMember): member object
        """

        if not port_id:
            try:
                return cls.objects.get(net=network, ref_id=member.ref_id)
            except cls.DoesNotExist:
                pass

        try:
            port_info = cls.objects.get(net=network, ref_id=member.ref_id)

            if int(port_info.port) != int(port_id):
                try:
                    cls.migrate_ports(port_info.port, port_id, reassign=True)
                    port_info.port = port_id
                except ValueError:
                    return port_info

        except cls.DoesNotExist:
            port_info = cls.objects.create(
                net=network, ref_id=member.ref_id, port=port_id
            )

        port_info.ix

        return port_info

    @classmethod
    def migrate_ports(cls, from_port, to_port, reassign=False):
        """
        Moves all PortInfo instances referenced to Port `from_port` to Port `to_port`

        Arguments:
            from_port (Port): Port object or id to migrate from
            to_port (Port): Port object or id to migrate to
            reassign (bool): If True, will reassign PortInfo instances to `to_port` even if it is already assigned
        """

        # from_port can either be id or port object
        if isinstance(from_port, PortObject):
            from_port = from_port.id

        # to_port can either be id or port object
        if isinstance(to_port, PortObject):
            to_port = to_port.id

        if not from_port:
            raise ValueError("Need to specify port to migrate from")

        if not to_port:
            raise ValueError("Need to specify port to migrate to")

        if not reassign and cls.objects.filter(port=to_port).exists():
            raise ValueError("Port is already assigned")

        cls.objects.filter(port=from_port).update(port=to_port)
        PeerSession.objects.filter(port=from_port).update(port=to_port)

    @property
    @ref_fallback(0)
    def ref_ix_id(self):
        return f"{self.ref_source}:{self.ref.ix_id}"

    @property
    @ref_fallback("")
    def ipaddr4(self):
        if self.port > 0:
            return ip_address_string(self.port.object.ip_address_4)
        if self.ip_address_4:
            return ip_address_string(self.ip_address_4)
        return ip_address_string(self.ref.ipaddr4)

    @property
    @ref_fallback("")
    def ipaddr6(self):
        if self.port > 0:
            return ip_address_string(self.port.object.ip_address_6)
        if self.ip_address_6:
            return ip_address_string(self.ip_address_6)
        return ip_address_string(self.ref.ipaddr6)

    @property
    @ref_fallback(0)
    def info_prefixes4(self):
        return self.ref.net.info_prefixes4

    @property
    @ref_fallback(0)
    def info_prefixes6(self):
        return self.ref.net.info_prefixes6

    @property
    @ref_fallback(False)
    def is_rs_peer(self):
        if self.is_route_server_peer is not None:
            return self.is_route_server_peer
        return self.ref.is_rs_peer

    @property
    @ref_fallback(0)
    def speed(self):
        return self.ref.speed

    @property
    @ref_fallback("")
    def ix_name(self):
        return InternetExchange.ref_bridge(self.ref_source).object(self.ref.ix_id).name

    @property
    @ref_fallback(None)
    def ix(self):
        return InternetExchange.get_or_create(self.ref.ix_id, self.ref_source)

    def __str__(self):
        return "PortInfo({}): {} {} {}".format(
            self.id, self.ix_name, self.ipaddr4, self.ipaddr6
        )

    def ipaddr(self, version):
        if version == 4:
            return self.ipaddr4
        elif version == 6:
            return self.ipaddr6
        raise ValueError(f"Ip Protocol version invalid: {version}")

    def info_prefixes(self, version):
        if version == 4:
            return self.info_prefixes4
        elif version == 6:
            return self.info_prefixes6
        raise ValueError(f"Ip Protocol version invalid: {version}")

    def set_is_route_server_peer(self, value):
        """
        Updates the is_route_server_peer value and also
        syncs to other services (ixctl)
        """
        self.is_route_server_peer = value
        self.save()
        SyncIsRsPeer.create_task(self.net.asn, self.ipaddr4, self.is_route_server_peer)

    def in_same_subnet(self, port_info):
        """
        Checks if the supplied port info is in the same subnet as this port info

        prefix length will be determined by either port_info's ip interface, checking
        self first, then the other port info
        """

        ip4 = ipaddress.ip_interface(self.ipaddr4) if self.ipaddr4 else None
        ip6 = ipaddress.ip_interface(self.ipaddr6) if self.ipaddr6 else None

        other_ip4 = (
            ipaddress.ip_interface(port_info.ipaddr4) if port_info.ipaddr4 else None
        )
        other_ip6 = (
            ipaddress.ip_interface(port_info.ipaddr6) if port_info.ipaddr6 else None
        )

        if ip4 and other_ip4:
            network4 = ip4.network if ip4.network.prefixlen < 32 else other_ip4.network

        if ip6 and other_ip6:
            network6 = ip6.network if ip6.network.prefixlen < 128 else other_ip6.network

        if ip4 and other_ip4:
            return other_ip4.ip in network4 and ip4.ip in network4

        if ip6 and other_ip6:
            return other_ip6.ip in network6 and ip6.ip in network6

        return False


class DeviceObject(devicectl.DeviceCtlEntity):
    @property
    def type_label(self):
        if not self.type:
            return "Unknown"
        return dict(DEVICE_TYPE_CHOICES)[self.type]

    @property
    def peer_session_qs(self):
        return PeerSession.objects.filter(
            models.Q(port__in=[p.id for p in self.ports]) | models.Q(device=self.id)
        )

    @property
    def ports(self):
        return Port().objects(device=self.id)

    def peer_groups(self, net, ip_version):
        """return collection of peer groups"""

        groups = {}

        for peer_session in self.peer_session_qs.filter(
            peer_port__peer_net__net=net, status="ok"
        ):
            policy = get_best_policy(peer_session, ip_version)
            name = policy.peer_group
            if name not in groups:
                groups[name] = [peer_session]
            else:
                groups[name].append(peer_session)

        return groups

    def _peer_groups_netom0_data(self, net, ip_version, peer_groups, **kwargs):
        """
        Fills the dict passed in `peer_groups` with groups and netom0
        peering object literals according to the specified ip_version

        This method is called automatically by `peer_groups_netom0_data`
        for both ip protocol versions.

        Arguments:
            - net <Network>
            - ip_version <int>: 4 or 6
            - peer_groups <dict>: this dictionary will be updated

                { peer_group_name : [netom0_data, ...] }
        """

        members = kwargs.get("members")

        for name, peer_session_set in list(self.peer_groups(net, ip_version).items()):
            if name not in peer_groups:
                peer_groups[name] = []

            for peer_session in peer_session_set:
                policy = get_best_policy(peer_session, ip_version)
                addr = peer_session.peer_port.port_info.ipaddr(ip_version)

                if not addr:
                    continue

                if members and peer_session.peer_port.port_info.ref_id not in members:
                    continue

                peer = {
                    "name": peer_session.peer_port.peer_net.peer.name,
                    "peer_as": peer_session.peer_port.peer_net.peer.asn,
                    "peer_type": "external",
                    "neighbor_address": addr,
                    "local_as": peer_session.peer_port.peer_net.net.asn,
                    "auth_password": peer_session.peer_port.peer_net.md5,
                    "max_prefixes": peer_session.peer_port.peer_net.info_prefixes(
                        ip_version
                    ),
                    "import_policy": policy.import_policy,
                    "export_policy": policy.export_policy,
                }
                peer_groups[name].append(peer)

    def peer_groups_netom0_data(self, net, **kwargs):
        """
        Returns dict with peer_groups and netom0 data for each
        peer

        Arguments:
            - net <Network>
        """
        peer_groups = {}
        self._peer_groups_netom0_data(net, 4, peer_groups, **kwargs)
        self._peer_groups_netom0_data(net, 6, peer_groups, **kwargs)
        r = {"peer_groups": peer_groups}
        return r


class Device(devicectl.Device):
    DoesNotExist = Exception

    class Meta(devicectl.Device.Meta):
        data_object_cls = DeviceObject


@reversion.register
class PeerPort(Base):
    # owner network
    # net = models.ForeignKey(Network) #, on_delete=models.CASCADE, related_name='+')

    peer_net = models.ForeignKey(
        PeerNetwork, on_delete=models.CASCADE, related_name="+"
    )
    #    virtual_port = models.ForeignKey(VirtualPort, on_delete=models.CASCADE, related_name='+')
    port_info = models.ForeignKey(PortInfo, on_delete=models.CASCADE, related_name="+")

    interface_name = models.CharField(
        max_length=255, null=True, blank=True, help_text=_("Peer interface name")
    )

    class HandleRef:
        tag = "peer_port"

    class Meta:
        db_table = "peerctl_peer_port"

    @classmethod
    @reversion.create_revision()
    def get_or_create(cls, port_info, peer_net):
        try:
            obj = cls.objects.get(port_info=port_info, peer_net=peer_net)
        except cls.DoesNotExist:
            obj = cls.objects.create(
                port_info=port_info, peer_net=peer_net, status="ok"
            )
        return obj

    @classmethod
    @reversion.create_revision()
    def get_or_create_from_members(cls, member_a, member_b):
        """
        Creates a peer_port instance using two member objects
        with `member_a` being the initiator.
        """

        # get ports for both members
        try:
            net_a = Network.objects.get(asn=member_a.asn)
        except Network.DoesNotExist:
            net_a = Network.get_or_create(member_a.asn, None)

        try:
            net_b = Network.objects.get(asn=member_b.asn)
        except Network.DoesNotExist:
            net_b = Network.get_or_create(member_b.asn, None)

        port_info_a = PortInfo.require_for_pdb_netixlan(net_a, 0, member_a)
        port_info_b = PortInfo.require_for_pdb_netixlan(net_b, 0, member_b)

        # get peer_net querying for member_a's network as
        # the initiator/owner
        peer_net = PeerNetwork.get_or_create(port_info_a.net, port_info_b.net)

        peer_port = PeerPort.get_or_create(port_info_b, peer_net)

        return peer_port

    def __str__(self):
        return f"PeerPort({self.id}): {self.port_info}"


# class BGPSession(Base):
@grainy_model(namespace="peer_session")
@reversion.register
class PeerSession(PolicyHolderMixin, meta.DataMixin, Base):
    """
    preferences and policy for specific peer::ix::session

    Need to have this level over the PeerPort to account for single Network
    port going to a Peer with 2 physical ports (with different IPs)
    """

    port = ReferencedObjectField(bridge=Port, null=True, blank=True)
    peer_port = models.ForeignKey(
        PeerPort, on_delete=models.CASCADE, related_name="peer_sessions"
    )
    peer_session_type = models.CharField(
        max_length=255,
        choices=(
            ("peer", _("Peer")),
            ("transit", _("Transit")),
            ("customer", _("Customer")),
            ("core", _("Core")),
        ),
        default="peer",
    )

    meta4 = models.JSONField(null=True, blank=True)
    meta6 = models.JSONField(null=True, blank=True)

    device = ReferencedObjectField(
        bridge=devicectl.Device,
        null=True,
        blank=True,
        help_text=_("Session is running on this device"),
    )

    class Meta:
        unique_together = ("port", "peer_port")
        db_table = "peerctl_peer_session"

    class HandleRef:
        tag = "peer_session"

    class DataSchema:

        """
        Session meta data
        """

        meta4 = PeerSessionSchema()
        meta6 = PeerSessionSchema()

    @classmethod
    @reversion.create_revision()
    def get_or_create(cls, port, peer_port, create_status="ok"):
        try:
            obj = cls.objects.get(port=port.pk, peer_port=peer_port)

        except cls.DoesNotExist:
            obj = cls.objects.create(
                port=port.pk, peer_port=peer_port, status=create_status
            )

        return obj

    @classmethod
    def get_unique(cls, asn, device, peer_asn, peer_ip):
        """
        Returns a unique PeerSession instance for the given
        port, peer_asn and peer_port

        port can be a devicectl port reference object, referece id or an ip address

        Arguments:

            - asn <int> AS number of the owner network
            - device <int> devicectl device id
            - peer_asn <int> AS number of the peer network
            - peer_ip <ipaddress> IP address of the peer network

        Returns:

            - PeerSession
        """

        # load session related objects, if they dont exist
        # no session exists and we can return None

        try:
            net = Network.objects.get(asn=asn)
            peer = Network.objects.get(asn=peer_asn)
            peer_net = PeerNetwork.objects.get(net=net, peer=peer)
        except (Network.DoesNotExist, PeerNetwork.DoesNotExist):
            return None

        # Resolve the port to a PortObject instance

        peer_ports = PeerPort.objects.filter(
            peer_net=peer_net, peer_sessions__device=int(device)
        )

        # loop through the peer ports to look for an ip match

        peer_port = None
        session = None
        peer_ip = ipaddress.ip_interface(peer_ip)

        for _peer_port in peer_ports:
            if peer_ip.version == 4 and not _peer_port.port_info.ipaddr4:
                continue

            if peer_ip.version == 6 and not _peer_port.port_info.ipaddr6:
                continue

            if (
                peer_ip.version == 4
                and ipaddress.ip_interface(_peer_port.port_info.ipaddr4).ip
                == peer_ip.ip
            ):
                peer_port = _peer_port
                break
            elif (
                peer_ip.version == 6
                and ipaddress.ip_interface(_peer_port.port_info.ipaddr6).ip
                == peer_ip.ip
            ):
                peer_port = _peer_port
                break

        # we got all pieces now to query the session

        if peer_port:
            session = cls.objects.filter(
                device=int(device), peer_port=peer_port
            ).first()

        if session:
            return session

        # no session found, see if there any group candidates

        peer_port = None

        for _peer_port in peer_ports:
            if (
                peer_ip.version == 4
                and _peer_port.port_info.ipaddr6
                and not _peer_port.port_info.ipaddr4
            ):
                peer_port = _peer_port
                break

            if (
                peer_ip.version == 6
                and _peer_port.port_info.ipaddr4
                and not _peer_port.port_info.ipaddr6
            ):
                peer_port = _peer_port
                break

        return cls.objects.filter(device=int(device), peer_port=peer_port).first()

    @property
    def ip4(self):
        return ip_address_string(self.port.object.ip_address_4)

    @property
    def ip6(self):
        return ip_address_string(self.port.object.ip_address_6)

    @property
    def peer_ip4(self):
        return self.peer_port.port_info.ipaddr4

    @property
    def peer_ip6(self):
        return self.peer_port.port_info.ipaddr6

    @property
    def peer_asn(self):
        return self.peer_port.peer_net.peer.asn

    @property
    def peer_is_managed(self):
        return self.peer_port.port_info.port > 0

    @property
    def user(self):
        """
        Returns the user that created this peer session
        using historic revision data
        """
        versions = reversion.models.Version.objects.get_for_object(self)
        first_version = versions.first()
        if first_version:
            return first_version.revision.user
        return None

    @property
    def devices(self):
        """
        TODO: this is deprecated by the device property, but
        references need to be set on all existing sessions first

        TODO: multiple devices / ports for same session?
        """

        if self.device:
            # device reference is set return it
            return [self.device.object]

        # otherwise get it from port
        devices = []
        if self.port:
            if self.port.object.device:
                return [self.port.object.device]
            return [device for device in Device().objects(port=int(self.port))]
        else:
            return devices

    @property
    def policy_parents(self):
        if self.port:
            return [self.peer_port.peer_net, self.port.object]
        return [self.peer_port.peer_net]

    def __str__(self):
        return "Session ({}): AS{} -> AS{}".format(
            self.id, self.peer_port.peer_net.net.asn, self.peer_port.peer_net.peer.asn
        )


@grainy_model(namespace="peerctl.user.{user.id}.wish")
@reversion.register
class Wish(HandleRefModel):
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="+"
    )
    path = models.CharField(max_length=1024)
    text = models.TextField()
    ticket = models.IntegerField(default=0)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default="open")

    class HandleRef:
        tag = "wish"

    class Meta:
        db_table = "peerctl_wish"
        verbose_name_plural = "Feature Requests"

    def notify(self):
        subject = "Wish Submission"
        body = (
            "User {s.user.username}<{s.user.email}> has submitted the following wish "
            "in the {s.path} component:\n\n{s.text}".format(s=self)
        )
        send_mail_from_default(
            subject,
            body,
            [settings.WISH_NOTIFY_EMAIL],
            debug_address=settings.WISH_NOTIFY_EMAIL,
        )


class TemplateBase(models.Model):
    net = models.ForeignKey(Network, on_delete=models.CASCADE, related_name="+")
    body = models.TextField()
    name = models.CharField(max_length=255)

    # if set, calling render() will always return
    # this as content - should generally be set
    # on the object instance and not the class
    content_override = None

    class Meta:
        abstract = True
        unique_together = (("net", "name"),)

    @property
    def template_path(self):
        """
        Returns the template path using the handleref tag and
        type
        """
        return os.path.join(self.HandleRef.tag, f"{self.type}.txt")

    @property
    def template_loader_paths(self):
        return [os.path.join(os.path.dirname(__file__), "..", "templates", "peerctl")]

    @property
    def context(self):
        if not hasattr(self, "_context"):
            self._context = {}
        return self._context

    def get_data(self):
        return dict()

    def get_env(self):
        """
        Returns the jinja template environment
        """

        if self.body:
            # if body is not empty, we use a dict loader
            # to make jinja load it as the template
            loader = DictLoader({self.template_path: self.body})
        else:
            # if body is empty we will load the default
            # template from file
            #
            # all templates are located at
            # templates/peerctl/<handle_ref_tag>
            loader = FileSystemLoader(self.template_loader_paths)

        env = Environment(trim_blocks=True, loader=loader, autoescape=True)

        env.filters["make_variable_name"] = make_variable_name

        return env

    def render(self):
        """
        renders a template to UTF-8
        """

        # if content_override is specified return that immediately
        # and skip the template rendering entirely
        if self.content_override:
            return self.content_override

        env = self.get_env()
        template = env.get_template(self.template_path)
        try:
            return strip_tags(template.render(**self.get_data()))
        except Exception as exc:
            import traceback

            print(traceback.format_exc())
            raise TemplateRenderError(exc)


@reversion.register
@grainy_model(
    namespace=Network.Grainy.namespace(),
    namespace_instance="{namespace}.{instance.net.asn}.device.{instance.id}",
)
class DeviceTemplate(Base, TemplateBase):
    type = models.CharField(max_length=255, choices=const.DEVICE_TEMPLATE_TYPES)
    default = models.BooleanField(default=False)

    class Meta:
        db_table = "peerctl_device_template"

    class HandleRef:
        tag = "device_template"

    @property
    def template_path(self):
        return const.DEVICE_TEMPLATES[self.type]

    @property
    def template_loader_paths(self):
        return [settings.NETOM_TEMPLATE_DIR] + super().template_loader_paths

    def render(self):
        r = super().render()
        if not r:
            return "There were no active sessions to generate configuration output for."
        return r

    def get_data(self):
        data = super().get_data()
        ctx = self.context
        device = ctx.get("device")
        net = ctx.get("net")
        member = ctx.get("member")
        if member:
            member = [member]

        data.update(**device.peer_groups_netom0_data(net, members=member))
        data["device"] = {"type": device.type}
        data["ports"] = [port for port in device.ports]

        return data


@reversion.register
@grainy_model(
    namespace=Network.Grainy.namespace(),
    namespace_instance="{namespace}.{instance.net.asn}.device.{instance.id}",
)
class EmailTemplate(Base, TemplateBase):
    type = models.CharField(max_length=255, choices=EMAIL_TEMPLATE_TYPES)
    default = models.BooleanField(default=False)

    class Meta:
        db_table = "peerctl_email_template"

    class HandleRef:
        tag = "email_template"

    def get_data(self):
        """
        Returns a dict containing all environment variables to
        be available during template rendering
        """
        data = super().get_data()

        ctx = self.context

        asn = ctx.get("asn")

        ix_ids = []

        for member in sot.InternetExchangeMember().objects(asn=self.net.asn):
            ref_ix_id = member.ref_rel_id("ix_id")
            if ref_ix_id not in ix_ids:
                ix_ids.append(ref_ix_id)

        data.update(
            {
                "my": {
                    "company_name": self.net.name,
                    "asn": self.net.asn,
                    "website": self.net.website,
                    "contact": self.net.peer_contact_email,
                    "description": self.net.info_type,
                    "exchanges": InternetExchange.objects.filter(ref_id__in=ix_ids),
                }
            }
        )

        if ctx.get("peer"):
            peer = ctx.get("peer")
            mutual_locations = []
            for ix_id in self.net.get_mutual_locations(peer.asn):
                ix_source, ix_id = ix_id.split(":")
                mutual_locations.append(
                    MutualLocation(
                        InternetExchange.get_or_create(int(ix_id), ix_source),
                        self.net,
                        peer,
                    )
                )
            data.update(
                {
                    "peer": {
                        "company_name": peer.name,
                        "asn": peer.asn,
                        "contact": get_peer_contact_email(peer.asn),
                    },
                    "mutual_locations": mutual_locations,
                }
            )
        else:
            # no peer information was passed along to the template

            # if the asn is set try to retrieve network infromation from it

            other_net = pdbctl.Network().first(asn=asn)
            if other_net:
                company_name = other_net.name
            elif asn:
                company_name = f"ASN{asn}"
            else:
                company_name = ""

            data["peer"] = {"asn": asn, "company_name": company_name}

        if "sessions" in ctx:
            data.update(
                {
                    "sessions": [
                        {
                            "peer_ip4": session.peer_port.port_info.ipaddr4,
                            "peer_ip6": session.peer_port.port_info.ipaddr6,
                            "ip4": session.port.object.port_info_object.ipaddr4,
                            "ip6": session.port.object.port_info_object.ipaddr6,
                            "prefix_length4": session.port.object.port_info_object.info_prefixes4,
                            "prefix_length6": session.port.object.port_info_object.info_prefixes6,
                        }
                        for session in ctx.get("sessions")
                        if session.port
                    ]
                }
            )
        else:
            data.update({"sessions": []})

        if "selected_exchanges" in ctx:
            data.update(selected_exchanges=ctx["selected_exchanges"])

        return data


# TODO  dont need anymore (fullctl auditlog)
@grainy_model(
    namespace="peerctl.net", namespace_instance="{namespace}.{instance.net.asn}"
)
@reversion.register
class AuditLog(HandleRefModel):
    net = models.ForeignKey(
        Network, related_name="qset_auditlog", on_delete=models.CASCADE
    )

    event = models.CharField(max_length=255, choices=const.AUDIT_EVENTS)

    user = models.ForeignKey(
        get_user_model(), on_delete=models.PROTECT, related_name="peerctl_auditlog"
    )

    data = models.TextField(null=True, blank=True)

    class HandleRef:
        tag = "auditlog"

    class Meta:
        db_table = "peerctl_auditlog"

    @classmethod
    def clean_data(cls, value):
        if isinstance(value, dict):
            return json.dumps(value)
        return value

    @classmethod
    def log(cls, network, event, user, **data):
        log = cls(net=network, event=event, user=user, data=cls.clean_data(data))
        log.full_clean()
        log.save()
        log.write_to_file()
        return log

    @classmethod
    def log_peer_session(cls, event, peer_session, user):
        return

    @classmethod
    def log_peer_session_request(cls, peer_session, user):
        return cls.log_peer_session("peer_session-request", peer_session, user)

    @classmethod
    def log_peer_session_add(cls, peer_session, user):
        return cls.log_peer_session("peer_session-add", peer_session, user)

    @classmethod
    def log_peer_session_del(cls, peer_session, user):
        return cls.log_peer_session("peer_session-del", peer_session, user)

    @classmethod
    def log_peer_session_mod(cls, peer_session, user):
        return cls.log_peer_session("peer_session-mod", peer_session, user)

    @classmethod
    def log_email(cls, email_log):
        return cls.log(
            email_log.net,
            "email",
            email_log.user,
            email_log=email_log.id,
            subject=email_log.subject,
            recipients=email_log.recipients,
            recipient=email_log.recipient,
            sender=email_log.sender_address,
            path=email_log.path,
        )

    @property
    def extra(self):
        if self.data:
            if not hasattr(self, "_extra"):
                self._extra = json.loads(self.data)
        return getattr(self, "_extra", {})

    @property
    def event_name(self):
        return dict(const.AUDIT_EVENTS).get(self.event)

    def write_to_file(self):
        extra = ", ".join([f"{k}={v}" for k, v in self.extra.items()])
        msg = "[AS{}] {} was performed by {}: {}".format(
            self.net.asn, self.event_name, self.user.username, extra
        )
        logging.getLogger("audit").info(msg)
        self.recent_log = msg


@grainy_model(
    namespace="peerctl.net", namespace_instance="{namespace}.{instance.net.asn}"
)
@reversion.register
class EmailLog(HandleRefModel):
    net = models.ForeignKey(
        Network, related_name="qset_email_log", on_delete=models.CASCADE
    )

    user = models.ForeignKey(get_user_model(), on_delete=models.PROTECT)
    sender_address = models.CharField(max_length=255)

    subject = models.CharField(max_length=255)

    body = models.TextField()

    origin = models.CharField(max_length=255, choices=const.EMAIL_ORIGIN)

    class HandleRef:
        tag = "email_log"

    class Meta:
        db_table = "peerctl_email_log"

    @classmethod
    def log(cls, net, user, subject, body, origin, **kwargs):
        log = cls(
            net=net,
            user=user,
            subject=subject,
            body=body,
            origin=origin,
            sender_address=kwargs.get("sender_address", user.email),
        )
        log.full_clean()
        log.save()

        recipients = kwargs.get("recipients") or []

        for recipient in recipients:
            if recipient.get("email"):
                EmailLogRecipient.objects.create(email_log=log, **recipient)

        AuditLog.log_email(log)

        return log

    @classmethod
    def log_peer_session_workflow(cls, asn, peer_asn, user, contact, subject, body):
        net = Network.objects.get(asn=asn)
        return cls.log(
            net,
            user,
            subject,
            body,
            "peer_session-workflow",
            recipients=[{"email": contact, "asn": peer_asn}],
            sender_address=net.peer_contact_email,
        )

    @property
    def recipients(self):
        return self.qset_recipient.count()

    @property
    def recipient(self):
        num = self.recipients
        if num == 1:
            return self.qset_recipient.first().email
        elif num > 1:
            return "multiple"
        return None

    @property
    def path(self):
        return f"/admctl/django_peerctl/email_log/{self.id}/change/"

    def queue(self):
        """
        Will mark the email log as queued, and the email be be sent by the
        peerctl_email_queue command the next time it runs
        """
        self.status = "queued"
        self.save()
        return self

    def send(self):
        if self.status == "queued":
            self.status = "ok"
            self.save()

            for recipient in self.qset_recipient.all():
                send_mail_from_default(
                    self.subject,
                    self.body,
                    [recipient.email],
                    reply_to=self.sender_address,
                )


@grainy_model(
    namespace="peerctl.net",
    namespace_instance="{namespace}.{instance.email_log.net.asn}",
)
class EmailLogRecipient(models.Model):
    email_log = models.ForeignKey(
        EmailLog, related_name="qset_recipient", on_delete=models.CASCADE
    )

    email = models.CharField(max_length=255)
    asn = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "peerctl_email_log_recipient"


@grainy_model(namespace="user")
@reversion.register
class UserPreferences(HandleRefModel):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    email_opt_features = models.BooleanField(default=True)
    email_opt_offers = models.BooleanField(default=True)

    class HandleRef:
        tag = "user"

    class Meta:
        db_table = "peerctl_user"

    @classmethod
    def get_or_create(cls, user):
        try:
            return cls.objects.get(user=user)
        except cls.DoesNotExist:
            return cls.objects.create(user=user, status="ok")


class UserSession(models.Model):
    """
    Tie client session ids to user ids
    """

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)


# class UserNetworkPerms(models.Model):
#    pass


# class User(AbstractBaseUser, PermissionsMixin):
#    class Meta:
#        db_table = "peeringdb_user"
#        verbose_name = _('user')
#        verbose_name_plural = _('users')
#
