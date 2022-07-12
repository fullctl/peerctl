from django.contrib.auth import get_user_model

from django_peerctl.exceptions import ReferenceNotFoundError
from django_peerctl.models import InternetExchange, PeerNetwork, PeerSession


def count_peer_session():

    """
    count peer_sessionsions and return a map with the following statistics:

        - all: all peer sessions
        - ip4: peer sessions where both sides have ip4 set
        - ip6: peer sessions where both sides have ip6 set

    """

    qset = PeerSession.objects.filter(status="ok").select_related(
        "peer_port__port_info", "port__port_info"
    )
    count = 0
    count_ip4 = 0
    count_ip6 = 0
    for peer_session in qset:
        if peer_session.peer_port.port_info.ipaddr6 and peer_session.port.port_info.ipaddr6:
            count_ip6 += 1
        if peer_session.peer_port.port_info.ipaddr4 and peer_session.port.port_info.ipaddr4:
            count_ip4 += 1
        count += 1
    return {"all": count, "ip4": count_ip4, "ip6": count_ip6}


def count_peers():
    """
    count peer networks and return a map with the following statistics

        - all: all peer networks
        - scope: counts per scope
        - typ: counts per type
    """

    peers_by_scope = {}
    peers_by_type = {}
    qset = PeerNetwork.objects.filter(status="ok")

    for peer_net in qset:
        try:
            scope = peer_net.net.pdb.info_scope
            typ = peer_net.net.pdb.info_type
            if scope not in peers_by_scope:
                peers_by_scope[scope] = []
            if typ not in peers_by_type:
                peers_by_type[typ] = []
            peers_by_scope[scope].append(peer_net.net.asn)
            peers_by_type[typ].append(peer_net.net.asn)
        except ReferenceNotFoundError:
            pass

    sort = lambda x: x[0]

    return {
        "all": qset.count(),
        "scope": sorted(
            ((scope, len(set(asns))) for scope, asns in peers_by_scope.items()),
            key=sort,
        ),
        "type": sorted(
            ((typ, len(set(asns))) for typ, asns in peers_by_type.items()), key=sort
        ),
    }


def site_stats():
    return {
        "user": get_user_model().objects.filter(is_active=True).count(),
        "ix": InternetExchange.objects.filter(status="ok").count(),
        "peers": count_peers(),
        "peer_session": count_peer_session(),
    }
