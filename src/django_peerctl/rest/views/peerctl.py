import ipaddress

import fullctl.service_bridge.ixctl as ixctl
import fullctl.service_bridge.pdbctl as pdbctl
import fullctl.service_bridge.sot as sot
from fullctl.django.auth import permissions
from fullctl.django.rest.core import BadRequest
from fullctl.django.rest.decorators import load_object
from fullctl.django.rest.mixins import CachedObjectMixin
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

import django_peerctl.models as models
from django_peerctl.const import DEVICE_TEMPLATE_TYPES, DEVICE_TYPES
from django_peerctl.exceptions import TemplateRenderError, UsageLimitError
from django_peerctl.models.tasks import SyncASSet
from django_peerctl.peer_session_workflow import (
    PeerRequestToAsnWorkflow,
    PeerSessionEmailWorkflow,
)
from django_peerctl.rest.decorators import grainy_endpoint
from django_peerctl.rest.route.peerctl import route
from django_peerctl.rest.serializers.peerctl import Serializers, ValidationError


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

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def update(self, request, asn, net, *args, **kwargs):
        serializer = self.serializer_class(net, data=request.data)

        if not serializer.is_valid():
            return BadRequest(serializer.errors)

        serializer.save()
        SyncASSet.create_task(asn, net.as_set_override)

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        serializer_class=Serializers.peeringdb_relationship,
    )
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def facilities(self, request, asn, net, *args, **kwargs):
        """
        Returns a list of peeringdb facilities for a network
        """

        entities = list(pdbctl.Facility().objects(asn=asn))
        serializer = self.get_serializer(entities, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        serializer_class=Serializers.peeringdb_relationship,
    )
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def internet_exchanges(self, request, asn, net, *args, **kwargs):
        """
        Returns a list of peeringdb exchanges for a network
        """

        entities = list(pdbctl.InternetExchange().objects(asn=asn))
        serializer = self.get_serializer(entities, many=True)
        return Response(serializer.data)


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

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)

        is_global4 = request.data.get("is_global4", False)
        if is_global4 == "false":
            is_global4 = False

        is_global6 = request.data.get("is_global6", False)
        if is_global6 == "false":
            is_global6 = False

        serializer.is_valid(raise_exception=True)

        policy = serializer.save(net=net, status="ok")

        if is_global4:
            net.policy4 = policy
            net.save()

        if is_global6:
            net.policy6 = policy
            net.save()

        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @load_object("policy", models.Policy, id="pk", net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def update(self, request, asn, net, pk, policy, *args, **kwargs):
        serializer = self.serializer_class(instance=policy, data=request.data)

        is_global4 = request.data.get("is_global4", False)
        if is_global4 == "false":
            is_global4 = False

        is_global6 = request.data.get("is_global6", False)
        if is_global6 == "false":
            is_global6 = False

        serializer.is_valid(raise_exception=True)

        serializer.save()

        if not is_global4 and net.policy4_id == policy.id:
            net.policy4 = None
            net.save()
        elif is_global4:
            net.policy4 = policy
            net.save()

        if not is_global6 and net.policy6_id == policy.id:
            net.policy6 = None
            net.save()
        elif is_global6:
            net.policy6 = policy
            net.save()

        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @load_object("policy", models.Policy, id="pk", net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def destroy(self, request, asn, net, pk, policy, *args, **kwargs):
        r = Response(self.serializer_class(policy).data)
        policy.delete()
        return r


@route
class Port(CachedObjectMixin, viewsets.GenericViewSet):
    serializer_class = Serializers.port
    require_asn = True

    def get_serializer_class(self):
        if self.action == "update":
            return Serializers.port_update
        return super().get_serializer_class()

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):
        filter_device = request.GET.get("device")
        ixi = request.GET.get("ixi")
        load_md5 = request.GET.get("load_md5", False)

        qset = models.PortInfo.objects.filter(
            net__org=request.org, net__asn=asn, port__gt=0
        )

        if ixi:
            # only grab IXI ports

            qset = qset.filter(ref_id__gt=0)

        # collect port ids

        port_ids = [int(obj.port) for obj in qset]

        instances = models.Port.preload(
            request.org, asn, port_ids, filter_device=filter_device
        )

        if ixi:
            models.Port.augment_ix(instances, asn)

        serializer = self.serializer_class(
            instances, many=True, context={"load_md5": load_md5}
        )

        data = sorted(serializer.data, key=lambda x: x["ix_simple_name"])

        return Response(data)

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def retrieve(self, request, asn, pk, *args, **kwargs):
        port = models.Port().object(pk)
        serializer = Serializers.port(instance=port)
        return Response(serializer.data)

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def update(self, request, asn, pk, *args, **kwargs):
        port = models.Port().object(pk)

        serializer = self.get_serializer_class()(
            data=request.data, context={"port": port}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="(?P<pk>[^/.]+)/list-available-ports",
        serializer_class=Serializers.available_port,
    )
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list_available_ports(self, request, asn, pk, *args, **kwargs):
        port = models.Port().object(pk)

        serializer = Serializers.available_port(data=request.GET)
        serializer.is_valid(raise_exception=True)

        ports = models.Port().objects(
            org=request.org.remote_id, device=serializer.validated_data["device_id"]
        )

        instances = [
            p
            for p in ports
            if (
                not p.is_management
                and not models.PortInfo.objects.filter(port=p.id)
                .exclude(port=port.id)
                .exists()
            )
        ]
        serializer = Serializers.available_port(instances, many=True)

        return Response(serializer.data)

    @action(detail=False, methods=["put"], url_path="(?P<pk>[^/.]+)/change-port")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def change_port(self, request, asn, pk, *args, **kwargs):
        current_port = models.Port().object(pk)

        if request.data["id"] == "0":
            serializer = Serializers.port(instance=current_port)
            return Response(serializer.data)

        new_port = models.Port().object(request.data["id"])

        models.PortInfo.migrate_ports(current_port, new_port)

        serializer = Serializers.port(instance=new_port)

        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    @load_object("port", models.Port, id="pk", port_info__net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def devices(self, request, asn, pk, port, *args, **kwargs):
        serializer = Serializers.device(instance=port.devices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["put"], url_path="(?P<pk>[^/.]+)/set_policy")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def set_policy(self, request, asn, pk, *args, **kwargs):
        # get port
        port = models.Port().object(pk)

        # check that the net owns the port
        models.PortInfo.objects.get(port=port, net__asn=asn)

        ip_version = int(request.data.get("ipv"))
        policy_id = int(request.data.get("value"))
        policy = None

        if policy_id:
            policy = models.Policy.objects.get(id=policy_id, net__asn=asn)

        try:
            port.set_policy(policy, ip_version)
        except Exception as exc:
            return BadRequest({"non_field_errors": [[str(exc)]]})

        serializer = self.serializer_class(port)
        return Response(serializer.data)

    @action(detail=True, methods=["put"])
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def set_mac_address(self, request, asn, pk, *args, **kwargs):
        # get port
        port = models.Port().object(pk)
        mac_address = request.data.get("mac_address")
        try:
            port.set_mac_address(mac_address)
        except Exception as exc:
            return BadRequest({"non_field_errors": [[str(exc)]]})

        serializer = self.serializer_class(port)
        return Response(serializer.data)

    @action(detail=True, methods=["put"])
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def set_is_route_server_peer(self, request, asn, pk, *args, **kwargs):
        # get port
        port = models.Port().object(pk)
        is_route_server_peer = request.data.get("is_route_server_peer")
        try:
            port.set_is_route_server_peer(is_route_server_peer)
        except Exception as exc:
            return BadRequest({"non_field_errors": [[str(exc)]]})

        serializer = self.serializer_class(port)
        return Response(serializer.data)


# peer view
# list all peers for a port and asn
# retrieve peer for port and asn
# details peer details for port and asn


def get_member(pk, join=None):
    ref_source, ref_id = pk.split(":")
    return models.PortInfo.ref_bridge(ref_source).object(ref_id, join=join)


@route
class NetworkSearch(viewsets.GenericViewSet):
    serializer_class = Serializers.network_search
    require_asn = True
    lookup_url_kwarg = "other_asn"

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def retrieve(self, request, asn, other_asn, **kwargs):
        network = pdbctl.Network().first(asn=other_asn)

        poc = pdbctl.NetworkContact().first(
            asn=other_asn, require_email=True, role="policy"
        )

        if not network:
            return Response([])

        if not poc:
            email = None
        else:
            email = poc.email

        result = {
            "asn": network.asn,
            "name": network.name,
            "peer_session_contact": email,
            "mutual_locations": {},
            "their_locations": {},
            "our_locations": {},
        }

        locations_them = {}
        locations_us = {}

        # get their exchanges, our exchanges, and also summarize mutual exchanges

        for netixlan in pdbctl.NetworkIXLan().objects(asns=[asn, other_asn], join="ix"):
            if netixlan.asn == int(asn):
                locations_us[netixlan.ix.id] = netixlan.ix.name
            elif netixlan.asn == int(other_asn):
                locations_them[netixlan.ix.id] = netixlan.ix.name

        for ix_id, ix_name in locations_them.items():
            result["their_locations"][ix_id] = {"ix_name": ix_name, "ix_id": ix_id}

        for ix_id, ix_name in locations_us.items():
            result["our_locations"][ix_id] = {"ix_name": ix_name, "ix_id": ix_id}

        for ix_id in result["their_locations"].keys() & result["our_locations"].keys():
            result["mutual_locations"][ix_id] = result["their_locations"].get(
                ix_id, result["our_locations"].get(ix_id)
            )
            del result["their_locations"][ix_id]
            del result["our_locations"][ix_id]

        # for mutual exchanges also note when there is already a session
        # configured

        peer_sessions = list(
            models.PeerSession.objects.filter(
                peer_port__peer_net__net__asn=asn,
                peer_port__peer_net__peer__asn=other_asn,
                status="ok",
            ).select_related("peer_port", "peer_port__port_info")
        )

        # loop through mutual locations

        for ix_id, loc_data in result["mutual_locations"].items():
            # loop through all peering sessions for this net and asn
            for session in peer_sessions:
                # check if the session is for this ix
                # for pdbctl this a straight forward ix id comparison
                # for ixctl we need to get the ix object and compare the pdb id

                port_info = session.peer_port.port_info

                try:
                    source = port_info.ref_source
                except sot.ReferenceNotSetError:
                    source = None

                if source == "pdbctl" and port_info.ref.ix_id == f"pdbctl:{ix_id}":
                    loc_data["session"] = True
                    break
                elif source == "ixctl":
                    ixctl_ix_id = port_info.ref_ix_id.split(":")[1]
                    ixctl_ix = ixctl.InternetExchange().object(ixctl_ix_id)

                    if ixctl_ix.pdb_id == ix_id:
                        loc_data["session"] = True
                        break
                elif session.port:
                    # the peer port does not have a direct reference to a
                    # pdbctl networkixlan or ixctl internet exchange member
                    # so we check by ip-address match instead.

                    ses_port_info = session.port.object.port_info_object

                    loc_data["session"] = ses_port_info.in_same_subnet(port_info)

        result["their_locations"] = sorted(
            list(result["their_locations"].values()), key=lambda x: x["ix_name"]
        )
        result["our_locations"] = sorted(
            list(result["our_locations"].values()), key=lambda x: x["ix_name"]
        )
        result["mutual_locations"] = sorted(
            list(result["mutual_locations"].values()), key=lambda x: x["ix_name"]
        )

        serializer = self.serializer_class(result)
        return Response(serializer.data)


@route
class SessionsSummary(CachedObjectMixin, viewsets.GenericViewSet):
    serializer_class = Serializers.peer_session
    require_asn = True
    optional_port = True
    ref_tag = "sessions_summary"

    def _filter_peer(self, sessions, peer):
        if not peer:
            return sessions
        try:
            peer = str(ipaddress.ip_interface(peer))
        except ValueError:
            pass

        r = []
        for session in sessions:
            if session.peer_ip4 == peer or session.peer_ip6 == peer:
                r.append(session)
            elif session.peer_port.peer_net.peer.name.lower().find(peer.lower()) > -1:
                r.append(session)
            elif str(session.peer_port.peer_net.peer.asn) == peer:
                r.append(session)

        return r

    def prefetch_relations(self, instances):
        port_ids = [i.port for i in instances]
        ports = {
            port.id: port
            for port in models.Port().objects(id__in=port_ids, join="device")
        }

        peer_asns = list({i.peer_port.peer_net.peer.asn for i in instances})
        peer_nets = {}
        if peer_asns:
            peer_nets = {
                net.asn: net for net in pdbctl.Network().objects(asns=peer_asns)
            }
        else:
            peer_nets = {}

        for i in instances:
            if not i.port:
                continue

            port = ports.get(int(i.port))
            if port:
                i.port._object = port

            net = peer_nets.get(i.peer_port.peer_net.peer.asn)
            i.peer_port.peer_net.peer._ref = net

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, net, *args, **kwargs):
        instances = net.peer_session_set.filter(status="ok")

        print([instance.id for instance in instances])

        instances = list(self._filter_peer(instances, request.GET.get("peer")))

        print([instance.id for instance in instances])

        self.prefetch_relations(instances)

        serializer = self.serializer_class(instances, many=True)
        data = sorted(serializer.data, key=lambda x: (x["peer_asn"], x["id"]))

        return Response(data)

    @action(detail=False, methods=["get"], url_path="port/(?P<port_pk>[^/]+)")
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list_by_port(self, request, asn, net, port_pk, *args, **kwargs):
        port = models.Port().object(id=port_pk)
        instances = port.peer_session_qs_prefetched.filter(status="ok")
        instances = self._filter_peer(instances, request.GET.get("peer"))

        self.prefetch_relations(instances)
        serializer = self.serializer_class(instances, many=True)
        data = sorted(serializer.data, key=lambda x: (x["peer_asn"], x["id"]))
        return Response(data)

    @action(detail=False, methods=["get"], url_path="device/(?P<device_pk>[^/]+)")
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list_by_device(self, request, asn, net, device_pk, *args, **kwargs):
        device = models.Device().object(id=device_pk)
        instances = device.peer_session_qs.filter(status="ok")
        instances = self._filter_peer(instances, request.GET.get("peer"))
        self.prefetch_relations(instances)
        serializer = self.serializer_class(instances, many=True)
        data = sorted(serializer.data, key=lambda x: (x["peer_asn"], x["id"]))
        return Response(data)

    @action(detail=False, methods=["get"], url_path="facility/(?P<facility_tag>[^/]+)")
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list_by_facility(self, request, asn, net, facility_tag, *args, **kwargs):
        devices = models.Device().objects(facility_slug=facility_tag)

        instances = []

        for device in devices:
            instances.extend(list(device.peer_session_qs.filter(status="ok")))

        instances = self._filter_peer(instances, request.GET.get("peer"))
        self.prefetch_relations(instances)
        serializer = self.serializer_class(instances, many=True)
        data = sorted(serializer.data, key=lambda x: (x["peer_asn"], x["id"]))
        return Response(data)

    @action(
        detail=False,
        methods=["get"],
        url_path="device/(?P<device_pk>[^/]+)/port/(?P<port_pk>[^/]+)",
    )
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list_by_port_and_device(
        self, request, asn, net, device_pk, port_pk, *args, **kwargs
    ):
        port = models.Port().object(id=port_pk)
        instances = port.peer_session_qs_prefetched.filter(status="ok")

        serializer = self.serializer_class(instances, many=True)

        intersection = []
        for row in serializer.data:
            if str(row["device_id"]) == device_pk:
                intersection.append(row)

        return Response(intersection)

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def destroy(self, request, asn, net, pk, *args, **kwargs):
        peer_session = models.PeerSession.objects.get(
            id=pk, peer_port__peer_net__net=net
        )
        response = Response(self.serializer_class(peer_session).data)
        peer_session.delete()
        return response


@route
class Peer(CachedObjectMixin, viewsets.GenericViewSet):
    serializer_class = Serializers.peer
    require_asn = True
    require_port = True

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, net, port_pk, *args, **kwargs):
        port = models.Port().first(id=port_pk)

        device = port.devices[0]

        instances = port.get_available_peers()

        serializer = self.serializer_class(
            instances, many=True, context={"port": port, "net": net, "device": device}
        )

        unified = {}
        for row in serializer.data:
            if row["asn"] == int(asn):
                continue
            if row["asn"] not in unified:
                unified[row["asn"]] = row

        # parse ordering
        #
        # we cannot use the existing ordering filters we have in fullctl
        # since that expects a django queryset and we are dealing with
        # service bridge data here
        #
        # TODO: make a fullctl thing for this like we already have
        # for django-rest-framework sql queries
        ordering = request.GET.get("ordering", "name") or "name"
        ordering_reverse = ordering[0] == "-"
        if ordering_reverse:
            ordering = ordering[1:]

        if ordering not in ["name"]:
            ordering = "name"

        return Response(
            sorted(
                list(unified.values()),
                key=lambda x: x[ordering].lower(),
                reverse=ordering_reverse,
            )
        )

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def retrieve(self, request, asn, net, port_pk, pk, *args, **kwargs):
        port = models.Port().object(port_pk)
        peer = get_member(pk)
        serializer = self.serializer_class(peer, context={"port": port, "net": net})
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def details(self, request, asn, net, port_pk, pk, *args, **kwargs):
        port = models.Port().object(port_pk)
        peer = get_member(pk)
        serializer = Serializers.peerdetail(peer, context={"port": port, "net": net})
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def mutual_locations(self, request, asn, net, port_pk, pk, *args, **kwargs):
        peer = get_member(pk)

        port = models.Port().object(port_pk)

        serializer = Serializers.peerdetail(peer, context={"port": port, "net": net})

        result = []

        for row in serializer.data["mutual_locations"]:
            for ip_row in row["ipaddr"]:
                ip_row["ix_name"] = row["ix_name"]
                ip_row["port_id"] = row["port_id"]
                ip_row["device_id"] = row["port"]["device"]["id"]
            result.extend(row["ipaddr"])

        return Response(result)

    @action(detail=True, methods=["put"])
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def set_md5(self, request, asn, net, port_pk, pk, *args, **kwargs):
        port = models.Port().object(port_pk)

        if int(asn) != port.asn:
            return Response({}, status=404)

        member = get_member(pk)
        peer = models.Network.objects.get(asn=member.asn)
        peer_net = models.PeerNetwork.get_or_create(net, peer)

        peer_net.md5 = request.data.get("md5")
        peer_net.save()

        peer_net.sync_route_server_md5()

        serializer = self.serializer_class(
            instance=member, context={"port": port, "net": net}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["put"])
    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def set_max_prefix(self, request, asn, net, port_pk, port, pk, *args, **kwargs):
        member = get_member(pk)
        peer = models.Network.objects.get(asn=member.asn)
        peer_net = models.PeerNetwork.get_or_create(net, peer)

        try:
            peer_net.set_info_prefixes(
                request.data.get("value"), request.data.get("ipv")
            )
        except ValidationError as exc:
            raise ValidationError(detail=exc.message_dict)
        except Exception as exc:
            raise ValidationError({"non_field_errors": [[str(exc)]]})

        serializer = self.serializer_class(
            instance=member, context={"port": port, "net": net}
        )
        return Response(serializer.data)


