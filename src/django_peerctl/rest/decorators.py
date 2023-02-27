from fullctl.django.rest.decorators import base
from fullctl.django.rest.decorators import grainy_endpoint as _grainy_endpoint

import django_peerctl.models as models


def load_org_instance_from_asn(self, request, data):
    if "asn" in data:
        org = models.Network.objects.get(asn=data["asn"]).org

        request.org = org
        data.update(org=request.org)

        if isinstance(data.get("instance"), self.instance_class):
            return

        instance, _ = self.instance_class.objects.get_or_create(org=request.org)
        data.update(instance=instance, org=request.org)

    elif request.org.id:
        data.update(org=request.org)

        if isinstance(data.get("instance"), self.instance_class):
            return


base.load_org_instance = load_org_instance_from_asn


class grainy_endpoint(_grainy_endpoint):
    def __init__(self, *args, **kwargs):
        super().__init__(
            instance_class=models.Instance,
            explicit=kwargs.pop("explicit", False),
            # apply_perms seems to collide with ? in the namespace
            # possible grainy bug - turn off for now since we dont need
            # this for anything at the moment
            enable_apply_perms=False,
            *args,
            **kwargs
        )
        if "namespace" not in kwargs:
            self.namespace += ["peerctl"]
