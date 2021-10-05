from fullctl.django.auth import permissions

from django_peerctl.utils import get_network
from django_peerctl.models import Port, Network

from fullctl.service_bridge.pdbctl import NetworkIXLan


def create_devices(backend, details, response, uid, user, *args, **kwargs):

    """
    When a user authenticates we create some default devices as necessary for
    the network's that user is provisioned to

    TODO: integrate devicectl
    """

    perms = permissions(user)
    perms.load()
    verified_asns = []

    for permission in perms.pset.permissions.values():
        if permission.namespace.match(["verified", "asn"]):
            asn = int(permission.namespace[2])
            verified_asns.append(asn)


    for netixlan in NetworkIXLan().objects(asns=verified_asns):
        print("Port", netixlan)
        Port.get_or_create(netixlan)
