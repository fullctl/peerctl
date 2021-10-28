from django.db.models import Q
from fullctl.django.rest.route.service_bridge import route
from fullctl.django.rest.views.service_bridge import DataViewSet, Exclude, HeartbeatViewSet, StatusViewSet

import django_peerctl.models.peerctl as models
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
        (
            "has_as_set",
            Exclude(Q(as_set_override__isnull=True) | Q(as_set_override="")),
        ),
    ]
    autocomplete = "name"
    allow_unfiltered = True

    queryset = models.Network.objects.all()
    serializer_class = Serializers.net
