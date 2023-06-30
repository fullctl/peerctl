import fullctl.django.autocomplete.devicectl as devicectl_autocomplete
from django.utils import html

from django_peerctl.models import InternetExchange, Network, Port, PortInfo


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

        # collect port info objects that an exchange reference, set through
        # ref id

        candidates = (
            PortInfo.objects.filter(net=net, port__gt=0)
            .exclude(ref_id__isnull=True)
            .exclude(ref_id="")
        )

        # map them by port for easy reference layer

        candidates_by_port = {int(c.port): c for c in candidates}

        # batch load service bridge references

        PortInfo.load_references(candidates)

        # gather port ids

        port_ids = [int(c.port) for c in candidates]

        if not self.q:
            # no search query, preprare a list of ports with IPs set
            # return at most 5

            qs = list(Port().objects(org_slug=org.slug, ids=port_ids, has_ips=True))[:5]
            query_exchanges = {}

        else:
            # search query, query devicectl port and ix names separately (Since
            # they dont exist in one service)

            qs = [
                o
                for o in Port().objects(
                    org_slug=org.slug, q=self.q, ids=port_ids, has_ips=True
                )
            ]

            # ix query search
            query_exchanges = {
                ix.ref_id: ix
                for ix in InternetExchange.objects.filter(
                    ref_id__in=[c.ref_ix_id for c in candidates], name__icontains=self.q
                )
            }

        # collect IX matches into ports
        ix_match_ports = []
        for candidate in candidates:
            if query_exchanges.get(candidate.ref_ix_id):
                ix_match_ports.append(int(candidate.port))

        # combine both queries

        if len(ix_match_ports) > 0:
            ix_match_ports_obj = [
                o
                for o in Port().objects(
                    org_slug=org.slug, ids=ix_match_ports, has_ips=True
                )
            ]

            # combine results from both queries leaving only unique objects
            qs = qs + ix_match_ports_obj
            dict_objects = {obj.id: obj for obj in qs}
            qs = list(dict_objects.values())

        # load all exchanges rquired to render the results

        all_exchanges_for_results = {
            ix.ref_id: ix
            for ix in InternetExchange.objects.filter(
                ref_id__in=[c.ref_ix_id for c in candidates]
            )
        }

        # set references to port info objects and ix objects on the result
        # items so we dont need to look them up again during result rendering

        for obj in qs:
            obj._port_info_object = candidates_by_port.get(obj.id)
            obj.ix = all_exchanges_for_results.get(obj.port_info_object.ref_ix_id)

        return qs

    def get_result_label(self, devicectl_port):
        port_info = devicectl_port.port_info_object
        ix = devicectl_port.ix
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
