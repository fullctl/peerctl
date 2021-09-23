from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


class ModelSerializer(serializers.ModelSerializer):
    grainy = serializers.SerializerMethodField()

    def get_grainy(self, obj):
        if hasattr(obj, "Grainy"):
            return obj.Grainy.namespace(obj)
        return None


class RequireContext:

    required_context = []

    def validate(self, data):
        data = super().validate(data)

        for key in self.required_context:
            if key not in self.context:
                raise serializers.ValidationError(_(f"Context missing: {key}"))

        return data
