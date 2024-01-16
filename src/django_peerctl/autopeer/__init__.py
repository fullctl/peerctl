from django.conf import settings

__all__ = [
    "autopeer_url",
]


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
