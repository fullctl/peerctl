import fullctl.service_bridge.ixctl as ixctl
import fullctl.service_bridge.pdbctl as pdbctl
import fullctl.service_bridge.sot as sot
from fullctl.django.auth import permissions

from django_peerctl.models import Network, Port
from django_peerctl.utils import get_network


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

    for member in sot.InternetExchangeMember().objects(asns=verified_asns, join="ix"):
        Port.get_or_create(member)
