import ipaddress

import fullctl.service_bridge.ixctl as ixctl
import fullctl.service_bridge.pdbctl as pdbctl
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from fullctl.django.models.concrete.tasks import TaskLimitError
from fullctl.django.rest.decorators import serializer_registry
from fullctl.django.rest.serializers import ModelSerializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError  # noqa

import django_peerctl.autopeer.tasks as autopeer_tasks
import django_peerctl.models as models
from django_peerctl.autopeer import autopeer_url
from django_peerctl.helpers import get_best_policy

Serializers, register = serializer_registry()


def is_dummy(name):
    if not name:
        return False

    return (
        name.startswith("pdb:")
        or name.startswith("ixctl:")
        or name.startswith("peerctl:")
    )


@register
class Network(ModelSerializer):
    name = serializers.SerializerMethodField()
    peer_contact_email = serializers.CharField(read_only=True)
    contacts = serializers.SerializerMethodField()

    prefix4_override = serializers.IntegerField(allow_null=True)
    prefix6_override = serializers.IntegerField(allow_null=True)

    class Meta:
        model = models.Network
        fields = [
            "id",
            "asn",
            "as_set",
            "as_set_source",
            "network_type",
            "prefix4",
            "prefix6",
            "traffic",
            "ratio",
            "scope",
            "multicast",
            "never_via_route_servers",
            "unicast",
            "name",
            "contacts",
            "peer_contact_email",
            "network_type_override",
            "prefix4_override",
            "prefix6_override",
            "as_set_override",
            "multicast_override",
            "never_via_route_servers_override",
            "ratio_override",
            "traffic_override",
            "unicast_override",
            "scope_override",
        ]
        read_only_fields = ("asn",)

    @models.ref_fallback(lambda s, o: f"AS{o.asn}")
    def get_name(self, instance):
        return instance.ref.name

    def get_contacts(self, instance):
        return instance.contacts


@register
class Policy(ModelSerializer):
    class Meta:
        model = models.Policy
        fields = [
            "id",
            "name",
            "import_policy",
            "export_policy",
            "localpref",
            "med",
            "is_global4",
            "is_global6",
            "peer_group",
            # XXX
            # "count_peers",
        ]


@register
class AvailablePort(serializers.Serializer):
    ref_tag = "available_port"
    id = serializers.IntegerField(source="pk", read_only=True)
    display_name = serializers.CharField(read_only=True)
    device = serializers.SerializerMethodField()

    device_id = serializers.IntegerField(help_text="list ports for this device")

    class Meta:
        fields = ["id", "display_name", "device"]

    def get_device(self, instance):
        return instance.devices[0].__dict__


@register
class Port(serializers.Serializer):
    ref_tag = "port"

    id = serializers.IntegerField(source="pk")

    net = serializers.IntegerField(read_only=True)
    asn = serializers.IntegerField(read_only=True)
    peers = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    ix = serializers.SerializerMethodField()
    ix_name = serializers.SerializerMethodField()
    ix_simple_name = serializers.SerializerMethodField()
    speed = serializers.SerializerMethodField()
    policy4 = serializers.SerializerMethodField()
    policy6 = serializers.SerializerMethodField()
    device = serializers.SerializerMethodField()
    mac_address = serializers.SerializerMethodField()
    is_route_server_peer = serializers.SerializerMethodField()
    md5 = serializers.SerializerMethodField()

    ref_ix_id = serializers.SerializerMethodField()
    ref_source = serializers.SerializerMethodField()
    ip4 = serializers.SerializerMethodField()
    ip6 = serializers.SerializerMethodField()
    mtu = serializers.SerializerMethodField()
    maxprefix4 = serializers.SerializerMethodField()
    maxprefix6 = serializers.SerializerMethodField()

    class Meta:
        fields = [
            "id",
            "ix",
            "ix_name",
            "ix_simple_name",
            "display_name",
            "net",
            "asn",
            "speed",
            "peers",
            "policy4",
            "policy6",
            "ip4",
            "ip6",
            "device",
            "ref_ix_id",
            "ref_source",
            "mac_address",
            "is_route_server_peer",
            "md5",
            "mtu",
            "maxprefix4",
            "maxprefix6",
        ]

    def get_ip4(self, instance):
        return instance.ip_address_4

    def get_ip6(self, instance):
        return instance.ip_address_6

    @models.ref_fallback(None)
    def get_mac_address(self, instance):
        if instance.mac_address:
            return f"{instance.mac_address}"
        return None

    @models.ref_fallback(False)
    def get_is_route_server_peer(self, instance):
        return instance.is_route_server_peer

    def get_peers(self, instance):
        return models.PeerSession.objects.filter(port=instance).count()

    @models.ref_fallback(0)
    def get_maxprefix4(self, instance):
        return instance.prefix4

    @models.ref_fallback(0)
    def get_maxprefix6(self, instance):
        return instance.prefix6

    @models.ref_fallback(0)
    def get_mtu(self, instance):
        return instance.mtu

    @models.ref_fallback("")
    def get_md5(self, instance):
        if not instance.is_route_server_peer:
            return ""

        if self.context.get("load_md5"):
            peer_net = instance.get_route_server_peer_net()
            if peer_net:
                return peer_net.md5

        return instance.port_info_object._ref.md5

    @models.ref_fallback(0)
    def get_ix(self, instance):
        return self.get_ix_object(instance).id

    @models.ref_fallback(None)
    def get_ix_object(self, instance):
        if not hasattr(self, "_ix_obj"):
            self._ix_obj = {}

        ref_id = instance.port_info_object.ref_ix_id

        if ref_id in self._ix_obj:
            return self._ix_obj[ref_id]

        self._ix_obj[ref_id] = models.InternetExchange.objects.get(
            ref_id=instance.port_info_object.ref_ix_id
        )

        return self._ix_obj[ref_id]

    @models.ref_fallback(None)
    def get_ref_ix_id(self, instance):
        return instance.port_info_object.ref_ix_id

    @models.ref_fallback("")
    def get_ref_source(self, instance):
        return self.get_ref_ix_id(instance).split(":")[0]

    @models.ref_fallback("")
    def get_ix_name(self, instance):
        self.get_device(instance)

        parts = []
        if instance.device and not is_dummy(instance.device.name):
            parts.append(instance.device.name)

        ix = self.get_ix_object(instance)

        if ix:
            parts.append(ix.name)
        else:
            parts.append(instance.display_name)

        parts.append(instance.ip_address_4)

        if instance.virtual_port_name and not is_dummy(instance.virtual_port_name):
            parts.append(instance.virtual_port_name)

        return " ".join([str(p) for p in parts])

    def get_ix_simple_name(self, instance):
        ix = self.get_ix_object(instance)

        if ix:
            return ix.name
        return ""

    def get_display_name(self, instance):
        if instance.virtual_port_name and not is_dummy(instance.virtual_port_name):
            return f"{instance.virtual_port_name}: {instance.display_name}"
        return instance.display_name

    @models.ref_fallback(0)
    def get_speed(self, instance):
        return instance.port_info_object.ref.speed

    def get_device(self, instance):
        if getattr(instance, "device", None):
            return instance.device.__dict__
        return instance.devices[0].__dict__

    def get_policy(self, instance, version):
        policy = get_best_policy(instance, version, raise_error=False)
        if policy:
            return {
                "id": policy.id,
                "inherited": getattr(instance, f"policy{version}_inherited"),
                "name": policy.name,
            }
        return {}

    def get_policy4(self, instance):
        return self.get_policy(instance, 4)

    def get_policy6(self, instance):
        return self.get_policy(instance, 6)


