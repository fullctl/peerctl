from django_peerctl.models import Network
from django.db import IntegrityError
from django_peerctl.exceptions import ASNClaimed


def get_network(asn, org):
    try:
        return Network.get_or_create(asn, org)
    except IntegrityError:
        # another org already claimed this asn
        raise ASNClaimed()

def verified_asns(perms, org, require_device=True):
    for permission in perms.pset.permissions.values():
        if permission.namespace.match(["verified", "asn"]):
            asn = int(permission.namespace[2])
            try:
                net = get_network(asn, org)
            except ASNClaimed:
                continue
            if require_device and not net.devices:
                continue
            yield net
