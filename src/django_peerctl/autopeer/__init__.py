import requests
from django.conf import settings
from django.contrib.staticfiles import finders
from openapi_core import Spec, validate_request
from openapi_core.contrib.requests import RequestsOpenAPIRequest
from requests import PreparedRequest

__all__ = [
    "autopeer_url",
    "request_valid_for_schema",
    "validate_and_send",
    "AutoPeerBaseException",
    "AutoPeerRequestNotValid",
]


class AutoPeerBaseException(Exception):
    pass


class AutoPeerRequestNotValid(AutoPeerBaseException):
    pass


def autopeer_url(asn):
    """
    checks if the target network is autopeer enabled and returns its autopeer
    api url.

    Will return None if disabled or no url is present
    """

    if not settings.AUTOPEER_ENABLED:
        # autopeer is disabled
        return None

    # TODO: this should query autopeer-registry once it exsts
    return settings.AUTOPEER_ENABLED_NETWORKS.get(asn, {}).get("url")


def request_is_valid(request: PreparedRequest, schema_version="1.0"):
    """
    validate if the request matches autopeer schema
    """
    path = finders.find(f"autopeer/{schema_version}/openapi.yaml")
    try:
        spec = Spec.from_file_path(path)
    except FileNotFoundError:
        settings.print_debug(
            f"Cannot find and open autopeer schema v{schema_version} at '{path}'"
        )
        return False  # TODO decide the default result when schema isn't found

    openapi_request = RequestsOpenAPIRequest(request)

    try:
        validate_request(openapi_request, spec=spec)
        return True
    except Exception as exc:
        settings.print_debug(str(exc))
        return False


def validate_and_send(method: str, url: str, params=None, data=None, json=None):
    """
    Wrapper for `requests` operations. Validates the request according to AutoPeer schema
    and sends the request if it's valid. Returns request response.

    Raises an exception otherwise.
    """
    req = requests.Request(method, url, data=data, params=params, json=json)
    prep_req = req.prepare()

    if not request_is_valid(prep_req):
        # TODO fail, log error and quit
        raise AutoPeerRequestNotValid(
            "Request does not match the schema, see the log for details"
        )

    s = requests.Session()
    return s.send(prep_req)
