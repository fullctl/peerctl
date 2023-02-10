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
