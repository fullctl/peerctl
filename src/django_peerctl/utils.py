from django_peerctl.models import Network


def get_network(asn):
    return Network.get_or_create(asn)
