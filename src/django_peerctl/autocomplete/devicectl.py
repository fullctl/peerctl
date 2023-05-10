import fullctl.service_bridge.devicectl as devicectl
from dal import autocomplete
from django.utils import html


class devicectl_port(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.q:
            return []
        qs = [
            o
            for o in devicectl.Port().objects(org_slug=self.request.org.slug, q=self.q)
        ]
        return qs

    def get_result_label(self, port):
        display_name = port.display_name

        if not display_name or display_name == "-":
            display_name = "No IPs set"

        display_name = html.escape(display_name)
        virtual_port_name = html.escape(port.virtual_port_name)
        device_name = html.escape(port.device_name)

        return {
            "primary": display_name,
            "secondary": virtual_port_name,
            "extra": device_name,
        }
