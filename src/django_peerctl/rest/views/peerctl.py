from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django_peeringdb.models.concrete import (
    NetworkIXLan,
)

from fullctl.django.rest.mixins import CachedObjectMixin
from fullctl.django.auth import permissions
from fullctl.django.rest.core import BadRequest
from fullctl.django.rest.decorators import billable, load_object

import django_peerctl.models as models
from django_peerctl.rest.decorators import grainy_endpoint
from django_peerctl.rest.route.peerctl import route
from django_peerctl.rest.serializers.peerctl import Serializers
from django_peerctl.exceptions import UsageLimitError

from django_peerctl.const import (
    DEVICE_TEMPLATE_TYPES,
    DEVICE_TYPES,
)


# network view
# list: all networks user has crud permissions to


@route
class Network(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.net
    queryset = models.Network.objects.all()

    lookup_url_kwarg = "asn"
    lookup_field = "asn"

    # no need to grainy gate this as list filtering does
    # its own permission check
    def list(self, request, *args, **kwargs):
        perms = permissions(request.user)
        perms.load()
        instances = perms.instances(
            models.Network, "crud", explicit=False, ignore_grant_all=True
        )
        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)


# device view
# list: all devices for a network


@route
class Device(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.device
    queryset = models.Device.objects.all()
    require_asn = True

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):
        instances = models.Device.objects.filter(net__asn=asn, status="ok")
        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)


# device-port view
# list: all Ports for a device


# policy view
# list all Polciy for a network
# create
# update
# destroy


@route
class Policy(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.policy
    queryset = models.Policy.objects.all()
    require_asn = True

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):
        instances = models.Policy.objects.filter(net__asn=asn, status="ok")
        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)


# port view
# list all Ports for a network
# set policy
# devices


@route
class Port(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.port
    queryset = models.Port.objects.all()
    require_asn = True

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):

        instances = models.Port.objects.filter(portinfo__net__asn=asn, status="ok")
        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)

    @action(detail=True)
    def devices(self, request, asn, pk):
        port = self.queryset.get(portinfo__net__asn=asn, pk=pk)
        serializer = Serializers.device(instance=port.devices, many=True)
        return Response(serializer.data)


# peer view
# list all peers for a port and asn
# retrieve peer for port and asn
# details peer details for port and asn


@route
class Peer(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.peer
    queryset = models.PeerNetwork.objects.all()
    require_asn = True
    require_port = True

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, net, port_pk, *args, **kwargs):
        port = (
            models.Port.objects.filter(id=port_pk)
            .prefetch_related("peerses_qs")
            .first()
        )
        instances = port.get_available_peers()

        serializer = self.serializer_class(instances, many=True, context={"port": port, "net": net})
        return Response(serializer.data)


    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @load_object("peer", NetworkIXLan, id="pk")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def retrieve(self, request, asn, net, port_pk, port, pk, peer, *args, **kwargs):
        serializer = self.serializer_class(peer, context={"port": port, "net": net})
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @load_object("peer", NetworkIXLan, id="pk")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def details(self, request, asn, net, port_pk, port, pk, peer, *args, **kwargs):
        serializer = Serializers.peerdetail(
            peer, context={"port":port, "net":net}
        )
        return Response(serializer.data)


    @action(detail=True, methods=["put"])
    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @load_object("peer", NetworkIXLan, id="pk")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def set_md5(self, request, asn, net, port_pk, port, pk, peer, *args, **kwargs):

        other_net= Network.objects.get(asn=netixlan.net.asn)
        peernet = PeerNetwork.get_or_create(net, other_net)

        peernet.md5 = request.POST.get("value")
        peernet.save()

        serializer = self.serializer_class(
            instance=peer, context={"port": port, "net": net}
        )
        return Response(serializer.data)


# peer request view
# create


# peer session view
# create

@route
class PeerSession(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.peerses
    queryset = models.PeerSession.objects.all()
    require_asn = True
    require_port = True

    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, port_pk, port, *args, **kwargs):
        data = request.POST.dict()

        netixlan = NetworkIXLan.objects.get(id=data.get("netixlan"))

        if data.get("through"):
            through_netixlan = NetworkIXLan.objects.get(id=data.get("through"))
        else:
            through_netixlan = netixlan

        peerport = models.PeerPort.get_or_create_from_netixlans(
            models.Port.objects.get(id=port_pk).portinfo.pdb, netixlan
        )


        #XXX aaactl metered limiting
        #try:
        #    port.portinfo.net.validate_limits()
        #except UsageLimitError as exc:
        #    raise serializers.ValidationError(
        #        {"non_field_errors": [["usage_limit", "{}".format(exc)]]}
        #    )

        instance = models.PeerSession.get_or_create(port, peerport)
        instance.status = "ok"
        instance.save()

        models.AuditLog.log_peerses_add(instance, request.user)

        serializer = Serializers.peer(
            through_netixlan, context={"port": port, "net": net}
        )
        return Response(serializer.data)

    def set_policy(self, request, asn_pk, port_pk, pk):
        peerses = self.queryset.get(port__portinfo__net__asn=asn_pk, pk=pk)

        ip_version = int(request.POST.get("ipv"))
        policy_id = int(request.POST.get("value"))
        policy = None

        if policy_id:
            policy = Policy.objects.get(id=policy_id, net__asn=asn_pk)

        try:
            peerses.set_policy(policy, ip_version)
        except Exception as exc:
            raise serializers.ValidationError({"non_field_errors": [[str(exc)]]})

        serializer = self.serializer_class(peerses)
        return Response(serializer.data)

    def destroy(self, request, asn_pk, port_pk, pk):
        instance = self.get_object()
        r = super(PeerSessionViewSet, self).destroy(request, asn_pk, port_pk, pk)
        AuditLog.log_peerses_del(instance, request.user)
        return r



# wish view
# list
# create

# user prefs
# list
# update

# email template
# list
# create
# preview


@route
class EmailTemplate(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.emltmpl
    queryset = models.EmailTemplate.objects.all()
    require_asn = True

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):
        instances = models.EmailTemplate.objects.filter(net__asn=asn, status="ok")
        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)


# device template
# list
# create
# preview


@route
class DeviceTemplate(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.devicetmpl
    queryset = models.DeviceTemplate.objects.all()
    require_asn = True

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):
        return Response({})

    @action(detail=False)
    def list_available(self, request, asn, *args, **kwargs):
        # load default templates (netom)
        data = [{"id": tmpl[0], "name": tmpl[1]} for tmpl in DEVICE_TEMPLATE_TYPES]

        # if a device type is specified in url parameters we
        # only want to display template types for this device type
        devtyp = request.GET.get("device_type")
        devtypes = dict(DEVICE_TYPES)
        if devtyp:
            devname = devtypes.get(devtyp)
            trimmed = []
            for tmpl in data:
                if tmpl["id"].find(f"{devtyp}-") == 0:
                    # remove device type label from template label
                    # as it's redundant when specifying a device
                    tmpl["name"] = tmpl["name"].replace(devname + " ", "")
                    trimmed.append(tmpl)
            data = trimmed

        serializer = Serializers.devicelist(data, many=True)
        return Response(serializer.data)
