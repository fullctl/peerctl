from django_peerctl.models import Network


def get_network(asn, org):
    return Network.get_or_create(asn, org)


def verified_asns(perms, org, require_device=True):
    for permission in perms.pset.permissions.values():
        if permission.namespace.match(["verified", "asn"]):
            asn = int(permission.namespace[2])
            net = get_network(asn, org)
            if require_device and not net.devices:
                continue
            yield net
