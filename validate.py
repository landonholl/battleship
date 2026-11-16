"""Shape checks for client messages: the MALFORMED rules.

Implements blueprint #1 (Message Envelope, Integer fields, Player ID
Validation), the payload tables in #2, and the MALFORMED row of #3. Only the
shape is checked here. Game rules (bounds, layout, version, room, phase,
turn) belong to game.py, and always run after these checks (#3).
"""

import re

# The four message types a client may send (blueprint #2).
CLIENT_TYPES = ("CONNECT", "PLACE_FLEET", "MOVE", "DISCONNECT")

# display_name: 1 to 20 lowercase letters a to z (blueprint #2, CONNECT).
NAME_PATTERN = re.compile(r"[a-z]{1,20}")


def is_int(value):
    """Integer fields (#1): bool, float, and str are never integers."""
    return type(value) is int


def envelope_ok(message):
    """#1: msg_type string, player_id string or null, payload object,
    timestamp integer. Unknown extra fields are ignored."""
    return (isinstance(message.get("msg_type"), str)
            and "player_id" in message
            and (message["player_id"] is None
                 or isinstance(message["player_id"], str))
            and isinstance(message.get("payload"), dict)
            and is_int(message.get("timestamp")))


def player_id_ok(message, conn):
    """#1, Player ID Validation: null only on CONNECT, and a non-null ID must
    be the one assigned to the socket the message arrived on."""
    player_id = message["player_id"]
    if message["msg_type"] == "CONNECT":
        return player_id is None
    return player_id is not None and player_id == conn.player_id


def connect_ok(payload):
    """#2, CONNECT: display_name a to z only, 1 to 20 long; version string."""
    name = payload.get("display_name")
    return (isinstance(name, str)
            and NAME_PATTERN.fullmatch(name) is not None
            and isinstance(payload.get("version"), str))


def ship_ok(ship):
    """#2, PLACE_FLEET: one entry of ships (the values are game rules)."""
    return (isinstance(ship, dict)
            and isinstance(ship.get("name"), str)
            and is_int(ship.get("row"))
            and is_int(ship.get("col"))
            and isinstance(ship.get("orientation"), str))


def place_fleet_ok(payload):
    """#2, PLACE_FLEET: ships is an array of ship objects."""
    ships = payload.get("ships")
    return isinstance(ships, list) and all(ship_ok(s) for s in ships)


def move_ok(payload):
    """#2, MOVE: row and col are integers (bounds are INVALID_COORD)."""
    return is_int(payload.get("row")) and is_int(payload.get("col"))


PAYLOAD_CHECKS = {
    "CONNECT": connect_ok,
    "PLACE_FLEET": place_fleet_ok,
    "MOVE": move_ok,
    "DISCONNECT": lambda payload: True,   # #2: empty payload, no fields
}


def validate(message, conn):
    """Return None if the message has the right shape, otherwise
    ("MALFORMED", rejected_type). rejected_type is the msg_type only when it
    is one of the four client types, so an unknown string is never echoed
    back (#2, ERROR)."""
    msg_type = message.get("msg_type")
    rejected_type = msg_type if msg_type in CLIENT_TYPES else None
    if (not envelope_ok(message)
            or rejected_type is None              # unknown or server-only
            or not player_id_ok(message, conn)
            or not PAYLOAD_CHECKS[msg_type](message["payload"])):
        return ("MALFORMED", rejected_type)
    return None
