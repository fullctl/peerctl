import fullctl.django.rest.urls.service_bridge_proxy as proxy
from django.conf import settings
from django.urls import include, path

import django_peerctl.views as views
from django_peerctl.legacy.views import device_template_base, email_template_base

import django_peerctl.autocomplete.devicectl

# from fullctl.django.views.template import TemplateFileView


proxy.setup(
    "devicectl",
    proxy.proxy_api(
        "devicectl",
        settings.DEVICECTL_URL,
        [
            (
                "facility/{org_tag}/{fac_tag}/devices/",
                "facility/<str:org_tag>/<str:fac_tag>/devices/",
                "facility-devices",
            ),
            (
                "facility/{org_tag}/{fac_tag}/",
                "facility/<str:org_tag>/<str:fac_tag>/",
                "facility-detail",
            ),
            ("facility/{org_tag}", "facility/<str:org_tag>/", "facility-list"),
            ("device/{org_tag}/{pk}/", "device/<str:org_tag>/<int:pk>/", "detail"),
            ("device/{org_tag}", "device/<str:org_tag>/", "list"),
        ],
    ),
)

proxy.setup(
    "aaactl",
    proxy.proxy_api(
        "aaactl",
        settings.AAACTL_URL,
        [
            (
                "billing/org/{org_tag}/start_trial/",
                "billing/<str:org_tag>/start_trial/",
                "start-trial",
            )
        ],
    ),
)

urlpatterns = proxy.urlpatterns(["aaactl", "devicectl"])

urlpatterns += [
    path(
        "autocomplete/device/port",
        django_peerctl.autocomplete.devicectl.devicectl_port.as_view(),
        name="devicectl port autocomplete",
    ),
]

urlpatterns += [
    path(
        "api/",
        include(
            ("django_peerctl.rest.urls.peerctl", "django_peerctl_api"),
            namespace="peerctl_api",
        ),
    ),
    path("tmpl/device_template/<str:template_id>/", device_template_base),
    path("tmpl/email_template/<str:template_id>/", email_template_base),
    path("<str:org_tag>/", views.view_instance, name="peerctl-home"),
    path("", views.org_redirect),
]
