from django.db.models import Q
from fullctl.django.models.concrete.tasks import TaskLimitError
from fullctl.django.rest.route.service_bridge import route
from fullctl.django.rest.views.service_bridge import (
    DataViewSet,
    Exclude,
    HeartbeatViewSet,
    StatusViewSet,
)
from rest_framework.decorators import action
from rest_framework.response import Response

import django_peerctl.models.peerctl as models
from django_peerctl.models.tasks import SyncDevicePorts
from django_peerctl.rest.serializers.service_bridge import Serializers


@route
class Status(StatusViewSet):
    checks = ("bridge_aaactl", "bridge_ixctl", "bridge_pdbctl")


@route
class Heartbeat(HeartbeatViewSet):
    pass


@route
class Network(DataViewSet):
    path_prefix = "/data"
    allowed_http_methods = ["GET"]
    valid_filters = [
        ("q", "name__icontains"),
        ("asn", "asn"),
        ("asns", "asn__in"),
        ("org", "instance__org__remote_id"),
        ("org_slug", "instance__org__slug"),
        (
            "has_as_set",
            Exclude(Q(as_set_override__isnull=True) | Q(as_set_override="")),
        ),
        (
            "has_overrides",
            Exclude(
                (
                    Q(as_set_override__isnull=True) | Q(as_set_override=""),
                    Q(prefix4_override__isnull=True),
                    Q(prefix6_override__isnull=True),
                )
            ),
        ),
    ]
    autocomplete = "name"
    allow_unfiltered = True

    queryset = models.Network.objects.all()
    serializer_class = Serializers.net

    @action(
        detail=False,
        methods=["POST"],
        serializer_class=Serializers.request_devicectl_sync,
    )
    def request_devicectl_sync(self, request, *args, **kwargs):
        serializer = Serializers.request_devicectl_sync(data=request.data)
        serializer.is_valid(raise_exception=True)

        org = models.Organization.objects.get(
            remote_id=serializer.validated_data["org_id"]
        )

        try:
            SyncDevicePorts.create_task(org=org)
        except TaskLimitError:
            pass

        return Response(serializer.data)
