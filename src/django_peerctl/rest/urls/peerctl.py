from django.urls import include, path

import django_peerctl.rest.route.peerctl
import django_peerctl.rest.views.peerctl

urlpatterns = [
    path("", include(django_peerctl.rest.route.peerctl.router.urls)),
]