@register
class PortUpdate(serializers.Serializer):

    """
    Allows updating of certain fields on a port or related
    to a port

    - prefix limits
    - mac address
    - route server md5
    """

    maxprefix4 = serializers.IntegerField(required=False)
    maxprefix6 = serializers.IntegerField(required=False)
    md5 = serializers.CharField(required=False, allow_blank=True)
    mac_address = serializers.CharField(required=False, allow_blank=True)
    is_route_server_peer = serializers.BooleanField(required=False)

    ref_tag = "port_update"

    class Meta:
        fields = [
            "maxprefix4",
            "maxprefix6",
            "md5",
            "mac_address",
            "is_route_server_peer",
        ]

    def save(self):
        # port will be a models.PortObject instance
        port = self.context.get("port")

        if not port:
            raise KeyError("No `port` object set in serializer context")

        prefix4 = self.validated_data.get("maxprefix4")
        prefix6 = self.validated_data.get("maxprefix6")
        md5 = self.validated_data.get("md5")
        mac_address = self.validated_data.get("mac_address")
        is_route_server_peer = self.validated_data.get("is_route_server_peer")

        # set mac address
        port.set_mac_address(mac_address)

        # set md5
        port.set_route_server_md5(md5)

        # override prefix limits
        net = port.port_info_object.net
        net.prefix4_override = prefix4
        net.prefix6_override = prefix6
        net.save()

        # override is_route_server_peer
        port.port_info_object.set_is_route_server_peer(is_route_server_peer)


