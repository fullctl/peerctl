import confu.schema


class PeerSessionSchema(confu.schema.Schema):
    # TODO: need confu date attribute
    last_updown = confu.schema.Int()

    # TODO: limit values?
    session_state = confu.schema.Str()

    active = confu.schema.Int()
    received = confu.schema.Int()
    accepted = confu.schema.Int()
    damped = confu.schema.Int()
