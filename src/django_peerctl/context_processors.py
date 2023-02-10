from django.conf import settings


def conf(request):
    """
    add some commonly used setting variables to all template
    contexts
    """
    return {
        "settings": {
            "emails": {
                "noreply": settings.NO_REPLY_EMAIL,
                "support": settings.DEFAULT_FROM_EMAIL,
                "peer_request_from": settings.PEER_REQUEST_FROM_EMAIL,
            },
            "peeringdb": {
                "url": settings.PEERINGDB_URL,
            }
        },
    }
