"""
email related functions and utilities
"""


from django.core.mail.message import EmailMultiAlternatives
from django.conf import settings


def send_mail(subject, body, from_address, to_addresses, reply_to=None, **kwargs):

    """
    send an email

    Arguments:
        - subject(str): email subject
        - body(str): email body
        - from_address(str): send from this address
        - to_addresses(list): list of recipient addresses

    Keyword Arguments:
        - reply_to(str): set reply to address to this
        - debug_address(str): if specified and settings.DEBUG_EMAIL is True
            override recipients to this address
        - prefix (bool): if true prefix subject with release env
    """

    if kwargs.get("prefix"):
        subject = f"{settings.EMAIL_SUBJECT_PREFIX} {subject}"
    debug = getattr(settings, "DEBUG_EMAIL", True)
    if reply_to:
        headers = {"Reply-To": reply_to}
    else:
        headers = {}

    if debug:
        to_addresses_original = to_addresses
        to_addresses = [kwargs.get("debug_address", getattr(settings, "SERVER_EMAIL"))]
        body = (
            "!!! Peerctl is currently running in early testing mode, "
            "as such this notification is sent to you ("
            "{}) instead of the actual recipient({})\n\n{}".format(
                ",".join(to_addresses), ",".join(to_addresses_original), body
            )
        )

        print(subject)
        print(headers)
        print(from_address)
        print(to_addresses)
        print(body)
        print(kwargs)

    body = f"{body}\n\nSent with Peerctl"

    mail = EmailMultiAlternatives(
        subject, body, from_address, to_addresses, headers=headers
    )
    mail.send()

    return {
        "to": to_addresses,
        "from": from_address,
        "subject": subject,
        "body": body,
        "headers": headers,
        "debug": debug,
    }


def send_mail_from_default(subject, body, to_addresses, reply_to=None, **kwargs):
    return send_mail(
        subject,
        body,
        getattr(settings, "DEFAULT_FROM_EMAIL"),
        to_addresses,
        reply_to=reply_to,
        **kwargs,
    )


def bulk_email_recipients(net, recipients=None, role="policy", **kwargs):
    """
    Returns email addresses in a list for bulk email operations

    Arguments:
        net <Network>
        recipients <str>: can be any of the following classifiers:
            - "peers" : all peers for the network
            - "peers_at_ix" : all pers for the network at ix, requires `ix_id`
                to be set in kwargs

    Keyword Arguments:
        - ix_id<int>: used to specify the exchange when recipients is `peers_at_ix`
        - role<str=policy>

    Returns:
        - list of email addresses
    """
    if recipients == "peers":
        return net.get_peer_contacts(role=role)
    elif recipients.find("peers_at_ix:") == 0:
        _, ix_id = tuple(recipients.split(":"))
        return net.get_peer_contacts(ix_id, role=role)
    elif recipients == "peers_at_ix":
        ix_id = kwargs.get("ix")
        if not ix_id:
            raise ValueError("No exchange specified")
        return net.get_peer_contacts(ix_id, role=role)
    else:
        raise ValueError(f"Invalid recipient specification: {recipients}")