@register
class Peer(serializers.Serializer):
    scope = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    policy_ratio = serializers.SerializerMethodField()
    policy_general = serializers.SerializerMethodField()
    policy_contracts = serializers.SerializerMethodField()
    policy_locations = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    asn = serializers.IntegerField()
    peeringdb = serializers.SerializerMethodField()
    peer_session = serializers.SerializerMethodField()
    peer_session_status = serializers.SerializerMethodField()
    peer_session_contact = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    md5 = serializers.SerializerMethodField()
    ix_name = serializers.SerializerMethodField()
    port_id = serializers.SerializerMethodField()
    device_id = serializers.SerializerMethodField()
    info_prefixes4 = serializers.SerializerMethodField()
    info_prefixes6 = serializers.SerializerMethodField()
    ipaddr = serializers.SerializerMethodField()
    is_rs_peer = serializers.BooleanField()
    ref_id = serializers.CharField()
    ref_tag = "peer"
    id = serializers.CharField(source="ref_id")

    class Meta:
        fields = [
            "id",
            "name",
            "status",
            "asn",
            "scope",
            "type",
            "info_prefixes4",
            "info_prefixes6",
            "peeringdb",
            "peer_session",
            "peer_session_status",
            "peer_session_contact",
            "user",
            "policy_general",
            "policy_ratio",
            "policy_contracts",
            "policy_locations",
            "is_rs_peer",
            "md5",
            "ix_name",
            "port_id",
            "ipaddr",
            "ref_id",
            "device_id",
        ]

    @property
    def port(self):
        return self.context.get("port")

    @property
    def pocs(self):
        """
        Build and cache a queryset of network contacts
        to use to retrieve contact points for peer session
        requests.
        """

        if not hasattr(self, "_pocs"):
            if not isinstance(self.instance, list):
                peers = [self.instance]
            else:
                peers = self.instance

            self._pocs = [
                poc
                for poc in pdbctl.NetworkContact().objects(
                    asns=[i.asn for i in peers], require_email=True, role="policy"
                )
            ]

        return self._pocs

    @property
    def peer_nets(self):
        """
        Returns all peer networks at the port specified in
        the serializer context

        Will be cached in order to speed up serialization
        times
        """
        if not hasattr(self, "_peer_nets"):
            self._peer_nets = {}
            ix = self.context["port"].port_info_object.ix
            if ix:
                _peer_nets = self.context["net"].peer_nets_at_ix(ix.id)
                for peer_net in _peer_nets:
                    self._peer_nets[peer_net.peer.asn] = peer_net
        return self._peer_nets

    def get_scope(self, obj):
        if hasattr(obj, "net") and obj.net is not None:
            return obj.net.info_scope
        return None

    def get_type(self, obj):
        if hasattr(obj, "net") and obj.net is not None:
            return obj.net.info_type
        return None

    def get_policy_ratio(self, obj):
        if hasattr(obj, "net") and obj.net is not None:
            return obj.net.policy_ratio
        return None

    def get_policy_general(self, obj):
        if hasattr(obj, "net") and obj.net is not None:
            return obj.net.policy_general
        return None

    def get_policy_contracts(self, obj):
        if hasattr(obj, "net") and obj.net is not None:
            return obj.net.policy_contracts
        return None

    def get_policy_locations(self, obj):
        if hasattr(obj, "net") and obj.net is not None:
            return obj.net.policy_locations
        return None

    def get_name(self, obj):
        return obj.name

    def get_peeringdb(self, obj):
        return f"https://www.peeringdb.com/asn/{obj.asn}"

    def get_ipaddr(self, obj):
        result = []

        if not isinstance(self.instance, list):
            qset = models.PortInfo.ref_bridge(obj.source).objects(
                ix=obj.ix_id, asn=obj.asn
            )
        else:
            qset = self.instance

        for member in qset:
            if member.asn != obj.asn:
                continue
            if self.context.get("ipaddr", "all") != "all":
                if member.id != obj.id:
                    continue

            peer_session = self.get_peer_session(member)
            result.append(
                {
                    "ipaddr4": str(member.ipaddr4),
                    "ipaddr6": str(member.ipaddr6),
                    "policy4": self.get_policy(member, 4),
                    "policy6": self.get_policy(member, 6),
                    "peer_session": peer_session,
                    "peer_session_status": self.get_peer_session_status(member),
                    "origin_id": obj.ref_id,
                    "id": member.ref_id,
                }
            )

        return result

    def get_policy(self, obj, version):
        peer_session = getattr(obj, "peer_session", None)
        if peer_session and peer_session.status == "ok":
            policy = get_best_policy(obj.peer_session, version, raise_error=False)
            if policy:
                return {
                    "id": policy.id,
                    "name": policy.name,
                    "inherited": getattr(
                        obj.peer_session, f"policy{version}_inherited"
                    ),
                }
        return {}

    def get_policy4(self, obj):
        return self.get_policy(obj, 4)

    def get_policy6(self, obj):
        return self.get_policy(obj, 6)

    def get_peer_session(self, obj):
        if getattr(obj, "peer_session", None):
            return obj.peer_session.id
        peer_session = self.port.get_peer_session(obj)

        # cache peer_session on obj, so we can re-use during `get_user`
        # `get_peer_session_status`
        obj.peer_session = peer_session
        if peer_session:
            return peer_session.id
        return 0

    def get_peer_session_contact(self, obj):
        for poc in self.pocs:
            if poc.asn == obj.asn:
                return poc.email
        return None

    def get_peer_session_status(self, obj):
        peer_session = getattr(obj, "peer_session", None)
        if peer_session:
            return peer_session.status
        return None

    def get_md5(self, obj):
        peer_net = self.peer_nets.get(obj.asn)
        if peer_net:
            return peer_net.md5
        return ""

    def get_user(self, obj):
        peer_session = getattr(obj, "peer_session", None)
        if peer_session:
            user = peer_session.user
            if user:
                return user.username
        return None

    def get_ix_name(self, obj):
        return self.context["port"].port_info_object.ix_name

    def get_port_id(self, obj):
        return self.context["port"].pk

    def get_device_id(self, obj):
        if "device" not in self.context:
            self.context["device"] = self.context["port"].devices[0]
        return self.context["device"].id

    @models.ref_fallback(0)
    def get_info_prefixes4(self, obj):
        peer_net = self.peer_nets.get(obj.asn)
        if peer_net and peer_net.info_prefixes4 is not None:
            return peer_net.info_prefixes4
        return obj.net.info_prefixes4

    @models.ref_fallback(0)
    def get_info_prefixes6(self, obj):
        peer_net = self.peer_nets.get(obj.asn)
        if peer_net and peer_net.info_prefixes6 is not None:
            return peer_net.info_prefixes6
        return obj.net.info_prefixes6


@register
class PeerDetails(serializers.Serializer):
    mutual_locations = serializers.SerializerMethodField()

    ref_tag = "peerdetail"

    class Meta:
        fields = [
            "id",
            "mutual_locations",
        ]

    def get_mutual_locations(self, obj):
        net = self.context.get("net")
        my_port = self.context.get("port")
        mutual_locs = []
        exclude = [my_port.port_info_object.ref_ix_id]

        for ix_id, result in net.get_mutual_locations(obj.asn, exclude=exclude).items():
            port = models.PortInfo.objects.get(
                ref_id=result[net.asn][0].ref_id
            ).port.object

            # port = models.Port.get_or_create(result[net.asn][0])
            if port.id == my_port.id:
                continue

            port_data = Port(instance=port).data

            for asn, members in result.items():
                if asn == net.asn:
                    continue
                for member in members:
                    peer = Peer(
                        instance=member,
                        context={"port": port, "net": net, "ipaddr": "single"},
                    ).data
                    peer["port"] = port_data
                    mutual_locs.append(peer)

        return mutual_locs


