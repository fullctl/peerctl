from fullctl.django.rest.decorators import serializer_registry
from fullctl.django.rest.serializers import ModelSerializer

import django_peerctl.models.peerctl as models

# from rest_framework import serializers


Serializers, register = serializer_registry()


@register
class Network(ModelSerializer):
    class Meta:
        model = models.Network
        fields = ["id", "name", "asn", "as_set"]
