import ipaddress

import fullctl.service_bridge.devicectl as devicectl
import fullctl.service_bridge.ixctl as ixctl
import fullctl.service_bridge.pdbctl as pdbctl
import fullctl.service_bridge.sot as sot
from django.db import IntegrityError
from grainy.const import PERM_READ

from django_peerctl.exceptions import ASNClaimed
from django_peerctl.models import Network, PortInfo


def get_network(asn, org):
    try:
        return Network.get_or_create(asn, org)
    except IntegrityError:
        # another org already claimed this asn
        raise ASNClaimed()


def verified_asns(perms, org, require_device=True):
    for permission in perms.pset.permissions.values():
        if permission.namespace.match(["verified", "asn"]) and perms.pset.check(
            permission.namespace, PERM_READ
        ):
            asn = int(permission.namespace[2])
            try:
                net = get_network(asn, org)
            except ASNClaimed:
                continue
            if require_device and not net.devices:
                continue
            yield net


def pdb_netixlan_ip_interfaces(netixlan):
    """
    Return the ip4 and ip6 addresses with appropriate
    prefix lengths according to the address space
    defined in the ixlanprefix
    """

    ip4 = netixlan.ipaddr4
    ip6 = netixlan.ipaddr6

    # convert to ip address objects

    if ip4:
        ip4 = ipaddress.ip_address(ip4)

    if ip6:
        ip6 = ipaddress.ip_address(ip6)

    return pdb_set_prefixlen(ip4, ip6, netixlan.ixlan_id)


def pdb_set_prefixlen(ip4, ip6, pdb_ix_id):
    """
    Will set the prefix length of the ip4 and ip6 addresses
    from peeringdb ixlan prefix data
    """

    ixpfxs = pdbctl.IXLanPrefix().objects(ix=pdb_ix_id)

    if ip4:
        ip4 = ipaddress.ip_interface(ip4)
        for ixpfx in ixpfxs:
            prefix = ipaddress.ip_network(ixpfx.prefix)
            if prefix.version == 4 and ip4.ip in prefix:
                ip4 = ipaddress.ip_interface(f"{ip4.ip}/{prefix.prefixlen}")
                break

    if ip6:
        ip6 = ipaddress.ip_interface(ip6)
        for ixpfx in ixpfxs:
            prefix = ipaddress.ip_network(ixpfx.prefix)
            if prefix.version == 6 and ip6.ip in prefix:
                ip6 = ipaddress.ip_interface(f"{ip6.ip}/{prefix.prefixlen}")
                break

    return (ip4, ip6)


def devicectl_create_devices(org, verified_asns):
    """
    When a user authenticates we create some default devices as necessary for
    the network's that user is provisioned to
    """

    required_ports = {}
    required_port_infos = {}
    networks = {}

    for member in sot.InternetExchangeMember().objects(asns=verified_asns, join="ix"):
        if member.asn not in networks:
            try:
                networks[member.asn] = get_network(member.asn, org)
            except ASNClaimed:
                continue

        source, ip4, ip6, ix_id = port_components(member)
        device_id = f"{source}:{ix_id}"

        required_ports.setdefault(device_id, [])
        required_port_infos.setdefault(ix_id, [])
        required_ports[device_id].append(
            {
                "asn": member.asn,
                "id": member.ref_id,
                "ip_address_4": (f"{ip4}" if ip4 else None),
                "ip_address_6": (f"{ip6}" if ip6 else None),
                "speed": member.speed,
            }
        )
        required_port_infos[ix_id].append(member)

    _ports = devicectl.Port().request_dummy_ports(
        org.slug, required_ports, "peerctl", device_type="junos"
    )
    ports = {}

    # re-arrange ports by ip address, using ip4 if its set and
    # falling back ip6 if its set. Skipping if neither are set.

    for port in _ports:
        if port["ip_address_4"]:
            ports[f"{ipaddress.ip_interface(port['ip_address_4']).ip}"] = port
        elif port["ip_address_6"]:
            ports[f"{ipaddress.ip_interface(port['ip_address_6']).ip}"] = port

    # create port info objects for each port (will also re-assign
    # device-ctl port ids if ip address has moved to a new port.)

    for _, members in required_port_infos.items():
        for member in members:
            ip = member.ipaddr4 if member.ipaddr4 else member.ipaddr6
            if not ip or ip not in ports:
                continue
            network = networks[member.asn]
            PortInfo.require_for_pdb_netixlan(network, ports[ip]["id"], member)


def port_components(member):
    """
    Returns the source, ip4, ip6, ix_id for a member in a tuple
    """

    # pdb sot == ixlan_id
    # ixctl sot == ix_id

    if hasattr(member, "ixlan_id"):
        # pdbctl is sot, set ip addresses from netixlan
        # and also set prefix length from ixlanprefix

        source = "pdbctl"
        ix_id = member.ixlan_id
        ip4, ip6 = pdb_netixlan_ip_interfaces(member)

    else:
        # ixctl is sot, set ip addresses from ix member
        # and also set prefix length from ixlanprefix if
        # ix has pdb_id specified.

        source = "ixctl"
        ix_id = member.ix_id
        ip4 = member.ipaddr4
        ip6 = member.ipaddr6

        if member.ix.pdb_id:
            ip4, ip6 = pdb_set_prefixlen(ip4, ip6, member.ix.pdb_id)

    return (source, ip4, ip6, ix_id)


def load_exchanges(ix_ids):
    """
    Takes a list of ix_ids and returns a list of exchanges

    ix_ids should be in the format of "{src}:{id}" where src is
    either "ixctl" or "pdbctl" and id is the id of the exchange
    """

    exchanges = []
    ixctl_ix_ids = [
        int(ix_id.split(":")[1]) for ix_id in ix_ids if ix_id.startswith("ixctl:")
    ]
    pdbctl_ix_ids = [
        int(ix_id.split(":")[1]) for ix_id in ix_ids if ix_id.startswith("pdbctl:")
    ]

    if ixctl_ix_ids:
        exchanges.extend(ixctl.InternetExchange().objects(ids=ixctl_ix_ids))

    if pdbctl_ix_ids:
        exchanges.extend(pdbctl.InternetExchange().objects(ids=pdbctl_ix_ids))

    return exchanges
