from django.conf import settings

from django_peerctl.confutil import discover_netom_templates

DEVICE_TYPES = (
    ("arista", "Arista EOS"),
    ("bird", "BIRD"),
    ("bird2", "BIRD 2"),
    ("cisco", "Cisco IOS"),
    ("cisco-xr", "Ciscoi IOS XR"),
    ("junos", "Juniper Junos OS"),
    ("junos-set", "Juniper Junos OS set"),
    ("sros-md", "Nokia SR OS MD-CLI"),
    ("sros-classic", "Nokia SR OS Classic CLI"),
)

DEVICE_TEMPLATES, DEVICE_TEMPLATE_TYPES = discover_netom_templates(
    DEVICE_TYPES, settings.NETOM_TEMPLATE_DIR
)

AUDIT_EVENTS = (
    ("peerses-request", "Peering Request"),
    ("peerses-add", "Session Add"),
    ("peerses-del", "Session Delete"),
    ("peerses-mod", "Session Modify"),
    ("policy-mod", "Policy Modify"),
    ("email", "Email"),
)

EMAIL_ORIGIN = (
    ("peerses-workflow", "Peering Session Workflow"),
    ("bulk-email", "Notification Email"),
)