class PeerSessionMeta(serializers.Serializer):
    # TODO: pydantic model

    last_updown = serializers.IntegerField(required=False, allow_null=True)
    session_state = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    active = serializers.IntegerField(required=False, allow_null=True)
    received = serializers.IntegerField(required=False, allow_null=True)
    accepted = serializers.IntegerField(required=False, allow_null=True)
    damped = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        fields = [
            "last_updown",
            "session_state",
            "active",
            "received",
            "accepted",
            "damped",
        ]


class SoftModelReferenceField(serializers.IntegerField):
    """
    Super fancy serializer field that can handle both integer and model instance
    since PrimaryKeyRelatedField does not work outside of ModelSerializers (apparently)
    """

    def to_representation(self, value):
        if hasattr(value, "id"):
            return value.id


@register
class UpdatePeerSession(serializers.Serializer):
    id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=_(
            "Peer session id, if specified, this session will be updated, regardless of any other fields specified"
        ),
    )

    peer_asn = serializers.IntegerField(help_text=_("ASN of the peer"))
    peer_ip4 = serializers.CharField(
        help_text=_("Peer IPv4 address"),
        allow_null=True,
        allow_blank=True,
        required=False,
    )
    peer_ip6 = serializers.CharField(
        allow_null=True,
        allow_blank=True,
        required=False,
        help_text=_("Peer IPv6 address"),
    )
    peer_interface = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text=_("Interface name of the peer port"),
    )
    peer_session_type = serializers.CharField(
        allow_null=True, allow_blank=True, required=False
    )
    policy4 = SoftModelReferenceField(
        required=False,
        allow_null=True,
        help_text=_(
            "IPv4 Policy - session will use this peering policy, should be policy id"
        ),
    )
    policy6 = SoftModelReferenceField(
        required=False,
        allow_null=True,
        help_text=_(
            "IPv6 Policy - session will use this peering policy, should be policy id"
        ),
    )
    peer_maxprefix4 = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=_(
            "Number of IPv4 prefixes - if not specified, value will be pulled from PeeringDB if network exists"
        ),
    )
    peer_maxprefix6 = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=_(
            "Number of IPv6 prefixes - if not specified, value will be pulled from PeeringDB if network exists"
        ),
    )
    md5 = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text=_("Session MD5 password"),
    )
    port = serializers.CharField(
        help_text=_("deviceCtl Port reference id or IP address"),
        required=False,
        allow_null=True,
    )
    device = serializers.CharField(
        help_text=_("deviceCtl Device reference id"),
        required=False,
        allow_null=True,
    )

    meta4 = PeerSessionMeta(required=False, allow_null=True)
    meta6 = PeerSessionMeta(required=False, allow_null=True)

    ref_tag = "update_peer_session"

    class Meta:
        fields = [
            "id",
            "policy4",
            "policy6",
            "md5",
            "peer_asn",
            "peer_ip4",
            "peer_ip6",
            "peer_interface",
            "peer_maxprefix4",
            "peer_maxprefix6",
            "peer_session_type",
            "port",
            "device",
        ]

    def validate_peer_maxprefix4(self, value):
        if value < 0:
            raise serializers.ValidationError("Cannot be negative")
        return value

    def validate_peer_maxprefix6(self, value):
        if value < 0:
            raise serializers.ValidationError("Cannot be negative")
        return value

    def validate(self, data):
        port = data.get("port")
        ip = None
        asn = self.context.get("asn")
        net = models.Network.objects.get(asn=asn)

        peer_ip4 = data.get("peer_ip4")
        peer_ip6 = data.get("peer_ip6")

        # make sure either peer_ip4 or peer_ip6 is specified

        if not peer_ip4 and not peer_ip6:
            raise serializers.ValidationError(
                "Must specify either peer_ip4 or peer_ip6"
            )

        try:
            ip = ipaddress.ip_address(port)
        except ValueError:
            try:
                port = int(port)
            except (ValueError, TypeError):
                data["port"] = port = None

        if ip:
            # no port specified, find by ip
            port = models.Port().first(org_slug=net.org.slug, ip=str(ip))
            if not port:
                # TODO: create dummy port?
                raise serializers.ValidationError(f"Could not find port by IP: {ip}")

            data["port"] = port.id

        if not data.get("port") and not data.get("device"):
            raise serializers.ValidationError("Must provide port or device")

        if not data.get("device"):
            port = models.Port().first(id=data["port"], org_slug=net.org.slug)
            data["device"] = port.device_id

        # if updating session and port is not specified, use the port from the session

        if (
            self.instance
            and data.get("port") is None
            and self.instance.port
            and data.get("device")
        ):
            if self.instance.port.object.device_id == int(data.get("device")):
                data["port"] = int(self.instance.port)

        # validate policies exist

        if data.get("policy4"):
            try:
                models.Policy.objects.get(id=data["policy4"], net=net)
            except models.Policy.DoesNotExist:
                raise serializers.ValidationError({"policy4": "Invalid policy4"})

        if data.get("policy6"):
            try:
                models.Policy.objects.get(id=data["policy6"], net=net)
            except models.Policy.DoesNotExist:
                raise serializers.ValidationError({"policy6": "Invalid policy6"})

        return data

    def ensure_peer_portinfo(self, net, peer_ip4, peer_ip6, port=None, port_info=None):
        """
        Ensures that a PortInfo object exists for the peer_ip4 and peer_ip6
        ip addresses. If the PortInfo object does not exist, it will be created.

        Arguments:

            net (models.Network): Network object - network that owns the session
            peer_ip4 (str): IPv4 address of the peer
            peer_ip6 (str): IPv6 address of the peer
            port (models.Port): Port object - port that the session runs on (this is NOT the peer side port)
            port_info (models.PortInfo): PortInfo object - port info for the peer side port
        """

        if peer_ip4:
            peer_ip4 = ipaddress.ip_interface(peer_ip4)

        if peer_ip6:
            peer_ip6 = ipaddress.ip_interface(peer_ip6)

        # if port is specified we can use its ip addresses to determine
        # the prefix length for the peer ip addresses (which may or may not
        # ne specified in peer_ip4 and peer_ip6 at this point)

        port_ip4 = None
        port_ip6 = None

        filters = []

        if port:
            if not isinstance(port, models.PortObject):
                port = models.Port().object(port)

            if peer_ip4 and port.ip_address_4:
                port_ip4 = ipaddress.ip_interface(port.ip_address_4)
                peer_ip4 = ipaddress.ip_interface(
                    f"{peer_ip4.ip}/{port_ip4.network.prefixlen}"
                )

            if peer_ip6 and port.ip_address_6:
                port_ip6 = ipaddress.ip_interface(port.ip_address_6)
                peer_ip6 = ipaddress.ip_interface(
                    f"{peer_ip6.ip}/{port_ip6.network.prefixlen}"
                )

        # filter arguments for PortInfo object

        if not port_info:
            if peer_ip4 and peer_ip6:
                filters.append(
                    Q(ip_address_4__host=peer_ip4.ip)
                    | Q(ip_address_6__host=peer_ip6.ip)
                )
            elif peer_ip4:
                filters.append(Q(ip_address_4__host=peer_ip4.ip))
            elif peer_ip6:
                filters.append(Q(ip_address_6__host=peer_ip6.ip))

            port_info = models.PortInfo.objects.filter(
                port=0,
                net=net,
                *filters,
            ).first()

        if not port_info:
            port_info = models.PortInfo.objects.create(
                port=0,
                net=net,
                ip_address_4=peer_ip4,
                ip_address_6=peer_ip6,
            )
        else:
            port_info.ip_address_4 = peer_ip4 or port_info.ip_address_4
            port_info.ip_address_6 = peer_ip6 or port_info.ip_address_6
            port_info.save()

        return port_info

    def save(self):
        if self.instance and self.instance.id:
            return self.update()
        return self.create()

    def create(self):
        data = self.validated_data
        asn = self.context.get("asn")

        net = models.Network.objects.get(asn=asn)

        peer = models.Network.get_or_create(asn=data["peer_asn"], org=None)

        peer_net = models.PeerNetwork.get_or_create(net, peer)

        old_md5 = peer_net.md5

        device = data.get("device")

        if "md5" in data:
            peer_net.md5 = data["md5"]

        if "peer_maxprefix4" in data:
            peer_net.info_prefixes4 = data["peer_maxprefix4"]

        if "peer_maxprefix6" in data:
            peer_net.info_prefixes6 = data["peer_maxprefix6"]

        peer_net.save()

        if old_md5 != peer_net.md5:
            peer_net.sync_route_server_md5()

        # handle port assignment

        port = data.get("port")
        device_id = data.get("device")

        if port and not isinstance(port, models.PortObject):
            port = models.Port().first(id=port)

        if port and not port.port_info_object:
            port_info = models.PortInfo.objects.create(port=port.id, net=net)
            port._port_info = port_info

        # find port based on peer subnet and device

        if not port and device_id:
            candidate_ports = models.Port.in_same_subnet(
                net.org, device_id, data.get("peer_ip4") or data.get("peer_ip6")
            )
            if candidate_ports:
                # TODO: what happens if more than one suitable port is returned? does that
                # ever happen in the real world? For now just pick the first.
                port = candidate_ports[0]

        if not port and not device_id:
            raise serializers.ValidationError("Must provide port or device")

        # sanity check for device and port

        if port and port.device_id and device and int(port.device_id) != int(device):
            # TODO port can be multiple devices through logical port
            raise serializers.ValidationError(
                "The device you provided does not match the device for the port specifierd"
            )

        if port:
            port_id = port.id
        else:
            port_id = None

        # create / update peer port and peer port portinfo

        peer_port_info = self.ensure_peer_portinfo(
            net, data.get("peer_ip4"), data.get("peer_ip6"), port
        )

        peer_port = models.PeerPort.objects.filter(
            port_info=peer_port_info, peer_net=peer_net
        ).first()
        if not peer_port:
            peer_port = models.PeerPort.objects.create(
                port_info=peer_port_info, peer_net=peer_net
            )

        if "peer_interface" in data:
            peer_port.interface_name = data["peer_interface"]

        peer_port.save()

        # determine default peer session type

        if peer_net.peer.asn == net.asn:
            default_peer_session_type = "core"
        elif port and port.is_ixi:
            default_peer_session_type = "peer"
        else:
            default_peer_session_type = "transit"

        if not data.get("peer_session_type"):
            data["peer_session_type"] = default_peer_session_type

        return models.PeerSession.objects.create(
            port=port_id,
            device=device_id,
            peer_port=peer_port,
            policy4_id=data.get("policy4") or None,
            policy6_id=data.get("policy6") or None,
            status="ok",
            peer_session_type=data.get("peer_session_type"),
            meta4=data.get("meta4") or None,
            meta6=data.get("meta6") or None,
        )

    def update(self):
        session = self.instance
        data = self.validated_data
        asn = self.context.get("asn")

        net = models.Network.objects.get(asn=asn)
        peer = models.Network.get_or_create(asn=data["peer_asn"], org=None)

        peer_net = models.PeerNetwork.get_or_create(net, peer)

        old_md5 = peer_net.md5

        if "md5" in data:
            peer_net.md5 = data["md5"]

        if "peer_maxprefix4" in data:
            peer_net.info_prefixes4 = data["peer_maxprefix4"]

        if "peer_maxprefix6" in data:
            peer_net.info_prefixes6 = data["peer_maxprefix6"]

        peer_net.save()

        if old_md5 != peer_net.md5 and session.port:
            peer_net.sync_route_server_md5()

        peer_port_info = self.ensure_peer_portinfo(
            net,
            data.get("peer_ip4"),
            data.get("peer_ip6"),
            data.get("port"),
            session.peer_port.port_info,
        )

        session.peer_port.peer_net = peer_net
        session.peer_port.port_info = peer_port_info

        if "peer_interface" in data:
            session.peer_port.interface_name = data["peer_interface"]

        session.peer_port.save()

        if "port" in data:
            session.port = data["port"]

        if "policy4" in data:
            session.policy4_id = data["policy4"]

        if "policy6" in data:
            session.policy6_id = data["policy6"]

        if "peer_session_type" in data:
            session.peer_session_type = data["peer_session_type"]

        if "meta4" in data:
            session.meta4 = data.get("meta4") or None

        if "meta6" in data:
            session.meta6 = data.get("meta6") or None

        if session.port and not session.port.object.port_info_object:
            port_info = models.PortInfo.objects.create(
                port=session.port.object.id, net=net
            )
            session.port.object._port_info = port_info

        session.status = "ok"
        session.save()

        return session


