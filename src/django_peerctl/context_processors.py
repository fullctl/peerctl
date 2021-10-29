from django.conf import settings as djsettings


def settings(request):
    """
    add some commonly used setting variables to all template
    contexts
    """
    return {
        "release_env": djsettings.RELEASE_ENV,
        "settings": {
            "version": djsettings.PACKAGE_VERSION,
            "content": {"header_message": djsettings.PEERCTL_HEADER_MESSAGE},
            "emails": {
                "noreply": djsettings.NO_REPLY_EMAIL,
                "support": djsettings.DEFAULT_FROM_EMAIL,
            },
        },
    }
