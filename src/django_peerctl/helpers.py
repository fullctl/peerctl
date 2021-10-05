from django_peerctl.exceptions import (
    PolicyMissingError,
)

from fullctl.service_bridge.pdbctl import (
    NetworkContact,
)


def get_peer_contact_email(pdb_net):
    poc = NetworkContact().first(asn=pdb_net.asn, role="Policy", require_email=True)
    if poc:
        return poc.email
    return None


def get_net_from_contact_email(email):
    """
    Returns Network object contains the Network contact with
    the specified email (first match)
    """
    poc = NetworkContact().first(email=email)
    if poc:
        return poc.net
    return None


def get_best_policy(obj, version, raise_error=True):
    field_name = f"policy{int(version)}"
    if not hasattr(obj, field_name):
        raise TypeError(f"{obj.__class__} does not implement a policy")
    if getattr(obj, field_name, None):
        return getattr(obj, field_name)
    policy = None
    try:
        for policy_parent in obj.policy_parents:
            policy = get_best_policy(policy_parent, version, raise_error=False)
            if policy:
                return policy
    except PolicyMissingError:
        if raise_error:
            raise
    finally:
        if raise_error and not policy:
            raise PolicyMissingError(obj)
        return policy
