from rest_framework import routers

router = routers.DefaultRouter()


def route(viewset):

    if hasattr(viewset, "ref_tag"):
        ref_tag = viewset.ref_tag
    else:
        ref_tag = viewset.serializer_class.ref_tag

    prefix = f"{ref_tag}"
    if getattr(viewset, "require_org_tag", False):
        prefix = f"{prefix}/(?P<org_tag>[^/]+)"

    if getattr(viewset, "require_asn", False):
        prefix = f"{prefix}/(?P<asn>[^/]+)"

    if getattr(viewset, "require_device", False):
        prefix = f"{prefix}/(?P<device_pk>[^/]+)"

    if getattr(viewset, "require_port", False):
        prefix = f"{prefix}/(?P<port_pk>[^/]+)"

    if getattr(viewset, "require_netixlan", False):
        prefix = f"{prefix}/(?P<netixlan_pk>[^/]+)"

    router.register(prefix, viewset, basename=ref_tag)
    return viewset
