import fullctl.service_bridge.devicectl as devicectl
import fullctl.service_bridge.sot as sot
from fullctl.django.auth import permissions

from django_peerctl.models import PortInfo
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

    if not verified_asns:
        return

    required_ports = {}
    required_port_infos = {}
    networks = {}

    # TODO better way to figure out which org to assign the network to.
    org = user.org_set.filter(is_default=True).first()
    if org:
        org = org.org

    port_infos = {p.ref_id: p for p in PortInfo.objects.filter(net__org=org)}

    for member in sot.InternetExchangeMember().objects(asns=verified_asns, join="ix"):
        if member.asn not in networks:
            networks[member.asn] = get_network(member.asn, org)

        if member.ref_id not in port_infos:
            required_ports.setdefault(member.ixlan_id, [])
            required_port_infos.setdefault(member.ixlan_id, [])
            required_ports[member.ixlan_id].append(
                {
                    "asn": member.asn,
                    "id": member.ref_id,
                    "ip_address_4": member.ipaddr4,
                    "ip_address_6": member.ipaddr6,
                    "speed": member.speed,
                }
            )
            required_port_infos[member.ixlan_id].append(member)

    ports = devicectl.Port().request_dummy_ports(
        org.slug, required_ports, "pdb", device_type="bird"
    )

    ports = {port["name"]: port for port in ports}

    for ixlan_id, members in required_port_infos.items():
        for member in members:
            network = networks[member.asn]
            PortInfo.require_for_pdb_netixlan(
                network, ports[f"pdb:{member.ref_id}"]["id"], member
            )

    # There is no reason to create PortInfo objects for PNIs here
    # as PortInfo objects currently only inform IXIs
    #
    #for port in devicectl.Port().objects(org=org.permission_id):
    #    if port.is_management:
    #        continue
    #    if not port.ip_address_4 and not port.ip_address_6:
    #        continue
    #    if PortInfo.objects.filter(port=port.id).exists():
    #        continue
    #    PortInfo.objects.create(net=networks[verified_asns[0]], port=port.id)