@register
class CreatePartialPeerSession(UpdatePeerSession):
    """DEPRECATED"""

    port = serializers.IntegerField(
        required=False, help_text=_("deviceCtl Port reference")
    )
    ref_tag = "create_partial_peer_session"


@register
class UpdatePartialPeerSession(UpdatePeerSession):
    """DEPRECATED"""

    port = serializers.IntegerField(
        required=False, help_text=_("deviceCtl Port reference")
    )
    ref_tag = "update_partial_peer_session"


@register
class UpdatePeerSessionMeta(ModelSerializer):

    """
    This serializer is used to update session meta data
    """

    meta4 = PeerSessionMeta(required=False, allow_null=True)
    meta6 = PeerSessionMeta(required=False, allow_null=True)

    ref_tag = "update_peer_session_meta"

    class Meta:
        model = models.PeerSession
        fields = ["meta4", "meta6"]


@register
class PeerSession(ModelSerializer):
    policy4_id = serializers.SerializerMethodField()
    policy4_name = serializers.SerializerMethodField()
    policy4_inherited = serializers.SerializerMethodField()
    policy4_peer_group = serializers.SerializerMethodField()
    policy4_import = serializers.SerializerMethodField()
    policy4_export = serializers.SerializerMethodField()

    policy6_id = serializers.SerializerMethodField()
    policy6_name = serializers.SerializerMethodField()
    policy6_inherited = serializers.SerializerMethodField()
    policy6_peer_group = serializers.SerializerMethodField()
    policy6_import = serializers.SerializerMethodField()
    policy6_export = serializers.SerializerMethodField()

    peer_id = serializers.PrimaryKeyRelatedField(
        source="peer_port", queryset=models.PeerPort.objects.all()
    )
    peer_asn = serializers.SerializerMethodField()
    peer_name = serializers.SerializerMethodField()
    peer_type = serializers.SerializerMethodField()
    peer_interface = serializers.SerializerMethodField()
    peer_maxprefix4 = serializers.SerializerMethodField()
    peer_maxprefix6 = serializers.SerializerMethodField()

    device_name = serializers.SerializerMethodField()
    device_id = serializers.SerializerMethodField()
    facility_slug = serializers.SerializerMethodField()

    port_id = serializers.IntegerField(source="port")
    port_display_name = serializers.SerializerMethodField()
    port_interface = serializers.SerializerMethodField()
    port_is_ix = serializers.SerializerMethodField()

    meta4 = serializers.SerializerMethodField()
    meta6 = serializers.SerializerMethodField()

    md5 = serializers.SerializerMethodField()

    status = serializers.SerializerMethodField()

    ref_tag = "peer_session"

    class Meta:
        model = models.PeerSession
        fields = [
            "id",
            "port_id",
            "port_interface",
            "port_display_name",
            "port_is_ix",
            "ip4",
            "ip6",
            "md5",
            "peer_id",
            "peer_asn",
            "peer_interface",
            "peer_ip4",
            "peer_ip6",
            "peer_is_managed",
            "peer_maxprefix4",
            "peer_maxprefix6",
            "peer_name",
            "peer_type",
            "peer_session_type",
            "policy4_id",
            "policy4_name",
            "policy4_inherited",
            "policy4_import",
            "policy4_export",
            "policy4_peer_group",
            "policy6_id",
            "policy6_name",
            "policy6_inherited",
            "policy6_import",
            "policy6_export",
            "policy6_peer_group",
            "device_name",
            "device_id",
            "facility_slug",
            "meta4",
            "meta6",
            "status",
        ]

    def get_meta4(self, obj):
        # TODO: fill in defaults?
        return obj.meta4

    def get_meta6(self, obj):
        # TODO: full in defaults?
        return obj.meta6

    def get_status(self, obj):
        """
        returns peer-session, but will return `partial` if minimum amount
        of information is missing
        """

        # if the session status is anything but `ok` we can just return
        # as is

        if obj.status != "ok":
            return obj.status

        # neither ipv4 nor ipv6 policy is set, partial config

        if not self.get_policy4_id(obj) and not self.get_policy6_id(obj):
            return "partial"

        # no peer type is specified, partial config

        if not self.get_peer_type(obj):
            return "partial"

        # neither peer ipv4 nor peer ipv6 address is set, partial config

        if not obj.peer_ip4 and not obj.peer_ip6:
            return "partial"

        # peer asn not specified, partial config

        if not self.get_peer_asn(obj):
            return "partial"

        # device and port not specified, partial config

        if not self.get_device_id(obj):
            return "partial"

        return "ok"

    def get_policy(self, obj, version):
        if obj and obj.status in ["ok"]:
            if hasattr(obj, f"_policy{version}"):
                policy = getattr(obj, f"_policy{version}")
            else:
                policy = get_best_policy(obj, version, raise_error=False)
                setattr(obj, f"_policy{version}", policy)
            if policy:
                return {
                    "id": policy.id,
                    "name": policy.name,
                    "import_policy": policy.import_policy,
                    "export_policy": policy.export_policy,
                    "peer_group": policy.peer_group,
                    "inherited": getattr(obj, f"policy{version}_inherited"),
                }
        return {}

    def get_policy4_id(self, obj):
        return self.get_policy(obj, 4).get("id", None)

    def get_policy4_name(self, obj):
        return self.get_policy(obj, 4).get("name", None)

    def get_policy4_inherited(self, obj):
        return self.get_policy(obj, 4).get("inherited", None)

    def get_policy4_import(self, obj):
        return self.get_policy(obj, 4).get("import_policy", None)

    def get_policy4_export(self, obj):
        return self.get_policy(obj, 4).get("export_policy", None)

    def get_policy4_peer_group(self, obj):
        return self.get_policy(obj, 4).get("peer_group", None)

    def get_policy6_id(self, obj):
        return self.get_policy(obj, 6).get("id", None)

    def get_policy6_name(self, obj):
        return self.get_policy(obj, 6).get("name", None)

    def get_policy6_inherited(self, obj):
        return self.get_policy(obj, 6).get("inherited", None)

    def get_policy6_import(self, obj):
        return self.get_policy(obj, 6).get("import_policy", None)

    def get_policy6_export(self, obj):
        return self.get_policy(obj, 6).get("export_policy", None)

    def get_policy6_peer_group(self, obj):
        return self.get_policy(obj, 6).get("peer_group", None)

    def get_md5(self, obj):
        return obj.peer_port.peer_net.md5

    def get_peer_type(self, obj):
        return "external"

    def get_peer_name(self, obj):
        return obj.peer_port.peer_net.peer.name

    def get_peer_asn(self, obj):
        return obj.peer_port.peer_net.peer.asn

    def get_peer_interface(self, obj):
        if obj.peer_is_managed:
            # TODO this currently returns the port name, but needs
            # to actually return the physical port name
            return obj.peer_port.port_info.port.object.name

        return obj.peer_port.interface_name

    def get_peer_maxprefix4(self, obj):
        return obj.peer_port.peer_net.info_prefixes(4)

    def get_peer_maxprefix6(self, obj):
        return obj.peer_port.peer_net.info_prefixes(6)

    def get_device_name(self, obj):
        if (not obj.port or not obj.port.object) and not obj.device:
            return None

        return obj.devices[0].display_name

    def get_device_id(self, obj):
        if (not obj.port or not obj.port.object) and not obj.device:
            return None

        return obj.devices[0].id

    def get_facility_slug(self, obj):
        if not obj.port or not obj.port.object:
            return None

        return obj.devices[0].facility_slug

    def get_port_is_ix(self, obj):
        if not obj.port or not obj.port.object:
            return False

        ix_id = obj.port.object.port_info_object.ref_ix_id
        return ix_id is not None and ix_id != 0

    def get_port_interface(self, obj):
        if obj.port and obj.port.object:
            return obj.port.object.virtual_port_name
        return None

    def get_port_display_name(self, obj):
        if not obj.port or not obj.port.object:
            return "No port assigned"

        parts = []

        if obj.port.object.port_info_object.ix_name:
            parts += [obj.port.object.port_info_object.ix_name]

        if obj.port.object.virtual_port_name:
            parts += [obj.port.object.virtual_port_name]

        if obj.port.object.port_info_object.ipaddr4:
            parts += [str(obj.port.object.port_info_object.ipaddr4)]

        return " ".join(parts)


