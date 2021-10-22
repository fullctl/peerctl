import fullctl.django.rest.urls.service_bridge_proxy as service_bridge
from django.urls import include, path

import django_peerctl.views as views
from django_peerctl.legacy.views import devicetmpl_base, emltmpl_base

urlpatterns = service_bridge.urlpatterns(["aaactl", "devicectl"])

urlpatterns += [
    path(
        "api/",
        include(
            ("django_peerctl.rest.urls.peerctl", "django_peerctl_api"),
            namespace="peerctl_api",
        ),
    ),
    path("tmpl/devicetmpl/<str:template_id>/", devicetmpl_base),
    path("tmpl/emltmpl/<str:template_id>/", emltmpl_base),
    path("<str:org_tag>/", views.view_instance, name="peerctl-home"),
    path("", views.org_redirect),
]
