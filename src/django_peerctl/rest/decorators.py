from fullctl.django.rest.decorators import grainy_endpoint as _grainy_endpoint

import django_peerctl.models as models


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
