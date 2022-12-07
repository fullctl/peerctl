import fullctl.service_bridge.pdbctl as pdbctl

# from django.utils.translation import ugettext_lazy as _
from fullctl.django.rest.decorators import serializer_registry
from fullctl.django.rest.serializers import ModelSerializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError  # noqa

import django_peerctl.models as models
from django_peerctl.helpers import get_best_policy

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
    speed = serializers.SerializerMethodField()
    policy4 = serializers.SerializerMethodField()
    policy6 = serializers.SerializerMethodField()
    device = serializers.SerializerMethodField()
    mac_address = serializers.SerializerMethodField()

    ref_ix_id = serializers.SerializerMethodField()

    class Meta:

        fields = [
            "id",
            "ix",
            "ix_name",
            "display_name",
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
        # XXX implement devicectl
        return ""

    def get_peers(self, instance):
        return models.PeerSession.objects.filter(port=instance).count()

    @models.ref_fallback(0)
    def get_ix(self, instance):
        return models.InternetExchange.objects.get(
            ref_id=instance.port_info_object.ref_ix_id
        ).id

    def get_ref_ix_id(self, instance):
        return instance.port_info_object.ref_ix_id

    @models.ref_fallback("")
    def get_ix_name(self, instance):
        self.get_device(instance)
        if not self.get_ix(instance):
            if instance.virtual_port_name and not instance.virtual_port_name.startswith("pdb:"):
                return f"{instance.device.name} {instance.display_name} {instance.virtual_port_name} "
            return f"{instance.device.name} {instance.display_name}"

        ix = models.InternetExchange.objects.get(
            ref_id=instance.port_info_object.ref_ix_id
        )
        if instance.virtual_port_name and not instance.virtual_port_name.startswith("pdb:"):
            name = f"{instance.device.name} {ix.name} {instance.ip_address_4} {instance.virtual_port_name}"
        else:
            name = f"{instance.device.name} {ix.name} {instance.ip_address_4}"
        return name

    def get_display_name(self, instance):
        if instance.virtual_port_name and not instance.virtual_port_name.startswith("pdb:"):
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
class Peer(serializers.Serializer):

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


@register
class CreateFloatingPeerSession(serializers.Serializer):

    ip_address_4 = serializers.CharField(allow_null=True, allow_blank=True)
    ip_address_6 = serializers.CharField(allow_null=True, allow_blank=True)
    policy_4 = serializers.IntegerField()
    policy_6 = serializers.IntegerField()
    peer_prefixes4 = serializers.IntegerField(allow_null=True)
    peer_prefixes6 = serializers.IntegerField(allow_null=True)
    md5 = serializers.CharField(allow_null=True, allow_blank=True)
    peer_asn = serializers.IntegerField()
    peer_interface = serializers.CharField(allow_null=True, allow_blank=True)
    port = serializers.IntegerField()

    ref_tag = "create_floating_peer_session"

    class Meta:
        fields = [
            "ip_address_4",
            "ip_address_6",
            "policy_4",
            "policy_6",
            "md5",
            "peer_asn",
            "peer_interface",
            "peer_prefixes4",
            "peer_prefixes6",
            "port",
        ]

    def validate_peer_prefixes4(self, value):
        if value < 0:
            raise serializers.ValidationError("Cannot be negative")
        return value

    def validate_peer_prefixes6(self, value):
        if value < 0:
            raise serializers.ValidationError("Cannot be negative")
        return value

    def save(self):

        data = self.validated_data
        asn = self.context.get("asn")

        net = models.Network.objects.get(asn=asn)

        port_info = models.PortInfo.objects.create(
            port=0,
            net=net,
            ip_address_4=data["ip_address_4"],
            ip_address_6=data["ip_address_6"],
        )

        peer = models.Network.get_or_create(asn=data["peer_asn"], org=None)

        peer_net = models.PeerNetwork.get_or_create(net, peer)
        peer_net.md5 = data["md5"]
        peer_net.info_prefixes4 = data["peer_prefixes4"]
        peer_net.info_prefixes6 = data["peer_prefixes6"]
        peer_net.save()

        peer_port = models.PeerPort.get_or_create(port_info, peer_net)
        peer_port.interface_name = data["peer_interface"]
        peer_port.save()

        return models.PeerSession.objects.create(
            port=data["port"],
            peer_port=peer_port,
            policy4_id=data["policy_4"] or None,
            policy6_id=data["policy_6"] or None,
            status="ok",
        )


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

    port_id = serializers.IntegerField(source="port")
    port_display_name = serializers.SerializerMethodField()
    port_interface = serializers.SerializerMethodField()

    md5 = serializers.SerializerMethodField()

    ref_tag = "peer_session"

    class Meta:
        model = models.PeerSession
        fields = [
            "id",
            "port_id",
            "port_interface",
            "port_display_name",
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
            "status",
        ]

    def get_policy(self, obj, version):

        if obj and obj.status == "ok":
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
        return obj.devices[0].display_name

    def get_device_id(self, obj):
        return obj.devices[0].id

    def get_port_interface(self, obj):
        return obj.port.object.virtual_port_name

    def get_port_display_name(self, obj):
        return (
            obj.port.object.port_info_object.ix_name
            + " "
            + obj.port.object.virtual_port_name
            + " "
            + obj.port.object.port_info_object.ipaddr4
        ).strip()


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


@register
class NetworkLocation(serializers.Serializer):
    ix_id = serializers.IntegerField()
    ix_name = serializers.CharField()

    ref_tag = "network_location"

    class Meta:
        fields = ["ix_id", "ix_name"]


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
