import fullctl.django.rest.urls.service_bridge_proxy as service_bridge
from django.conf import settings
from django.urls import include, path

import django_peerctl.views as views
from django_peerctl.legacy.views import device_template_base, email_template_base

import fullctl.django.rest.urls.service_bridge_proxy as proxy
from fullctl.django.views.template import TemplateFileView

proxy.setup("devicectl", proxy.proxy_api(
    "devicectl",
    settings.DEVICECTL_URL,
    [
        ("device/{org_tag}/{pk}/", "device/<str:org_tag>/{pk}", "detail"),
        ("device/{org_tag}", "device/<str:org_tag>/", "list"),
    ],
))

urlpatterns = proxy.urlpatterns(["devicectl"])


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
