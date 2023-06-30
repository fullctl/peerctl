import fullctl.django.autocomplete.devicectl as devicectl_autocomplete
import fullctl.service_bridge.devicectl as devicectl
from django.utils import html

from django_peerctl.models import InternetExchange, Network, PortInfo


class devicectl_ixi_port(devicectl_autocomplete.devicectl_port):

    """
    Devicectl port autocomplete that only returns IXI ports with IPs set

    IXI ports are exchange ports which can be identified by checking if their ref_id is set
    """

    def get_queryset(self):
        asn = self.request.GET.get("asn")

        if not asn:
            return []

        net = (
            Network.objects.filter(asn=asn)
            .exclude(org_id__isnull=True)
            .select_related("org")
            .first()
        )
        if not net or not net.org_id:
            return []
        org = net.org

        if not self.request.perms.check(f"port.{org.permission_id}", "r"):
            return []

        if not self.q:
            return []

        candidates = (
            PortInfo.objects.filter(net=net, port__gt=0)
            .exclude(ref_id__isnull=True)
            .exclude(ref_id="")
        )

        port_ids = [int(c.port) for c in candidates]
        qs = [
            o
            for o in devicectl.Port().objects(
                org_slug=org.slug, q=self.q, ids=port_ids, has_ips=True
            )
        ]

        # check if query matches any IX names
        ix_match_ports = []
        for candidate in candidates:
            ix = InternetExchange.objects.filter(
                ref_id=candidate.ref_ix_id, name__istartswith=self.q
            ).first()
            if ix:
                ix_match_ports.append(int(candidate.port))

        if len(ix_match_ports) > 0:
            ix_match_ports_obj = [
                o
                for o in devicectl.Port().objects(
                    org_slug=org.slug, ids=ix_match_ports, has_ips=True
                )
            ]

            # combine results from both queries leaving only unique objects
            qs = qs + ix_match_ports_obj
            dict_objects = {obj.id: obj for obj in qs}
            qs = list(dict_objects.values())

        return qs

    def get_result_label(self, devicectl_port):
        port_info = PortInfo.objects.get(port=devicectl_port.id)
        ix = InternetExchange.objects.filter(ref_id=port_info.ref_ix_id).first()

        display_name = ix.name

        ipaddr4 = port_info.ipaddr4
        if not ipaddr4 or ipaddr4 == "-":
            display_name += " No IPs set"
        else:
            display_name += f" {ipaddr4}"

        display_name = html.escape(display_name)

        return {
            "primary": display_name,
            "secondary": "",
            "extra": "",
        }
