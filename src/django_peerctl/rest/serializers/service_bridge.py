from fullctl.django.rest.decorators import serializer_registry
from fullctl.django.rest.serializers import ModelSerializer
from rest_framework import serializers

import django_peerctl.models.peerctl as models

Serializers, register = serializer_registry()


@register
class Network(ModelSerializer):
    class Meta:
        model = models.Network
        fields = ["id", "name", "asn", "as_set", "prefix4", "prefix6"]


@register
class RequestDevicectlSync(serializers.Serializer):
    org_id = serializers.IntegerField()
    ref_tag = "request_devicectl_sync"

    class Meta:
        fields = ["org_id"]