# peer request view
# create


@route
class PeerRequest(CachedObjectMixin, viewsets.ModelViewSet):
    serializer_class = Serializers.peer_session
    queryset = models.PeerSession.objects.all()
    require_asn = True
    require_port = True
    require_member = True

    ref_tag = "email_workflow"

    # XXX throttle scopes

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, port_pk, member_pk, *args, **kwargs):
        port = models.Port().object(port_pk)
        member = get_member(member_pk)
        reply_to = request.data.get("reply_to")
        from_email = request.data.get("from_email")
        email_template_id = int(request.data.get("email_template", 0))
        content = request.data.get("body")

        # update reply-to if specified
        if reply_to != net.email_override:
            net.email_override = reply_to
            net.full_clean()
            net.save()

        # update from-address override if specified
        if from_email != net.from_email_override:
            net.from_email_override = from_email
            net.full_clean()
            net.save()

        workflow = PeerSessionEmailWorkflow(port, member)
        workflow.cc = request.data.get("cc_reply_to")
        workflow.test_mode = request.data.get("test_mode")
        workflow.peer_contact_override = request.data.get("peer_session_contact")

        if email_template_id > 0:
            email_template = models.EmailTemplate.objects.get(id=email_template_id)
        else:
            email_template = models.EmailTemplate(type=workflow.next_step, net=net)

        # if content is passed with request, override it
        if content:
            email_template.content_override = content

        try:
            peer_session = workflow.progress(request.user, email_template)
        except TemplateRenderError as exc:
            raise ValidationError({"non_field_errors": [f"{exc}"]})
        except UsageLimitError as exc:
            raise ValidationError({"non_field_errors": [["usage_limit", f"{exc}"]]})

        if workflow.test_mode:
            return Response({})

        serializer = Serializers.peer(
            [ps.peer_port.port_info.ref for ps in peer_session],
            many=True,
            context={"port": port, "net": net},
        )
        return Response(serializer.data)


