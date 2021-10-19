import collections
import datetime
import json
import logging
import os.path

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
from django_handleref.models import HandleRefModel
from django_inet.models import ASNField, IPAddressField, IPPrefixField
from netfields import MACAddressField
from fullctl.django.models.concrete import Instance
from fullctl.service_bridge.data import Relationships
from jinja2 import DictLoader, Environment, FileSystemLoader


from django_peerctl import const
from django_peerctl.email import send_mail_from_default
from django_peerctl.exceptions import (
    ReferenceSourceInvalid,
    TemplateRenderError,
    UsageLimitError,
)
from django_peerctl.helpers import get_best_policy, get_peer_contact_email
from django_peerctl.templating import make_variable_name
from django_peerctl.models.tasks import SyncMacAddress, SyncASSet


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
            except (sot.ReferenceNotFoundError, ObjectDoesNotExist):
                if isinstance(value, collections.Callable):
                    return value(*args)
                return value

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
        for peerses in self.net.peerses_at_ix(ix_id=None):
            if get_best_policy(peerses, 4) == self:
                count += 1
            elif get_best_policy(peerses, 6) == self:
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


@grainy_model(namespace="admin")
@reversion.register
class Organization(UsageLimitMixin, Base):
    name = models.CharField(max_length=128, unique=True)

    class Meta:
        db_table = "peerctl_org"

    class HandleRef:
        tag = "org"

    def __str__(self):
        return f"Organization({self.id}): {self.name}"


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

    # default_policy

    class HandleRef:
        tag = "net"

    class Meta:
        db_table = "peerctl_net"

    def __str__(self):
        return f"AS{self.asn}"

    @classmethod
    @reversion.create_revision()
    def get_or_create(cls, asn):
        """get or create a network object from an ASN"""
        try:
            obj = cls.objects.get(asn=asn)

        except cls.DoesNotExist:
            obj = cls.objects.create(asn=asn, status="ok")

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
        return get_peer_contact_email(self.asn)

    @property
    @ref_fallback("")
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
    def as_set(self):
        if not self.as_set_override:
            return self.ref.irr_as_set or ""
        return self.as_set_override

    @property
    def as_set_source(self):
        if self.as_set_override:
            return "peerctl"
        if self.ref.irr_as_set:
            return "pdbctl"
        return None

    @property
    def peerses_set(self):
        """
        returns all peer sessions owned by this network
        """
        return PeerSession.objects.filter(port__portinfo__net=self)

    @property
    def peernet_set(self):
        """
        returns all PeerNetworks owned by this network
        """
        return PeerNetwork.objects.filter(net=self).select_related("net", "peer")

    def peernets_at_ix(self, ix_id=None):

        """
        returns all PeerNetworks owned by this network at the specified
        exchange
        """
        qset = self.peernet_set
        if ix_id:
            exchange = InternetExchange.objects.get(id=ix_id)
            ref_source, ref_id = exchange.ref_parts
            members = [
                n.ref_id for n in PortInfo.ref_bridge(ref_source).objects(ix=ref_id)
            ]
            peerport_qset = PeerPort.objects.filter(portinfo__ref_id__in=members)
            ids = [peerport.peernet_id for peerport in peerport_qset]
            qset = qset.filter(id__in=ids)
        return qset

    def peerses_at_ix(self, ix_id=None):
        qset = self.peerses_set

        if ix_id:
            exchange = InternetExchange.objects.get(id=ix_id)
            ref_source, ref_id = exchange.ref_parts
            members = [
                n.ref_id for n in PortInfo.ref_bridge(ref_source).objects(ix=ref_id)
            ]
            qset = qset.filter(peerport__portinfo__ref_id__in=members)

        return qset

    def get_max_sessions(self):
        """
        Returns max sessions allowed for this network

        Will first check if there is a limit set on the organization
        and if so return that limit instead

        If neither the organization nor the network has a limit
        defined the free usage limit will be returned
        """

        # XXX aaactl metered / plans
        return 99999

        # if self.org_id and self.org.max_sessions:
        #     return self.org.max_sessions
        # return self.max_sessions or settings.FREE_LIMITS.get("MAX_PEERSES")

    def validate_limits(self):
        maxses = self.get_max_sessions()
        if self.peerses_set.count() + 1 > maxses:
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
        peerses_qset = (
            self.peerses_at_ix(ix_id)
            .filter(status="ok")
            .select_related("peerport", "peerport__peernet", "peerport__peernet__peer")
        )
        r = list(
            {
                peerses.peerport.peernet.peer.contacts.get(role)
                for peerses in peerses_qset
            }
        )
        try:
            r.remove(None)
        except:
            pass
        return r

    def set_as_set(self, as_set):
        self.as_set_override = as_set
        self.save()
        SyncASSet.create_task(self.asn, self.as_set_override)


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
        db_table = "peerctl_peernet"
        verbose_name = "Network to Peer Relationship"
        verbose_name_plural = "Network to Peer Relationships"

    class HandleRef:
        tag = "peernet"

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
                # XXX: ixctl needs to provide country for source of truth
                # exchanges
                country=getattr(ix, "country", "US"),
                ref_id=ix.ref_id,
            )

        return obj

    def __str__(self):
        return f"InternetExchange({self.id}): {self.name}"


