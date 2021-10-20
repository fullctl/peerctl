from django.db.models import Q
from fullctl.django.rest.route.service_bridge import route
from fullctl.django.rest.views.service_bridge import DataViewSet, Exclude, MethodFilter

import django_peerctl.models.peerctl as models
from django_peerctl.rest.serializers.service_bridge import Serializers


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
