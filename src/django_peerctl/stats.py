from django.contrib.auth import get_user_model

from django_peerctl.exceptions import ReferenceNotFoundError
from django_peerctl.models import InternetExchange, PeerNetwork, PeerSession


def count_peerses():

    """
    count peersessions and return a map with the following statistics:

        - all: all peer sessions
        - ip4: peer sessions where both sides have ip4 set
        - ip6: peer sessions where both sides have ip6 set

    """

    qset = PeerSession.objects.filter(status="ok").select_related(
        "peerport__portinfo", "port__portinfo"
    )
    count = 0
    count_ip4 = 0
    count_ip6 = 0
    for peerses in qset:
        if peerses.peerport.portinfo.ipaddr6 and peerses.port.portinfo.ipaddr6:
            count_ip6 += 1
        if peerses.peerport.portinfo.ipaddr4 and peerses.port.portinfo.ipaddr4:
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

    for peernet in qset:
        try:
            scope = peernet.net.pdb.info_scope
            typ = peernet.net.pdb.info_type
            if scope not in peers_by_scope:
                peers_by_scope[scope] = []
            if typ not in peers_by_type:
                peers_by_type[typ] = []
            peers_by_scope[scope].append(peernet.net.asn)
            peers_by_type[typ].append(peernet.net.asn)
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
        "peerses": count_peerses(),
    }
