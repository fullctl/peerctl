from django.conf import settings
from django.core.management.base import BaseCommand
from peeringdb import initialize_backend, resource
from peeringdb.client import Client

# from peeringdb import get_backend


class Command(BaseCommand):

    """
    Pull peeringdb updates
    """

    def add_arguments(self, parser):
        parser.add_argument("--pdburl", default="https://www.peeringdb.com/api")

    def handle(self, *args, **kwargs):
        self.pdburl = kwargs.get("pdburl")
        self.sync()

    def sync(self):
        settings.USE_TZ = False
        config = {
            "sync": {
                "url": self.pdburl,
                "user": "",
                "password": "",
                "strip_tz": 1,
                "timeout": 0,
                "only": [],
            },
            "orm": {
                "database": settings.DATABASES["default"],
                "backend": "django_peeringdb",
                "migrate": True,
            },
        }

        initialize_backend("django_peeringdb", **config["orm"])
        # b = get_backend()

        client = Client(config, **config)
        print("Syncing from", config["sync"]["url"])
        client.update_all(resource.all_resources())