@register
class TemplatePreview(serializers.Serializer):

    """
    This serializer can be used to preview templates

    It needs to be instantiated with a TemplateBase
    object
    """

    body = serializers.SerializerMethodField()
    ref_tag = "tmplpreview"

    class Meta:
        fields = ["body"]

    def get_body(self, obj):
        try:
            return obj.render()
        except Exception as exc:
            return (
                "!!! ERROR !!!\nWhen trying to render the template "
                "we encountered the following issue:\n\n{}\n\nPlease fix and try again.".format(
                    exc
                )
            )


@register
class DeviceTemplate(ModelSerializer):
    class Meta:
        model = models.DeviceTemplate
        fields = ["id", "name", "type", "body", "default"]


@register
class DeviceTemplateList(serializers.Serializer):
    id = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    ref_tag = "devicelist"

    class Meta:
        fields = ["id", "name", "type"]

    def get_type(self, obj):
        if isinstance(obj, dict):
            return obj.get("type", obj.get("id"))
        return obj.type

    def get_id(self, obj):
        if isinstance(obj, dict):
            return obj["id"]
        return obj.id

    def get_name(self, obj):
        if isinstance(obj, dict):
            return obj["name"]
        return obj.name


@register
class EmailTemplate(ModelSerializer):
    class Meta:
        model = models.EmailTemplate
        fields = ["id", "name", "type", "body", "default"]


