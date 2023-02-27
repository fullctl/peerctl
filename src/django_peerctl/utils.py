import ipaddress

from django.db import IntegrityError

from django_peerctl.exceptions import ASNClaimed
from django_peerctl.models import Network


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


def pdb_netixlan_ip_interfaces(netixlan, prefixes):
    """
    Return the ip4 and ip6 addresses with appropriate
    prefix lengths according to the address space
    defined in the ixlanprefix
    """

    ip4 = netixlan.ipaddr4
    ip6 = netixlan.ipaddr6
    prefix4 = None
    prefix6 = None

    # convert to ip address objects

    if ip4:
        ip4 = ipaddress.ip_address(ip4)

    if ip6:
        ip6 = ipaddress.ip_address(ip6)

    # find the matching ixlan prefix

    for ixpfx in prefixes:
        prefix = ipaddress.ip_network(ixpfx.prefix)

        if ip4 and prefix.version == 4 and ip4 in prefix:
            prefix4 = prefix

        if ip6 and prefix.version == 6 and ip6 in prefix:
            prefix6 = prefix

    if ip4:
        if prefix4:
            ip4 = ipaddress.ip_interface(f"{ip4}/{prefix4.prefixlen}")
        else:
            ip4 = ipaddress.ip_interface(ip4)

    if ip6:
        if prefix6:
            ip6 = ipaddress.ip_interface(f"{ip6}/{prefix6.prefixlen}")
        else:
            ip6 = ipaddress.ip_interface(ip6)

    return (ip4, ip6)