@reversion.register
class PortInfo(sot.ReferenceMixin, Base):
    """
    ix member abstraction to allow for private peering
    if ref id is set, uses all fields from that, if not uses local_
    to add private peering, we will probably need to define facility as well, and abstract to this

    ref_id may either point to a pdbctl netixlan object or a ixctl member object
    """

    net = models.ForeignKey(
        Network, on_delete=models.CASCADE, related_name="portinfo_qs"
    )

    ref_id = models.CharField(max_length=64, null=True, blank=True)
    # ip_addr

    class HandleRef:
        tag = "portinfo"

    class Meta:
        db_table = "peerctl_portinfo"
        verbose_name = "Port Information"
        verbose_name_plural = "Port Information"

    @property
    def ref_ix_id(self):
        return f"{self.ref_source}:{self.ref.ix_id}"

    @property
    @ref_fallback("")
    def ipaddr4(self):
        return self.ref.ipaddr4

    @property
    @ref_fallback("")
    def ipaddr6(self):
        return self.ref.ipaddr6

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


# TODOCLIENT push
# TODO djnetworkdevice
# TODO devicectl
@grainy_model(
    namespace=Network.Grainy.namespace(),
    namespace_instance="{namespace}.{instance.net.asn}.device.{instance.id}",
)
@reversion.register
class Device(Base):
    net = models.ForeignKey(Network, on_delete=models.CASCADE, related_name="device_qs")
    name = models.CharField(max_length=255)
    description = DescriptionField()
    type = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="type of device (software)",
        choices=DEVICE_TYPE_CHOICES,
    )

    # fk pdb fac
    # device info
    # management_address

    class HandleRef:
        tag = "device"
        unique_together = ("net", "name")

    class Meta:
        db_table = "peerctl_device"

    @property
    def type_label(self):
        if not self.type:
            return "Unknown"
        return dict(DEVICE_TYPE_CHOICES)[self.type]

    @property
    @ref_fallback(lambda o: o.name)
    def display_name(self):
        try:
            portinfo = self.port_qs.first().portinfo
        except AttributeError:
            return self.name
        ix_id = portinfo.ref.ix_id
        ix = InternetExchange.get_or_create(ix_id, portinfo.ref_source)
        return f"{ix.name}-{portinfo.ref_id}"

    @property
    def logport_qs(self):
        logport_ids = [p.logport_id for p in self.phyport_qs.all()]
        return LogicalPort.objects.filter(id__in=logport_ids)

    @property
    def virtport_qs(self):
        return VirtualPort.objects.filter(logport__in=self.logport_qs)

    @property
    def port_qs(self):
        return Port.objects.filter(virtport__in=self.virtport_qs)

    @property
    def peerses_qs(self):
        port = self.port_qs.first()
        return PeerSession.objects.filter(
            peerport__portinfo__ref_id__in={
                n.ref_id for n in port.get_available_peers()
            }
        )

    def peer_groups(self, net, ip_version):
        """return collection of peer groups"""

        groups = {}

        for peerses in self.peerses_qs.filter(peerport__peernet__net=net, status="ok"):
            policy = get_best_policy(peerses, ip_version)
            name = policy.peer_group
            if name not in groups:
                groups[name] = [peerses]
            else:
                groups[name].append(peerses)

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

        for name, peerses_set in list(self.peer_groups(net, ip_version).items()):
            peer_groups[name] = []
            for peerses in peerses_set:
                policy = get_best_policy(peerses, ip_version)
                addr = peerses.peerport.portinfo.ipaddr(ip_version)

                if not addr:
                    continue

                if members and peerses.peerport.portinfo.ref_id not in members:
                    continue

                peer = {
                    "name": peerses.peerport.peernet.peer.name,
                    "peer_as": peerses.peerport.peernet.peer.asn,
                    "peer_type": "external",
                    "neighbor_address": addr,
                    "local_as": peerses.peerport.peernet.net.asn,
                    "auth_password": peerses.peerport.peernet.md5,
                    "max_prefixes": peerses.peerport.peernet.info_prefixes(ip_version),
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
        return {"peer_groups": peer_groups}


# TODO djnetworkdevice
@reversion.register
class PhysicalPort(Base):
    device = models.ForeignKey(
        Device,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="phyport_qs",
    )
    name = models.CharField(max_length=255, unique=False)
    description = DescriptionField()

    logport = models.ForeignKey(
        "LogicalPort",
        null=True,
        blank=True,
        help_text="logical port this is a member of",
        on_delete=models.CASCADE,
        related_name="phyport_qs",
    )

    class HandleRef:
        tag = "phyport"

    class Meta:
        db_table = "peerctl_phyport"


# TODO djnetworkdevice
@reversion.register
class LogicalPort(Base):
    """
    Logical port a peering session is build on
    could be a vlan ID on a physical port
    for LAGS, would be the ae port
    """

    name = models.CharField(max_length=255, blank=True)
    description = DescriptionField()
    #    mtu = models.IntegerField(blank=True, null=True)
    trunk = models.IntegerField(blank=True, null=True)
    channel = models.IntegerField(blank=True, null=True)

    #    notes = models.TextField(blank=True)

    class HandleRef:
        tag = "logport"

    class Meta:
        db_table = "peerctl_logport"


@reversion.register
class VirtualPort(Base):
    """
    Port a peering session is build on, ties a virtual port back to a logical port
    """

    #    net = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='+')
    logport = models.ForeignKey(
        LogicalPort,
        null=True,
        blank=True,
        help_text="logical port",
        on_delete=models.CASCADE,
        related_name="virtport_qs",
    )

    vlan_id = models.IntegerField()

    mac_address = MACAddressField(blank=True, null=True)

    class HandleRef:
        tag = "virtport"

    class Meta:
        db_table = "peerctl_virtport"


@reversion.register
class Port(PolicyHolderMixin, Base):
    """
    preferences and policy for specific ix
    use case: if network has multiple IX ports
    makes it easy to support different policy on separate ports, and for the 99% who just have a single IP, it's no different
    """

    virtport = models.ForeignKey(
        VirtualPort, on_delete=models.CASCADE, related_name="+"
    )
    portinfo = models.ForeignKey(
        PortInfo, on_delete=models.CASCADE, related_name="port_qs"
    )

    class HandleRef:
        tag = "port"

    class Meta:
        db_table = "peerctl_port"

    @classmethod
    @reversion.create_revision()
    def get_or_create(cls, member):

        net, created = Network.objects.get_or_create(asn=member.asn)

        portinfo = PortInfo.objects.filter(net=net, ref_id=member.ref_id)

        # if port info with net , member already
        # exists, skip
        if portinfo.exists():
            try:
                portinfo = portinfo.first()
                port = Port.objects.get(portinfo=portinfo)
                return port
            except Port.DoesNotExist:
                pass
        else:
            portinfo = None

        # common name
        name = f"member:{member.ref_id}"

        # create device
        device = Device.objects.create(name=name, net=net, status="ok")

        # create logical port
        logport = LogicalPort.objects.create(name=name, status="ok")

        # create physical port
        phyport = PhysicalPort.objects.create(
            device=device, name=name, status="ok", logport=logport
        )

        # create virtual port
        virtport = VirtualPort.objects.create(logport=logport, vlan_id=0, status="ok")

        # create port info
        if not portinfo:
            portinfo = PortInfo.objects.create(
                net=net, ref_id=member.ref_id, status="ok"
            )
        else:
            portinfo.status = "ok"
            portinfo.save()

        # create port
        port = Port.objects.create(virtport=virtport, portinfo=portinfo, status="ok")

        exchange = InternetExchange.get_or_create(member.ix, member.source)

        return port

    @property
    def devices(self):
        """
        Return device for the port
        """
        # TODO: Looks like it'd be possible to have more than one device
        # through logport?

        logport_id = self.virtport.logport_id
        phyport_qs = PhysicalPort.objects.filter(logport_id=logport_id)
        if not phyport_qs.exists():
            return None
        return [phyport.device for phyport in phyport_qs]

    @property
    def policy_parents(self):
        return [self.portinfo.net]

    @property
    def peerses_qs_prefetched(self):
        """
        Returns an instance of the peerses_qs set that has peerport
        and portinfo preselected for performance.
        """
        # FIXME: should see if there is a way to tell django to automatically
        # do that for a set.
        if not hasattr(self, "_peerses_qs_prefetched"):
            self._peerses_qs_prefetched = self.peerses_qs.select_related(
                "peerport", "peerport__portinfo", "peerport__peernet"
            ).all()
        return self._peerses_qs_prefetched

    @property
    def mac_address(self):
        return self.virtport.mac_address or ""

    def set_mac_address(self, mac_address):

        self.virtport.mac_address = mac_address
        self.virtport.full_clean()
        self.virtport.save()

        source, id = self.portinfo.ref_parts

        if source == "ixctl":
            SyncMacAddress.create_task(id, mac_address)

    def get_peerses(self, member):
        """
        Returns the peering session for this port
        and a member
        """

        try:
            for peerses in self.peerses_qs_prefetched:
                if peerses.peerport.portinfo.ref_id == member.ref_id:
                    return peerses
        except PeerSession.DoesNotExist:
            return None
        return None

    # FIXME: should probably be a property
    @ref_fallback([])
    def get_available_peers(self):
        """
        Returns queryset for all available peers at
        this port
        """

        ref_source, ref_id = self.portinfo.ref_parts

        query = self.portinfo.ref_objects(peers=ref_id)

        peers = [peer for peer in query]

        Relationships.preload("net", peers)

        return peers

    def __str__(self):
        return f"Port({self.id}): {self.portinfo}"


@reversion.register
class PeerPort(Base):
    # owner network
    # net = models.ForeignKey(Network) #, on_delete=models.CASCADE, related_name='+')

    peernet = models.ForeignKey(PeerNetwork, on_delete=models.CASCADE, related_name="+")
    #    virtport = models.ForeignKey(VirtualPort, on_delete=models.CASCADE, related_name='+')
    portinfo = models.ForeignKey(PortInfo, on_delete=models.CASCADE, related_name="+")

    class HandleRef:
        tag = "peerport"

    class Meta:
        db_table = "peerctl_peerport"

    @classmethod
    @reversion.create_revision()
    def get_or_create(cls, portinfo, peernet):
        try:
            obj = cls.objects.get(portinfo=portinfo, peernet=peernet)
        except cls.DoesNotExist:
            obj = cls.objects.create(portinfo=portinfo, peernet=peernet, status="ok")
        return obj

    @classmethod
    @reversion.create_revision()
    def get_or_create_from_members(cls, member_a, member_b):
        """
        Creates a peerport instance using two member objects
        with `member_a` being the initiator.
        """

        # get ports for both members
        port_a = Port.get_or_create(member_a)
        port_b = Port.get_or_create(member_b)

        # get peernet querying for member_a's network as
        # the initiator/owner
        peernet = PeerNetwork.get_or_create(port_a.portinfo.net, port_b.portinfo.net)

        peerport = PeerPort.get_or_create(port_b.portinfo, peernet)

        return peerport

    def __str__(self):
        return f"PeerPort({self.id}): {self.portinfo}"


# class BGPSession(Base):
@grainy_model(namespace="peerses")
@reversion.register
class PeerSession(PolicyHolderMixin, Base):
    """
    preferences and policy for specific peer::ix::session

    Need to have this level over the PeerPort to account for single Network
    port going to a Peer with 2 physical ports (with different IPs)
    """

    port = models.ForeignKey(Port, on_delete=models.CASCADE, related_name="peerses_qs")
    peerport = models.ForeignKey(PeerPort, on_delete=models.CASCADE, related_name="+")

    class Meta:
        unique_together = ("port", "peerport")
        db_table = "peerctl_peerses"

    class HandleRef:
        tag = "peerses"

    @classmethod
    @reversion.create_revision()
    def get_or_create(cls, port, peerport, create_status="ok"):
        try:
            obj = cls.objects.get(port=port, peerport=peerport)

        except cls.DoesNotExist:
            obj = cls.objects.create(port=port, peerport=peerport, status=create_status)

        return obj

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
        devices = []
        for phyport in self.port.virtport.logport.phyport_qs.all():
            devices.append(phyport.device)
        return list(set(devices))

    @property
    def policy_parents(self):
        return [self.peerport.peernet, self.port]

    def __str__(self):
        return "Session ({}): AS{} -> AS{}".format(
            self.id, self.peerport.peernet.net.asn, self.peerport.peernet.peer.asn
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

        env = Environment(trim_blocks=True, loader=loader)

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

    class Meta:
        db_table = "peerctl_devicetmpl"

    class HandleRef:
        tag = "devicetmpl"

    @property
    def template_path(self):
        return const.DEVICE_TEMPLATES[self.type]

    @property
    def template_loader_paths(self):
        return [settings.NETOM_TEMPLATE_DIR] + super().template_loader_paths

    def get_data(self):
        data = super().get_data()
        ctx = self.context
        device = ctx.get("device")
        net = ctx.get("net")
        member = ctx.get("member")
        if member:
            member = [int(member)]

        data.update(**device.peer_groups_netom0_data(net, members=member))
        data["device"] = {"type": device.type}
        data["ports"] = [port for port in device.port_qs]

        return data


@reversion.register
@grainy_model(
    namespace=Network.Grainy.namespace(),
    namespace_instance="{namespace}.{instance.net.asn}.device.{instance.id}",
)
class EmailTemplate(Base, TemplateBase):
    type = models.CharField(max_length=255, choices=EMAIL_TEMPLATE_TYPES)

    class Meta:
        db_table = "peerctl_emltmpl"

    class HandleRef:
        tag = "emltmpl"

    def get_data(self):
        """
        Returns a dict containing all environment variables to
        be available during template rendering
        """
        data = super().get_data()

        ctx = self.context

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

        if "peer" in ctx:
            peer = ctx.get("peer")
            mutual_locations = []
            for ix_id in self.net.get_mutual_locations(peer.asn):
                ix_source, ix_id = ix_id.split(":")
                mutual_locations.append(
                    InternetExchange.get_or_create(int(ix_id), ix_source)
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

        if "sessions" in ctx:
            data.update(
                {
                    "sessions": [
                        {
                            "peer_ip4": session.peerport.portinfo.ipaddr4,
                            "peer_ip6": session.peerport.portinfo.ipaddr6,
                            "ip4": session.port.portinfo.ipaddr4,
                            "ip6": session.port.portinfo.ipaddr6,
                            "prefix_length4": session.port.portinfo.info_prefixes4,
                            "prefix_length6": session.port.portinfo.info_prefixes6,
                        }
                        for session in ctx.get("sessions")
                    ]
                }
            )
        else:
            data.update({"sessions": []})

        return data


# XXX dont need anymore (fullctl auditlog)
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
    def log_peerses(cls, event, peerses, user):
        peerport = peerses.peerport
        return cls.log(
            peerport.peernet.net,
            event=event,
            user=user,
            ix=peerses.port.portinfo.ix_name,
            ix_id=peerses.port.portinfo.ix.id,
            asn=peerport.peernet.peer.asn,
            net=peerport.peernet.peer.name,
            net_id=peerport.peernet.peer.id,
            ip4=f"{peerport.portinfo.ipaddr4}",
            ip6=f"{peerport.portinfo.ipaddr6}",
            status=peerses.status,
        )

    @classmethod
    def log_peerses_request(cls, peerses, user):
        return cls.log_peerses("peerses-request", peerses, user)

    @classmethod
    def log_peerses_add(cls, peerses, user):
        return cls.log_peerses("peerses-add", peerses, user)

    @classmethod
    def log_peerses_del(cls, peerses, user):
        return cls.log_peerses("peerses-del", peerses, user)

    @classmethod
    def log_peerses_mod(cls, peerses, user):
        return cls.log_peerses("peerses-mod", peerses, user)

    @classmethod
    def log_email(cls, emaillog):
        return cls.log(
            emaillog.net,
            "email",
            emaillog.user,
            emaillog=emaillog.id,
            subject=emaillog.subject,
            recipients=emaillog.recipients,
            recipient=emaillog.recipient,
            sender=emaillog.sender_address,
            path=emaillog.path,
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
        Network, related_name="qset_emaillog", on_delete=models.CASCADE
    )

    user = models.ForeignKey(get_user_model(), on_delete=models.PROTECT)
    sender_address = models.CharField(max_length=255)

    subject = models.CharField(max_length=255)

    body = models.TextField()

    origin = models.CharField(max_length=255, choices=const.EMAIL_ORIGIN)

    class HandleRef:
        tag = "emaillog"

    class Meta:
        db_table = "peerctl_emaillog"

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
                EmailLogRecipient.objects.create(emaillog=log, **recipient)

        AuditLog.log_email(log)

        return log

    @classmethod
    def log_peerses_workflow(cls, asn, peer_asn, user, contact, subject, body):
        net = Network.objects.get(asn=asn)
        return cls.log(
            net,
            user,
            subject,
            body,
            "peerses-workflow",
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
        return f"/admctl/django_peerctl/emaillog/{self.id}/change/"

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
    namespace_instance="{namespace}.{instance.emaillog.net.asn}",
)
class EmailLogRecipient(models.Model):

    emaillog = models.ForeignKey(
        EmailLog, related_name="qset_recipient", on_delete=models.CASCADE
    )

    email = models.CharField(max_length=255)
    asn = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "peerctl_emaillog_recipient"


@grainy_model(namespace="user")
@reversion.register
class UserPreferences(HandleRefModel):

    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    email_opt_features = models.BooleanField(default=True)
    email_opt_offers = models.BooleanField(default=True)

    class HandleRef:
        tag = "userpref"

    class Meta:
        db_table = "peerctl_userpref"

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
