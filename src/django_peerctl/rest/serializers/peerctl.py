import fullctl.service_bridge.ixctl as ixctl
import fullctl.service_bridge.pdbctl as pdbctl
import fullctl.service_bridge.sot as sot
from django.utils.translation import ugettext_lazy as _
from fullctl.django.rest.decorators import serializer_registry
from fullctl.django.rest.serializers import (
    ModelSerializer,
    RequireContext,
    SoftRequiredValidator,
)
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

import django_peerctl.models as models
from django_peerctl.helpers import get_best_policy
from django_peerctl.peer_session_workflow import PeerSessionEmailWorkflow

Serializers, register = serializer_registry()


@register
class Network(ModelSerializer):

    name = serializers.SerializerMethodField()
    peer_contact_email = serializers.CharField(read_only=True)
    contacts = serializers.SerializerMethodField()

    class Meta:
        model = models.Network
        fields = [
            "id",
            "asn",
            "as_set",
            "as_set_source",
            "name",
            "peer_contact_email",
            "contacts",
        ]

    @models.ref_fallback(lambda s, o: f"AS{o.asn}")
    def get_name(self, instance):
        return instance.ref.name

    def get_contacts(self, instance):
        return instance.contacts


@register
class Device(ModelSerializer):

    display_name = serializers.SerializerMethodField()

    class Meta:
        model = models.Device
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "type",
        ]

    def get_display_name(self, obj):
        return obj.display_name


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
            "count_peers",
        ]


@register
class Port(ModelSerializer):

    net = serializers.IntegerField(source="port_info.net.id", read_only=True)
    asn = serializers.IntegerField(source="port_info.net.asn", read_only=True)
    peers = serializers.SerializerMethodField()

    ix = serializers.SerializerMethodField()
    ix_name = serializers.SerializerMethodField()
    speed = serializers.SerializerMethodField()
    policy4 = serializers.SerializerMethodField()
    policy6 = serializers.SerializerMethodField()
    device = serializers.SerializerMethodField()
    mac_address = serializers.SerializerMethodField()

    ref_ix_id = serializers.SerializerMethodField()

    class Meta:
        model = models.Port
        fields = [
            "id",
            "ix",
            "ix_name",
            "net",
            "asn",
            "speed",
            "peers",
            "policy4",
            "policy6",
            "device",
            "ref_ix_id",
            "mac_address",
        ]

    def get_mac_address(self, instance):
        return f"{instance.mac_address}"

    def get_peers(self, instance):
        return models.PeerSession.objects.filter(port=instance).count()

    @models.ref_fallback(0)
    def get_ix(self, instance):
        return models.InternetExchange.objects.get(
            ref_id=instance.port_info.ref_ix_id
        ).id

    def get_ref_ix_id(self, instance):
        return instance.port_info.ref_ix_id

    @models.ref_fallback("")
    def get_ix_name(self, instance):
        ix = models.InternetExchange.objects.get(ref_id=instance.port_info.ref_ix_id)
        name = f"{ix.name}: {instance.port_info.ipaddr4}"
        return name

    @models.ref_fallback(0)
    def get_speed(self, instance):
        return instance.port_info.ref.speed

    def get_device(self, instance):
        return Device(instance=instance.devices[0]).data

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
class Peer(ModelSerializer):

    scope = serializers.CharField(source="net.info_scope")
    type = serializers.CharField(source="net.info_type")
    policy_ratio = serializers.CharField(source="net.policy_ratio")
    policy_general = serializers.CharField(source="net.policy_general")
    policy_contracts = serializers.CharField(source="net.policy_contracts")
    policy_locations = serializers.CharField(source="net.policy_locations")
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
        model = models.Port
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
            ix = self.context["port"].port_info.ix
            if ix:
                _peer_nets = self.context["net"].peer_nets_at_ix(ix.id)
                for peer_net in _peer_nets:
                    self._peer_nets[peer_net.peer.asn] = peer_net
        return self._peer_nets

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
                    "inherited": getattr(obj.peer_session, f"policy{version}_inherited"),
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
        return self.context["port"].port_info.ix_name

    def get_port_id(self, obj):
        return self.context["port"].id

    def get_device_id(self, obj):
        if "device" not in self.context:
            self.context["device"] = self.context["port"].devices[0]
        return self.context["device"].id

    def get_info_prefixes4(self, obj):
        peer_net = self.peer_nets.get(obj.asn)
        if peer_net and peer_net.info_prefixes4 is not None:
            return peer_net.info_prefixes4
        return obj.net.info_prefixes4

    def get_info_prefixes6(self, obj):
        peer_net = self.peer_nets.get(obj.asn)
        if peer_net and peer_net.info_prefixes6 is not None:
            return peer_net.info_prefixes6
        return obj.net.info_prefixes6


@register
class PeerDetails(ModelSerializer):
    mutual_locations = serializers.SerializerMethodField()

    ref_tag = "peerdetail"

    class Meta:
        model = models.Port
        fields = [
            "id",
            "mutual_locations",
        ]

    def get_mutual_locations(self, obj):
        net = self.context.get("net")
        my_port = self.context.get("port")
        mutual_locs = []
        exclude = [my_port.port_info.ref_ix_id]

        for ix_id, result in net.get_mutual_locations(obj.asn, exclude=exclude).items():
            port = models.Port.get_or_create(result[net.asn][0])
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


@register
class PeerSession(ModelSerializer):
    policy6 = serializers.SerializerMethodField()
    policy4 = serializers.SerializerMethodField()
    asn = serializers.SerializerMethodField()
    devices = serializers.SerializerMethodField()
    device_id = serializers.SerializerMethodField()
    port_display_name = serializers.SerializerMethodField()
    ref_tag = "peer_session"

    class Meta:
        model = models.PeerSession
        fields = [
            "id", 
            "port", 
            "peer_port", 
            "policy6", 
            "policy4" , 
            "asn", 
            "devices",
            "device_id",
            "port_display_name",
            "status"
        ]


    def get_policy(self, obj, version):
        if obj and obj.status == "ok":
            policy = get_best_policy(obj, version, raise_error=False)
            if policy:
                return {
                    "id": policy.id,
                    "name": policy.name,
                    "inherited": getattr(obj, f"policy{version}_inherited"),
                }
        return {}
    
    def get_policy4(self, obj):
        return self.get_policy(obj, 4)

    def get_policy6(self, obj):
        return self.get_policy(obj, 6)

    def get_asn(self, obj):
        return obj.peer_port.peer_net.peer.asn

    def get_devices(self, obj):
        return obj.devices[0].display_name

    def get_device_id(self, obj):
        return obj.devices[0].id

    def get_port_display_name(self, obj):
        return obj.port.port_info.ix_name + " " + obj.port.port_info.ipaddr4



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
        fields = ["id", "name", "type", "body"]


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
        fields = ["id", "name", "type", "body"]


@register
class UserPreferences(ModelSerializer):
    class Meta:
        model = models.UserPreferences
        fields = ["id", "email_opt_features", "email_opt_offers"]
