from fullctl.django.auth import permissions

from django_peerctl.utils import devicectl_create_devices


def create_devices(backend, details, response, uid, user, *args, **kwargs):
    """
    When a user authenticates we create some default devices as necessary for
    the network's that user is provisioned to
    """

    perms = permissions(user)
    perms.load()
    verified_asns = []

    for permission in perms.pset.permissions.values():
        if permission.namespace.match(["verified", "asn"]):
            asn = int(permission.namespace[2])
            verified_asns.append(asn)

    if not verified_asns:
        return

    # TODO better way to figure out which org to assign the network to.
    org = user.org_set.filter(is_default=True).first()
    if org:
        org = org.org

    devicectl_create_devices(org, verified_asns)
