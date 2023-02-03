class PeerctlException(Exception):
    """peerctl base exception"""


class ReferenceNotFoundError(PeerctlException, LookupError):
    """Reference query returned a 404 Not Found"""

    def __init__(self, tag, pk, source):
        msg = f"reference missing {source}:{tag}/{pk}"
        super().__init__(msg)


class ReferenceSourceInvalid(PeerctlException, ValueError):
    pass


class TemplateRenderError(PeerctlException, ValueError):
    """Error that gets raised when template render fails"""

    def __init__(self, tmpl_exc):
        msg = f"Could not render template: {tmpl_exc}"
        super().__init__(msg)


class PolicyMissingError(PeerctlException):
    def __init__(self, obj):
        msg = (
            "No policy could be obtained for {}, either directly "
            "or through the policy hierarchy. You can set a global policy "
            "that will be applied in such cases.".format(obj)
        )
        super().__init__(msg)


class UsageLimitError(PeerctlException):
    pass


class ASNClaimed(PeerctlException):
    pass
