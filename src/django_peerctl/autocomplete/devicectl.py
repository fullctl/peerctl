from dal import autocomplete
from django.utils import html

import fullctl.service_bridge.devicectl as devicectl
from fullctl.django.models.concrete import Organization

from django_peerctl.models import PortInfo, Network

import fullctl.django.autocomplete.devicectl as devicectl_autocomplete


class devicectl_ixi_port(devicectl_autocomplete.devicectl_port):

    """
    Devicectl port autocomplete that only returns IXI ports with IPs set

    IXI ports are exchange ports which can be identified by checking if their ref_id is set
    """

    def get_queryset(self):

        asn=self.request.GET.get("asn")

        if not asn:
            return []

        net = Network.objects.filter(asn=asn).exclude(org_id__isnull=True).select_related("org").first()
        if not net or not net.org_id:
            return []
        org = net.org

        if not self.request.perms.check(f"port.{org.permission_id}", "r"):
            return []

        if not self.q:
            return []

        candidates = PortInfo.objects.filter(net=net, port__gt=0).exclude(ref_id__isnull=True).exclude(ref_id="")

        port_ids = [int(c.port) for c in candidates]

        qs = [o for o in devicectl.Port().objects(org_slug=org.slug, q=self.q, ids=port_ids, has_ips=True)]
        return qs