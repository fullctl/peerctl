from django_peerctl.models import Network


def get_network(asn):
    return Network.get_or_create(asn)


def verified_asns(perms, require_device=True):
    for permission in perms.pset.permissions.values():
        if permission.namespace.match(["verified", "asn"]):
            asn = int(permission.namespace[2])
            net = get_network(asn)
            if require_device and not net.device_qs.exists():
                continue
            yield net