@route
class PeerRequestToAsn(CachedObjectMixin, viewsets.ModelViewSet):
    serializer_class = Serializers.peer_session
    queryset = models.PeerSession.objects.all()
    require_asn = True

    ref_tag = "email_asn_request_peering"

    # XXX throttle scopes

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, *args, **kwargs):
        reply_to = request.data.get("reply_to")
        from_email = request.data.get("from_email")
        email_template_id = int(request.data.get("email_template", 0))
        content = request.data.get("body")

        # update reply-to if specified
        if reply_to != net.email_override:
            net.email_override = reply_to
            net.full_clean()
            net.save()

        # update from-address override if specified
        if from_email != net.from_email_override:
            net.from_email_override = from_email
            net.full_clean()
            net.save()

        workflow = PeerRequestToAsnWorkflow(
            asn, request.data.get("asn"), request.data.get("ix_ids")
        )
        workflow.cc = request.data.get("cc_reply_to")
        workflow.test_mode = request.data.get("test_mode")
        workflow.peer_contact_override = request.data.get("peer_session_contact")

        if email_template_id > 0:
            email_template = models.EmailTemplate.objects.get(id=email_template_id)
        else:
            email_template = models.EmailTemplate(type=workflow.next_step, net=net)

        # if content is passed with request, override it
        if content:
            email_template.content_override = content

        try:
            workflow.progress(request.user, email_template)
        except TemplateRenderError as exc:
            raise ValidationError({"non_field_errors": [f"{exc}"]})
        except UsageLimitError as exc:
            raise ValidationError({"non_field_errors": [["usage_limit", f"{exc}"]]})

        return Response({})


