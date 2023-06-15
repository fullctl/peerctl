import time
import uuid

import fullctl.service_bridge.pdbctl as pdbctl
import fullctl.service_bridge.sot as sot

import django_peerctl.autopeer.schema as schema
from django_peerctl.autopeer import autopeer_url, validate_and_send
from django_peerctl.models.peerctl import (
    Network,
    PeerPort,
    PeerRequest,
    PeerSession,
    PortInfo,
)
from django_peerctl.peer_session_workflow import PeerSessionWorkflow

__all__ = [
    "AutopeerWorkflow",
]


class AutopeerWorkflow(PeerSessionWorkflow):

    """
    Peer Session setup workflow using autopeer
    """

    cc = False
    test_mode = False

    def __init__(self, my_asn, their_asn, task, peer_request=None):
        self.net = Network.objects.get(asn=my_asn)
        self.other_net = pdbctl.Network().first(asn=their_asn)
        self.to_asn = their_asn
        self.asn = my_asn
        self.locations = []
        self.task = task
        self.peer_request = peer_request

        if not self.autopeer_url:
            raise ValueError(f"Autopeer is not enabled for this ASN: AS{their_asn}")

    @property
    def autopeer_url(self):
        """
        checks if the target network is autopeer enabled and returns its autopeer
        api url.

        Will return None if disabled or no url is present
        """
        return autopeer_url(self.to_asn)

    def request(self, *args, **kwargs):
        if not self.peer_request:
            self.peer_request = PeerRequest.objects.create(
                net=self.net, peer_asn=self.to_asn, task=self.task, type="autopeer"
            )

        locations = self.request_list_locations()

        peerctl_sessions, autopeer_sessions = self.request_add_sessions(locations)

        print("request", peerctl_sessions)

        self.peer_request.status = "completed"
        self.peer_request.save()

        for location in self.peer_request.locations.all():
            # TODO: mockup for now just assume session for location completed successfully
            location.status = "completed"
            location.save()

        return {
            "autopeer_sessions": [
                autopeer_session.dict() for autopeer_session in autopeer_sessions
            ],
            "peerctl_sessions": [
                (peerctl_session[0].id, peerctl_session[1])
                for peerctl_session in peerctl_sessions
            ],
            "locations": list(
                {peerctl_session[1] for peerctl_session in peerctl_sessions}
            ),
        }

    def progress(self, *args, **kwargs):
        return

    def configure(self, *args, **kwargs):
        return

    def finalize(self, *args, **kwargs):
        return

    @property
    def portinfos(self):
        if hasattr(self, "_portinfos"):
            return self._portinfos

        self._portinfos = (
            PortInfo.objects.filter(net__asn=self.asn)
            .exclude(port__isnull=True)
            .exclude(ref_id__isnull=True)
        )
        return self._portinfos

    def request_list_locations(self, *args, **kwargs):
        """
        Autopeer request list locations, list of exchanges
        in the format of: pdb:ix:{id}

        Will return a list of peeringdb exchange int ids
        """

        locations = []

        _locations = schema.Locations(
            **validate_and_send("get", f"{self.autopeer_url}/list_locations?asn={self.asn}").json()
        )

        for location in _locations.items:
            source, typ, ix_id = location.id.split(":")

            # currently we only process pdb:ix:{id}

            if source != "pdb" or typ != "ix":
                continue

            locations.append(int(ix_id))

        print("request_locations", locations)

        return locations

    def request_add_sessions(self, locations, *args, **kwargs):
        """
        Autopeer request add sessions

        locations: list of peeringdb exchange int ids
        """

        # set up peerctl side sessions

        members = sot.InternetExchangeMember().objects(asn=self.to_asn, join=["ix"])
        sessions = []
        autopeer_sessions = []

        for ix_id in locations:
            sessions.extend(self._ensure_peerctl_sessions(members, ix_id))

        # request add session from remote autopeer api

        for peerctl_session, pdb_ix_id in sessions:
            autopeer_session4 = None
            autopeer_session6 = None

            if peerctl_session.ip4:
                autopeer_session4 = schema.Session(
                    peer_asn=peerctl_session.peer_port.peer_net.net.asn,
                    peer_ip=peerctl_session.ip4.split("/")[0],
                    peer_type=peerctl_session.peer_session_type,
                    location=schema.Location(
                        id=f"pdb:ix:{pdb_ix_id}",
                        type="PUBLIC",
                    ),
                    # md5 = peerctl_session.peer_port.peer_net.md5,
                    local_asn=peerctl_session.peer_port.peer_net.peer.asn,
                    local_ip=peerctl_session.peer_ip4.split("/")[0],
                    status="pending",
                    uuid=str(uuid.uuid4()),
                )

            if peerctl_session.ip6:
                autopeer_session6 = schema.Session(
                    peer_asn=peerctl_session.peer_port.peer_net.net.asn,
                    peer_ip=peerctl_session.ip6.split("/")[0],
                    peer_type=peerctl_session.peer_session_type,
                    location=schema.Location(
                        id=f"pdb:ix:{pdb_ix_id}",
                        type="PUBLIC",
                    ),
                    # md5 = peerctl_session.peer_port.peer_net.md5,
                    local_asn=peerctl_session.peer_port.peer_net.peer.asn,
                    local_ip=peerctl_session.peer_ip6.split("/")[0],
                    status="ok",
                    uuid=str(uuid.uuid4()),
                )

            if autopeer_session4:
                autopeer_sessions.append(autopeer_session4)

            if autopeer_session6:
                autopeer_sessions.append(autopeer_session6)

        response = validate_and_send("post",
            f"{self.autopeer_url}/add_sessions",
            json=[autopeer_session.dict() for autopeer_session in autopeer_sessions],
        )

        request_id = response.json()["requestId"]

        if response.status_code != 200:
            raise ValueError(f"Error adding sessions: {response.json()}")

        # request /get_status for each session until OK
        loops = 0
        while True:
            session_status = self.request_get_status(request_id)

            if session_status:
                break

            # high sleep time to simulate long running request
            time.sleep(3)
            loops += 1
            if loops > 300:
                raise Exception("never got session status")

        return sessions, autopeer_sessions

    def request_get_status(self, request_id, *args, **kwargs):
        """
        Autopeer request get status
        """

        # TODO: mockup for now, just assume configured and return

        url = f"{self.autopeer_url}/get_status?request_id={request_id}&asn={self.asn}"
        print("request_get_status", url)

        response = validate_and_send("get", url)

        print(response.json())

        return response.json()["sessions"]

    def _ensure_peerctl_sessions(self, members, pdb_ix_id):
        sessions = []

        for member in members:
            if member.source == "ixctl" and member.pdb_ix_id != pdb_ix_id:
                continue

            if member.source == "pdbctl" and member.ix_id != pdb_ix_id:
                continue

            _sessions = self._ensure_peerctl_member_sessions(member) or []
            for _session in _sessions:
                self.peer_request.add_pdb_location(pdb_ix_id)
                sessions.append((_session, pdb_ix_id))

        return sessions

    def _ensure_peerctl_member_sessions(self, member):
        sessions = []

        for portinfo in self.portinfos:
            ref_source, ref_ix_id = portinfo.ref_ix_id.split(":")

            print(
                "REF SOURCE",
                portinfo.ref.ipaddr4,
                member.ipaddr4,
                ref_ix_id,
                member.ix_id,
            )

            if int(ref_ix_id) != member.ix_id:
                continue

            port = portinfo.port.object
            if not port:
                continue

            print("ensuring session", port.port_info_object.ref.ipaddr4, member.ipaddr4)

            peer_port = PeerPort.get_or_create_from_members(
                port.port_info_object.ref, member
            )

            peer_session = PeerSession.get_or_create(
                port, peer_port, create_status="ok"
            )

            if peer_session.status != "ok":
                peer_session.status = "ok"
                peer_session.save()

            sessions.append(peer_session)

        return sessions
