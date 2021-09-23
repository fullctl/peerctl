from fullctl.django.auth import permissions

from django_peerctl.utils import get_network
from django_peerctl.models import Port, Network


def create_devices(backend, details, response, uid, user, *args, **kwargs):

    """
    When a user authenticates we create some default devices as necessary for
    the network's that user is provisioned to

    TODO: integrate devicectl
    """

    perms = permissions(user)
    perms.load()

    for permission in perms.pset.permissions.values():
        if permission.namespace.match(["verified", "asn"]):
            asn = int(permission.namespace[2])

            net = get_network(asn)
            for netixlan in net.pdb.netixlan_set.filter(status="ok"):
                Port.get_or_create(netixlan)
