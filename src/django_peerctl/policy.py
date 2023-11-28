from jinja2 import Environment, TemplateSyntaxError, UndefinedError
from pydantic import BaseModel, Field

class VariableContextPeer(BaseModel):
    asn: int = 0

class VariableContext(BaseModel):
    peer: VariableContextPeer = Field(default_factory=VariableContextPeer)


def render_policy_variable(
    template_string: str,
    jinja_env: Environment = None,
    raise_errors: bool = False,
    **kwargs
):
    """
    Renders a policy variable.

    This uses jinja2 to render the template string. The context is populated with
    the following variables:

    - peer_asn: The peer's ASN
    - peer_maxprefix4: The peer's maxprefix for IPv4
    - peer_maxprefix6: The peer's maxprefix for IPv6
    - peer_ip4: The peer's IPv4 address
    - peer_ip6: The peer's IPv6 address

    If a session is passed, the context is populated with the session's
    peer_port and peer_ip4/peer_ip6. Otherwise the context is populated
    with the kwargs.

    If a jinja_env is passed, it is used to render the template. Otherwise
    a new jinja2.Environment is created.

    If the template_string does not contain any jinja2 variables, the
    template_string is returned as-is.

    Example value for template_string:

        as{{peer.asn}}-in-v4
    """

    if not template_string:
        return template_string

    context = VariableContext(**kwargs)

    if jinja_env is None:
        jinja_env = Environment()

    # Check if the string is a Jinja2 template
    if "{{" in template_string:
        template = jinja_env.from_string(template_string)
        try:
            return template.render(context)
        except (TemplateSyntaxError, UndefinedError):
            if raise_errors:
                raise
            # TODO: do we log template syntax errors, unsure since
            # those are user input errors
            # TODO: how do we communicate the issue back to the user
            # For now just return the original unformatted string
            return template_string
    return template_string