# peer session view
# create


@route
class PeerSession(CachedObjectMixin, viewsets.ModelViewSet):
    serializer_class = Serializers.peer_session
    queryset = models.PeerSession.objects.all()
    require_asn = True
    require_port = True

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, port_pk, *args, **kwargs):
        data = request.data

        port = models.Port().first(id=port_pk, org_slug=net.org.slug)

        if not port:
            return Response({}, status=404)

        member = get_member(data.get("member"), join="ix")

        if data.get("through"):
            through_member = get_member(data.get("through"), join="ix")
        else:
            through_member = member

        if not data.get("peer_asn"):
            data["peer_asn"] = 0

        # check if session exists

        session_exists = models.PeerSession.get_unique(
            asn,
            port.device_id,
            member.asn,
            member.ipaddr4 or member.ipaddr6,
        )

        if not session_exists:
            peer_port = models.PeerPort.get_or_create_from_members(
                port.port_info_object.ref, member
            )

            instance = models.PeerSession.get_or_create(port, peer_port)
            instance.status = "ok"
            instance.save()

            models.AuditLog.log_peer_session_add(instance, request.user)

        serializer = Serializers.peer(
            through_member, context={"port": port, "net": net}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["put"])
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def set_policy(self, request, asn, net, port_pk, pk, *args, **kwargs):
        # make sure port exists
        models.Port().object(port_pk)

        peer_session = models.PeerSession.objects.get(id=pk)

        ip_version = int(request.data.get("ipv"))
        policy_id = int(request.data.get("value"))
        policy = None

        if policy_id:
            policy = models.Policy.objects.get(id=policy_id, net__asn=asn)

        try:
            peer_session.set_policy(policy, ip_version)
        except Exception as exc:
            return BadRequest({"non_field_errors": [[str(exc)]]})

        serializer = self.serializer_class(peer_session)
        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def destroy(self, request, asn, net, port_pk, pk, *args, **kwargs):
        port = models.Port().object(port_pk)
        peer_session = models.PeerSession.objects.get(id=pk)

        response = Response(self.serializer_class(peer_session).data)

        if peer_session.port and int(peer_session.port.id) == int(port_pk):
            super().destroy(request, asn, port, pk)
        return response


