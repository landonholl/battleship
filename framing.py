"""Message framing shared by the server and the client.

Implements blueprint #1 (Message Envelope) and #6 (Message Framing,
The Receiver Algorithm). Both programs build, encode, and split messages
with these functions, so the two sides can never disagree on the wire format.
"""

import json
import time

# 64 KB cap on an unfinished message in a receive buffer (FRAME_TOO_LARGE,
# blueprint #6 step 6) and on a server send buffer (#5, Send Buffer Limit).
MAX_BUFFER = 65536


def build_message(msg_type, player_id, payload):
    """Return the 4 field envelope (blueprint #1). Nothing else is added."""
    return {
        "msg_type": msg_type,
        "player_id": player_id,
        "payload": payload,
        "timestamp": int(time.time()),  # integer Unix seconds
    }


def encode_message(message):
    """The framing rule (blueprint #6): compact JSON, UTF-8, one 0x0A."""
    return json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"


class FrameBuffer:
    """One connection's receive buffer (blueprint #6, The Receiver Algorithm).

    The server keeps one on each connection; the client keeps one for its
    single socket.
    """

    def __init__(self):
        self.buf = bytearray()   # bytes received but not yet split off
        self.too_large = False   # set when the unfinished message passes 64 KB

    def feed(self, data):
        """Add one recv() worth of bytes (steps 4 to 6).

        Return every complete message in arrival order: a dict, or None for
        a MALFORMED frame (not UTF-8, not JSON, or not a JSON object).
        """
        self.buf += data                          # step 4: add to the end
        messages = []
        while b"\n" in self.buf:                  # step 5: any 0x0A left?
            end = self.buf.index(b"\n")           # first 0x0A
            frame = bytes(self.buf[:end])         # the bytes before it
            del self.buf[:end + 1]                # remove them and the 0x0A
            try:
                msg = json.loads(frame.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
                msg = None                        # not UTF-8 or not JSON
            if not isinstance(msg, dict):
                msg = None                        # valid JSON, not an object
            messages.append(msg)
        if len(self.buf) > MAX_BUFFER:            # step 6: leftover bytes only
            self.too_large = True
        return messages
