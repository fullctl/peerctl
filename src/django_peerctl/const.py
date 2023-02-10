from django.utils.translation import gettext as _
from django.conf import settings

from django_peerctl.confutil import discover_netom_templates

DEVICE_TYPES = (
    ("arista", "Arista EOS"),
    ("bird", "BIRD"),
    ("bird2", "BIRD 2"),
    ("cisco", "Cisco IOS"),
    ("cisco-xr", "Cisco IOS XR"),
    ("cisco-nexus", "Cisco Nexus"),
    ("junos", "Juniper Junos OS"),
    ("junos-set", "Juniper Junos OS set"),
    ("sros-md", "Nokia SR OS MD-CLI"),
    ("sros-classic", "Nokia SR OS Classic CLI"),
)

NET_TYPES = (
    ("NSP", _("NSP")),
    ("Content", _("Content")),
    ("Cable/DSL/ISP", _("Cable/DSL/ISP")),
    ("Enterprise", _("Enterprise")),
    ("Educational/Research", _("Educational/Research")),
    ("Non-Profit", _("Non-Profit")),
    ("Route Server", _("Route Server")),
    ("Network Services", _("Network Services")),
    ("Route Collector", _("Route Collector")),
    ("Government", _("Government")),
)

TRAFFIC = (
    ("0-20Mbps", _("0-20Mbps")),
    ("20-100Mbps", _("20-100Mbps")),
    ("100-1000Mbps", _("100-1000Mbps")),
    ("1-5Gbps", _("1-5Gbps")),
    ("5-10Gbps", _("5-10Gbps")),
    ("10-20Gbps", _("10-20Gbps")),
    ("20-50Gbps", _("20-50Gbps")),
    ("50-100Gbps", _("50-100Gbps")),
    ("100-200Gbps", _("100-200Gbps")),
    ("200-300Gbps", _("200-300Gbps")),
    ("300-500Gbps", _("300-500Gbps")),
    ("500-1000Gbps", _("500-1000Gbps")),
    ("1-5Tbps", _("1-5Tbps")),
    ("5-10Tbps", _("5-10Tbps")),
    ("10-20Tbps", _("10-20Tbps")),
    ("20-50Tbps", _("20-50Tbps")),
    ("50-100Tbps", _("50-100Tbps")),
    ("100+Tbps", _("100+Tbps")),
)

SCOPES = (
    ("Regional", _("Regional")),
    ("North America", _("North America")),
    ("Asia Pacific", _("Asia Pacific")),
    ("Europe", _("Europe")),
    ("South America", _("South America")),
    ("Africa", _("Africa")),
    ("Australia", _("Australia")),
    ("Middle East", _("Middle East")),
    ("Global", _("Global")),
)

RATIOS = (
    ("Heavy Outbound", _("Heavy Outbound")),
    ("Mostly Outbound", _("Mostly Outbound")),
    ("Balanced", _("Balanced")),
    ("Mostly Inbound", _("Mostly Inbound")),
    ("Heavy Inbound", _("Heavy Inbound")),
)


DEVICE_TEMPLATES, DEVICE_TEMPLATE_TYPES = discover_netom_templates(
    DEVICE_TYPES, settings.NETOM_TEMPLATE_DIR
)

AUDIT_EVENTS = (
    ("peer_session-request", "Peering Request"),
    ("peer_session-add", "Session Add"),
    ("peer_session-del", "Session Delete"),
    ("peer_session-mod", "Session Modify"),
    ("policy-mod", "Policy Modify"),
    ("email", "Email"),
)

EMAIL_ORIGIN = (
    ("peer_session-workflow", "Peering Session Workflow"),
    ("bulk-email", "Notification Email"),
)