@register
class UserPreferences(ModelSerializer):
    class Meta:
        model = models.UserPreferences
        fields = ["id", "email_opt_features", "email_opt_offers"]


@register
class NetworkLocation(serializers.Serializer):
    ix_id = serializers.CharField()
    ix_name = serializers.CharField()
    session = serializers.BooleanField(required=False)

    ref_tag = "network_location"

    class Meta:
        fields = ["ix_id", "ix_name", "session"]


@register
class NetworkSearch(serializers.Serializer):
    asn = serializers.IntegerField()
    name = serializers.CharField()
    peer_session_contact = serializers.CharField()

    mutual_locations = NetworkLocation(many=True)
    their_locations = NetworkLocation(many=True)
    our_locations = NetworkLocation(many=True)

    ref_tag = "network_search"

    class Meta:
        fields = [
            "asn",
            "name",
            "peer_session_contact",
            "mutual_locations",
            "their_locations",
            "our_locations",
        ]


@register
class PeeringDBRelationship(serializers.Serializer):

    """
    Renders a relationship to a PeeringDB object
    """

    remote_ref_tag = serializers.SerializerMethodField()
    name = serializers.CharField()
    id = serializers.IntegerField()
    org_id = serializers.IntegerField()
    url = serializers.SerializerMethodField()

    ref_tag = "peeringdb_relationship"

    class Meta:
        fields = [
            "remote_ref_tag",
            "name",
            "id",
            "org_id",
        ]

    def get_remote_ref_tag(self, obj):
        return obj.ref_tag

    def get_url(self, obj):
        return f"https://www.peeringdb.com/{obj.ref_tag}/{obj.id}"


