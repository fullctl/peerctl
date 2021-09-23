from django.apps import AppConfig


class DjangoPeerctlConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_peerctl"

    def ready(self):
        import django_peerctl.signals  # noqa
