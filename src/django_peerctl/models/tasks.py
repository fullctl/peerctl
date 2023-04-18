import fullctl.service_bridge.ixctl as ixctl
from fullctl.django.models.concrete import Task
from fullctl.django.tasks import register

@register
class SyncMacAddress(Task):

    """
    Sync the port mac address to ixctl
    """

    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_sync_mac_address"

    def run(self, asn, ip4, mac_address, *args, **kwargs):
        ixctl.InternetExchangeMember().set_mac_address(
            asn, ip4, mac_address, source="peerctl"
        )


@register
class SyncASSet(Task):

    """
    Sync the network as-set to ixctl
    """

    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_sync_asset"

    def run(self, member_id, as_macro, *args, **kwargs):
        ixctl.InternetExchangeMember().set_as_macro(
            member_id, as_macro, source="peerctl"
        )


@register
class SyncRouteServerMD5(Task):

    """
    Sync the network's route server md5 to ixctl
    """

    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_sync_md5"

    def run(self, asn, md5, member_ip, router_ip, *args, **kwargs):
        ixctl.InternetExchangeMember().set_route_server_md5(
            asn, md5, member_ip, router_ip, source="peerctl"
        )


@register
class SyncIsRsPeer(Task):

    """
    Syncs the network's route server peer status to ixctl for a member port
    """

    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_sync_is_rs_peer"

    def run(self, asn, ip4, is_rs_peer, *args, **kwargs):
        # get the member object

        member = ixctl.InternetExchangeMember().first(ip=ip4, asn=asn, ix_verified=True)

        if not member:
            return f"no member found for {asn} {ip4} at any verified ix"

        # send a partial update to ixctl to set the is_rs_peer
        # value accordingly

        ixctl.InternetExchangeMember().partial_update(
            member, {"is_rs_peer": is_rs_peer}
        )

        return f"updated {member.id} is_rs_peer to {is_rs_peer}"

@register
class SyncDevicePorts(Task):

    """
    Sync devices and ports from devicectl to port info objects in peerctl
    
    This will call utils.devicectl_create_devices for all networks owned by an
    organziation.
    """

    class Meta:
        proxy = True

    class TaskMeta:
        limit = 1

    class HandleRef:
        tag = "task_sync_device_ports"


    def run(self, *args, **kwargs):
        from django_peerctl.utils import devicectl_create_devices
        from django_peerctl.models import Organization
        devicectl_create_devices(self.org, [net.asn for net in self.org.net_set.all()])

    def generate_limit_id(self):
        return self.org_id