@route
class UpdatePeerSession(CachedObjectMixin, viewsets.ModelViewSet):

    """
    Ultimate endpoint for creating and updating peer session objects
    based on port (ip or id), peer asn, and peer ip

    Should eventually replace all other ends points for updating / creating
    peer sessions
    """

    serializer_class = Serializers.peer_session
    queryset = models.PeerSession.objects.all()
    require_asn = True
    ref_tag = "update_peer_session"

    def get_serializer_dynamic(self, path, method, direction):
        """
        Retrieve correct serializer class for openapi schema
        generation
        """

        if method == "POST":
            return Serializers.update_peer_session()

        return Serializers.peer_session()

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, *args, **kwargs):
        """
        Handles saving of peer session data (both creation an update)

        Unique sessions are identified by device or port (ip) + peer asn + peer ip

        If a peer session already exists, it is updated, otherwise a new
        session is created.
        """

        data = request.data

        # the form will send blank strings for these fields, in which case they should
        # just be removed

        if "peer_maxprefix4" in data and not data["peer_maxprefix4"]:
            data.pop("peer_maxprefix4")

        if "peer_maxprefix6" in data and not data["peer_maxprefix6"]:
            data.pop("peer_maxprefix6")

        if "policy4" in data and (not data["policy4"] or data["policy4"] == "0"):
            data["policy4"] = None

        if "policy6" in data and (not data["policy6"] or data["policy6"] == "0"):
            data["policy6"] = None

        if "id" in data and not data["id"]:
            data.pop("id")

        valid_slz = Serializers.update_peer_session(data=data, context={"asn": asn})
        valid_slz.is_valid(raise_exception=True)

        data = valid_slz.validated_data

        if data.get("id"):
            # id is specified, so thats the session to update
            session = models.PeerSession.objects.get(
                pk=data["id"], peer_port__peer_net__net=net
            )

            collision = models.PeerSession.get_unique(
                asn,
                data["device"],
                data["peer_asn"],
                data.get("peer_ip4") or data.get("peer_ip6"),
            )

            if collision and collision.id != session.id:
                return BadRequest(
                    {
                        "non_field_errors": [
                            "A session with the same device, peer asn, and peer ip already exists"
                        ]
                    }
                )
        else:
            # other wise we use the unique fields to find the session
            session = models.PeerSession.get_unique(
                asn,
                data["device"],
                data["peer_asn"],
                data.get("peer_ip4") or data.get("peer_ip6"),
            )

        if session:
            print(data)

            serializer = Serializers.update_peer_session(
                instance=session, data=data, context={"asn": asn}
            )

        else:
            serializer = Serializers.update_peer_session(
                data=data, context={"asn": asn}
            )

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def destroy(self, request, asn, net, *args, **kwargs):
        """
        Handles deletion of a peer session

        Unique sessions are identified by port (ip) + peer asn + peer ip
        """

        data = request.data

        if "id" in data and not data["id"]:
            data.pop("id")

        valid_slz = Serializers.update_peer_session(data=data, context={"asn": asn})
        valid_slz.is_valid(raise_exception=True)

        data = valid_slz.validated_data

        if data.get("id"):
            # id is specified, so thats the session to update
            session = models.PeerSession.objects.get(
                pk=data["id"], peer_port__peer_net__net=net
            )
        else:
            # other wise we use the unique fields to find the session
            session = models.PeerSession.get_unique(
                asn,
                data["device"],
                data["peer_asn"],
                data.get("peer_ip4") or data.get("peer_ip6"),
            )

        if not session:
            return Response({}, status=404)

        response = Response(valid_slz.data)

        session.delete()

        return response


