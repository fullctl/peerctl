from django.contrib import admin
from django.urls import include, path

# import django_peerctl.urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("social_django.urls", namespace="social")),
    path("", include("fullctl.django.urls")),
    path("", include("django_peerctl.urls")),
]

handler500 = "fullctl.django.views.handle_error_500"
handler404 = "fullctl.django.views.handle_error_404"
handler403 = "fullctl.django.views.handle_error_403"
handler401 = "fullctl.django.views.handle_error_401"
handler400 = "fullctl.django.views.handle_error_400"
