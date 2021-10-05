from django.utils.translation import ugettext_lazy as _
from fullctl.django.rest.decorators import serializer_registry
from fullctl.django.rest.serializers import (
    ModelSerializer,
    RequireContext,
    SoftRequiredValidator,
)
import fullctl.service_bridge.pdbctl as pdbctl_bridge

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

import django_peerctl.models as models

from django_peerctl.peerses_workflow import PeerSessionEmailWorkflow

from django_peerctl.helpers import (
    get_best_policy,
)



Serializers, register = serializer_registry()


@register
class Network(ModelSerializer):

    name = serializers.SerializerMethodField()
    peer_contact_email = serializers.CharField(read_only=True)
    contacts = serializers.SerializerMethodField()

    class Meta:
        model = models.Network
        fields = ["id", "asn", "name", "peer_contact_email", "contacts"]

    @models.pdb_fallback(lambda s, o: f"AS{o.asn}")
    def get_name(self, instance):
        return instance.pdb.name

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

    net = serializers.IntegerField(source="portinfo.net.id", read_only=True)
    asn = serializers.IntegerField(source="portinfo.net.asn", read_only=True)
    peers = serializers.SerializerMethodField()

    ix = serializers.SerializerMethodField()
    ix_name = serializers.SerializerMethodField()
    speed = serializers.SerializerMethodField()
    policy4 = serializers.SerializerMethodField()
    policy6 = serializers.SerializerMethodField()
    device = serializers.SerializerMethodField()

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
        ]

    def get_peers(self, instance):
        return models.PeerSession.objects.filter(port=instance).count()

    @models.pdb_fallback(0)
    def get_ix(self, instance):
        return models.InternetExchange.objects.get(
            ixlan_id=instance.portinfo.pdb.ixlan_id
        ).id

    @models.pdb_fallback("")
    def get_ix_name(self, instance):
        ix = models.InternetExchange.objects.get(ixlan_id=instance.portinfo.pdb.ixlan_id)
        name = f"{ix.name}: {instance.portinfo.ipaddr4}"
        return name

    @models.pdb_fallback(0)
    def get_speed(self, instance):
        return instance.portinfo.pdb.speed

    def get_device(self, instance):
        return Device(instance=instance.devices[0]).data

    def get_policy(self, instance, version):
        policy = get_best_policy(instance, version, raise_error=False)
        if policy:
            return {
                "id": policy.id,
                "inherited": getattr(instance, "policy{}_inherited".format(version)),
                "name": policy.name,
            }
        return {}

    def get_policy4(self, instance):
        return self.get_policy(instance, 4)

    def get_policy6(self, instance):
        return self.get_policy(instance, 6)


