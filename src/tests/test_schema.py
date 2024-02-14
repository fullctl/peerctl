import uuid

import pydantic

import django_peerctl.autopeer.schema as schema


def test_schema():
    session = schema.Session(
        peer_asn="1234568",
        peer_ip="127.0.0.1",
        peer_type="peer",
        location=schema.Location(
            id=f"pdb:ix:1",
            type="PUBLIC",
        ),
        md5="feb64ec1f94fd7834cf380069bd72f37",
        local_asn="12345",
        local_ip="127.0.0.2",
        status="pending",
        uuid=str(uuid.uuid4()),
    )
    assert session.peer_asn == "1234568"
    assert pydantic.version.VERSION == "2.5.3"
