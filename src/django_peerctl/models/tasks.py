from fullctl.django.models.concrete import Task
from fullctl.django.tasks import register
import fullctl.service_bridge.ixctl as ixctl


@register
class SyncMacAddress(Task):

    """
    Sync the port mac address to ixctl
    """

    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_sync_mac_address"

    def run(self, member_id, mac_address, *args, **kwargs):
        ixctl.InternetExchangeMember().set_mac_address(
            member_id, mac_address, source="peerctl"
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