@register
class Peer(ModelSerializer):

    name = serializers.CharField(source="net.name")
    asn = serializers.IntegerField(source="net.asn")
    scope = serializers.CharField(source="net.info_scope")
    type = serializers.CharField(source="net.info_type")
    policy_ratio = serializers.CharField(source="net.policy_ratio")
    policy_general = serializers.CharField(source="net.policy_general")
    policy_contracts = serializers.CharField(source="net.policy_contracts")
    policy_locations = serializers.CharField(source="net.policy_locations")
    peeringdb = serializers.SerializerMethodField()
    peerses = serializers.SerializerMethodField()
    peerses_status = serializers.SerializerMethodField()
    peerses_contact = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    md5 = serializers.SerializerMethodField()
    ix_name = serializers.SerializerMethodField()
    port_id = serializers.SerializerMethodField()
    info_prefixes4 = serializers.SerializerMethodField()
    info_prefixes6 = serializers.SerializerMethodField()
    ipaddr = serializers.SerializerMethodField()
    is_rs_peer = serializers.BooleanField()
    ref_tag = "peer"

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
            "peerses",
            "peerses_status",
            "peerses_contact",
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

            self._pocs = [poc for poc in pdbctl_bridge.NetworkContact().objects(
                nets=[i.net_id for i in peers],
                require_email=True,
                role="policy"
            )]


        return self._pocs

    @property
    def peernets(self):
        """
        Returns all peer networks at the port specified in
        the serializer context

        Will be cached in order to speed up serialization
        times
        """
        if not hasattr(self, "_peernets"):
            self._peernets = {}
            ix = self.context["port"].portinfo.ix
            if ix:
                _peernets = self.context["net"].peernets_at_ix(ix.id)
                for peernet in _peernets:
                    self._peernets[peernet.peer.asn] = peernet
        return self._peernets

    def get_peeringdb(self, obj):
        return "https://www.peeringdb.com/asn/{}".format(obj.net.asn)

    def get_ipaddr(self, obj):
        result = []

        if not isinstance(self.instance, list):
            qset = pdbctl_bridge.NetworkIXLan().objects(ix=obj.ixlan_id, asn=obj.asn)
        else:
            qset = self.instance


        for netixlan in qset:
            if netixlan.asn != obj.asn:
                continue

            peerses = self.get_peerses(netixlan)
            result.append(
                {
                    "ipaddr4": str(netixlan.ipaddr4),
                    "ipaddr6": str(netixlan.ipaddr6),
                    "policy4": self.get_policy(netixlan, 4),
                    "policy6": self.get_policy(netixlan, 6),
                    "peerses": peerses,
                    "peerses_status": self.get_peerses_status(netixlan),
                    "origin_id": obj.id,
                    "id": netixlan.id,
                }
            )

        return result

    def get_policy(self, obj, version):
        peerses = getattr(obj, "peerses", None)
        if peerses and peerses.status == "ok":
            policy = get_best_policy(obj.peerses, version, raise_error=False)
            if policy:
                return {
                    "id": policy.id,
                    "name": policy.name,
                    "inherited": getattr(
                        obj.peerses, "policy{}_inherited".format(version)
                    ),
                }
        return {}

    def get_policy4(self, obj):
        return self.get_policy(obj, 4)

    def get_policy6(self, obj):
        return self.get_policy(obj, 6)

    def get_peerses(self, obj):
        if getattr(obj, "peerses", None):
            return obj.peerses.id
        peerses = self.port.get_peerses(obj)

        # cache peerses on obj, so we can re-use during `get_user`
        # `get_peerses_status`
        obj.peerses = peerses
        if peerses:
            return peerses.id
        return 0

    def get_peerses_contact(self, obj):
        for poc in self.pocs:
            if poc.net_id == obj.net_id:
                return poc.email
        return None

    def get_peerses_status(self, obj):
        peerses = getattr(obj, "peerses", None)
        if peerses:
            return peerses.status
        return None

    def get_md5(self, obj):
        peernet = self.peernets.get(obj.net.asn)
        if peernet:
            return peernet.md5
        return ""

    def get_user(self, obj):
        peerses = getattr(obj, "peerses", None)
        if peerses:
            user = peerses.user
            if user:
                return user.username
        return None

    def get_ix_name(self, obj):
        return self.context["port"].portinfo.ix_name

    def get_port_id(self, obj):
        return self.context["port"].id

    def get_info_prefixes4(self, obj):
        peernet = self.peernets.get(obj.net.asn)
        if peernet and peernet.info_prefixes4 is not None:
            return peernet.info_prefixes4
        return obj.net.info_prefixes4

    def get_info_prefixes6(self, obj):
        peernet = self.peernets.get(obj.net.asn)
        if peernet and peernet.info_prefixes6 is not None:
            return peernet.info_prefixes6
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

        for ixlan_id, result in net.get_mutual_locations(obj.asn).items():
            port = models.Port.get_or_create(result[net.asn][0])
            if port.id == my_port.id:
                continue
            port_data = Port(instance=port).data
            for asn, netixlans in result.items():
                if asn == net.asn:
                    continue
                for netixlan in netixlans:
                    peer = Peer(
                        instance=netixlan, context={"port": port, "net": net}
                    ).data
                    peer["port"] = port_data
                    mutual_locs.append(peer)

        return mutual_locs


@register
class PeerSession(ModelSerializer):
    class Meta:
        model = models.PeerSession
        fields = ["id", "port", "peerport"]


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
            return obj["id"]
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
