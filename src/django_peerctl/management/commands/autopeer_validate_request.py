from fullctl.django.management.commands.base import CommandInterface

from django_peerctl.autopeer import request_valid_for_schema


class Command(CommandInterface):
    """
    Validates the request against AutoPeer API schema.

    devicectl needs to be running.
    """

    def add_arguments(self, parser):
        super(self).add_arguments(parser)

        parser.add_argument(
            "--version", default="1.0", type=str, help="API schema version"
        )
        parser.add_argument("method", type=str, help="request method (GET/POST)")
        parser.add_argument("url", type=str, help="URL with query")

    def run(self, *args, **kwargs):
        version = kwargs["version"]
        method = kwargs["method"]
        url = kwargs["url"]
        print(f"running with args: version: {version}, method: {method}, url: {url}")

        if request_valid_for_schema(method, url, version=version):
            print(f"This request is valid according to AutoPeer schema v{version}.")
        else:
            print(f"This request is NOT valid according to AutoPeer schema v{version}.")