@register
class AutopeerRequest(serializers.Serializer):
    """
    Initiates an autopeering request
    """

    asn = serializers.IntegerField()
    date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    location = serializers.SerializerMethodField()
    id = serializers.IntegerField(read_only=True)
    num_locations = serializers.IntegerField(read_only=True)
    peer_id = serializers.CharField(read_only=True)
    port_id = serializers.IntegerField(read_only=True, allow_null=True)

    ref_tag = "autopeer"

    class Meta:
        fields = [
            "id",
            "asn",
            "status",
            "location",
            "type",
            "date",
            "peer_id",
            "port_id",
        ]

    @classmethod
    def get_requests(cls, net):
        _requests = list(
            models.PeerRequest.objects.filter(net=net)
            .prefetch_related("locations")
            .order_by("-created")
        )
        ixctl_ix_ids = []
        pdbctl_ix_ids = []
        locations = []

        for req in _requests:
            for location in req.locations.all():
                if location.pdb_ix_id:
                    pdbctl_ix_ids.append(location.pdb_ix_id)
                elif location.ixctl_ix_id:
                    ixctl_ix_ids.append(location.ixctl_ix_id)

        if pdbctl_ix_ids:
            pdbctl_exchanges = {
                ix.id: ix for ix in pdbctl.InternetExchange().objects(ids=pdbctl_ix_ids)
            }

        if ixctl_ix_ids:
            ixctl_exchanges = {
                ix.id: ix for ix in ixctl.InternetExchange().objects(ids=ixctl_ix_ids)
            }

        for req in _requests:
            req_locations = list(req.locations.all())
            num_locations = len(req_locations)

            if not num_locations:
                locations.append(
                    {
                        "id": req.id,
                        "asn": req.peer_asn,
                        "location": "...",
                        "status": req.status,
                        "date": req.created,
                        "type": req.type,
                        "num_locations": 0,
                        "peer_id": None,
                        "port_id": None,
                    }
                )

            for location in req_locations:
                ix = None
                if location.pdb_ix_id:
                    ix = pdbctl_exchanges.get(location.pdb_ix_id)
                elif location.ixctl_ix_id:
                    ix = ixctl_exchanges.get(location.ixctl_ix_id)

                if ix:
                    location._name = ix.name
                else:
                    location._name = "Unknown"

                if location.port:
                    port = int(location.port)
                else:
                    port = None

                locations.append(
                    {
                        "id": req.id,
                        "asn": req.peer_asn,
                        "location": location.name,
                        "status": location.status,
                        "date": req.created,
                        "type": req.type,
                        "num_locations": num_locations,
                        "peer_id": location.peer_id,
                        "port_id": port,
                    }
                )

        return locations

    def get_location(self, obj):
        return obj.get("location", [])

    def validate(self, data):
        asn = data["asn"]

        if not autopeer_url(asn):
            raise serializers.ValidationError(
                "This ASN is not enabled for autopeering."
            )

        return data

    def save(self):
        try:
            net = self.context.get("net")
            asn = net.asn
            peer_asn = self.validated_data["asn"]

            peer_request = models.PeerRequest.objects.create(
                net=net, peer_asn=peer_asn, type="autopeer"
            )
            return autopeer_tasks.AutopeerRequest.create_task(
                asn,
                peer_asn,
                org=self.context.get("org"),
                peer_request_id=peer_request.id,
            )
        except TaskLimitError:
            raise serializers.ValidationError(
                "You already have a pending autopeer request towards this ASN."
            )


@register
class AutopeerEnabled(serializers.Serializer):
    """
    States whether or not a given asn has autopeer enabled
    """

    asn = serializers.IntegerField()
    enabled = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    ref_tag = "autopeer_enabled"

    class Meta:
        fields = ["asn", "enabled", "url"]

    def get_enabled(self, obj):
        return autopeer_url(obj["asn"]) is not None

    def get_url(self, obj):
        return autopeer_url(obj["asn"])