@route
class PartialPeerSession(CachedObjectMixin, viewsets.ModelViewSet):
    """
    DEPRECATED - use UpdatePeerSession instead
    """

    serializer_class = Serializers.peer_session
    queryset = models.PeerSession.objects.all()
    require_asn = True

    ref_tag = "partial_peer_session"

    def get_serializer_dynamic(self, path, method, direction):
        """
        Retrieve correct serializer class for openapi schema
        generation
        """

        if method == "POST":
            return Serializers.create_partial_peer_session()
        elif method == "PUT":
            return Serializers.update_partial_peer_session()

        return Serializers.peer_session()

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, *args, **kwargs):
        data = request.data.copy()

        if not data.get("peer_maxprefix4"):
            data["peer_maxprefix4"] = 0

        if not data.get("peer_maxprefix6"):
            data["peer_maxprefix6"] = 0

        if not data.get("peer_asn"):
            data["peer_asn"] = 0

        if not data.get("port"):
            data["port"] = 0

        serializer = Serializers.update_peer_session(data=data, context={"asn": asn})

        serializer.is_valid(raise_exception=True)

        peer_session = serializer.save()

        return Response(self.serializer_class(peer_session).data)

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def update(self, request, asn, net, pk, *args, **kwargs):
        data = request.data.copy()
        session = models.PeerSession.objects.get(pk=pk, peer_port__peer_net__net=net)

        if not data.get("peer_maxprefix4"):
            data["peer_maxprefix4"] = 0

        if not data.get("peer_maxprefix6"):
            data["peer_maxprefix6"] = 0

        if not data.get("peer_asn"):
            data["peer_asn"] = 0

        if not data.get("port"):
            data["port"] = 0

        serializer = Serializers.update_peer_session(
            session, data=data, context={"asn": asn}
        )

        serializer.is_valid(raise_exception=True)

        peer_session = serializer.save()

        return Response(self.serializer_class(peer_session).data)


@route
class UserPreferences(CachedObjectMixin, viewsets.ModelViewSet):
    serializer_class = Serializers.user
    queryset = models.UserPreferences.objects.all()

    def update(self, request, pk=None, *args, **kwargs):
        user = models.UserPreferences.get_or_create(request.user)
        serializer = self.serializer_class(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user_id=request.user.id, status="ok")
        return Response(serializer.data)

    def list(self, request):
        user = models.UserPreferences.get_or_create(request.user)
        serializer = self.serializer_class(instance=user)
        return Response(serializer.data)


# email template
# list
# create
# preview


@route
class EmailTemplate(CachedObjectMixin, viewsets.ModelViewSet):
    serializer_class = Serializers.email_template
    queryset = models.EmailTemplate.objects.all()
    require_asn = True

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):
        instances = models.EmailTemplate.objects.filter(status="ok", net__asn=asn)
        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @load_object("tmpl", models.EmailTemplate, id="pk", net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def destroy(self, request, asn, net, pk, tmpl, *args, **kwargs):
        r = Response(self.serializer_class(tmpl).data)
        tmpl.delete()
        return r

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(net_id=net.id, status="ok")
        return Response(serializer.data)

    @action(detail=False, methods=["post", "get"])
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def preview_default(self, request, asn, net, *args, **kwargs):
        return self._preview(request, asn, net, "0", *args, **kwargs)

    @action(detail=True, methods=["post", "get"])
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def preview(self, request, asn, net, pk, *args, **kwargs):
        return self._preview(request, asn, net, pk, *args, **kwargs)

    def _preview(self, request, asn, net, pk, *args, **kwargs):
        """
        Template preview

        expects `body` and `type` in POST

        Renders TemplatePreviewSerializer response
        """
        if not pk or pk == "0":
            email_template = models.EmailTemplate(
                name="Preview",
                net=net,
                body=request.data.get("body"),
                type=request.data.get("type"),
            )
        else:
            email_template = models.EmailTemplate.objects.get(id=pk)

        email_template.context["asn"] = request.data.get("asn")

        if "peer" in request.data:
            email_template.context["peer"] = get_member(request.data["peer"])
        elif "asn" in request.data:
            email_template.context["peer"] = sot.InternetExchangeMember().first(
                asn=request.data["asn"]
            )
        else:
            email_template.context["peer"] = sot.InternetExchangeMember().first(asn=asn)

        if request.data.get("ix_ids"):
            email_template.context["selected_exchanges"] = list(
                models.MutualLocation(ix, net, None)
                for ix in pdbctl.InternetExchange().objects(ids=request.data["ix_ids"])
            )

        if "peer_session" in request.data:
            email_template.context["sessions"] = models.PeerSession.objects.filter(
                id=request.data["peer_session"]
            )

        serializer = Serializers.tmplpreview(instance=email_template)
        return Response(serializer.data)


# device template
# list
# create
# preview


@route
class DeviceTemplate(CachedObjectMixin, viewsets.ModelViewSet):
    serializer_class = Serializers.device_template
    queryset = models.DeviceTemplate.objects.all()
    require_asn = True

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):
        instances = models.DeviceTemplate.objects.filter(status="ok", net__asn=asn)
        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @load_object("tmpl", models.DeviceTemplate, id="pk", net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def destroy(self, request, asn, net, pk, tmpl, *args, **kwargs):
        r = Response(self.serializer_class(tmpl).data)
        tmpl.delete()
        return r

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(net_id=net.id, status="ok")
        return Response(serializer.data)

    @action(detail=False, methods=["post", "get"])
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def preview_default(self, request, asn, net, *args, **kwargs):
        return self._preview(request, asn, net, "0", *args, **kwargs)

    @action(detail=True, methods=["post", "get"])
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def preview(self, request, asn, net, pk, *args, **kwargs):
        return self._preview(request, asn, net, pk, *args, **kwargs)

    def _preview(self, request, asn, net, pk, *args, **kwargs):
        if not pk or pk == "0":
            device_template = models.DeviceTemplate(
                name="Preview",
                net=net,
                body=request.data.get("body"),
                type=request.data.get("type"),
            )
        else:
            device_template = models.DeviceTemplate.objects.get(id=pk)

        port = net.port_info_qs.first().port.object

        device_template.context["port"] = port
        device_template.context["net"] = net
        # FIXME: support more than one physical port in templates (expose multiple devices?)
        device_template.context["device"] = models.Device().object(port.device_id)
        device_template.context["member"] = request.data.get("member")

        serializer = Serializers.tmplpreview(instance=device_template)
        return Response(serializer.data)

    @action(detail=False)
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
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


# bulk email
