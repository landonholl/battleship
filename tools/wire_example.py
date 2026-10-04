"""Build and check the back-to-back wire example in docs/protocol_blueprint.md (#6).

Serializes the four messages the server sends to Player_2 during game setup,
using the exact call from the framing rule, then prints the raw stream and the
byte table and checks that the copy in the blueprint matches byte for byte.

Run from the repo root:  python tools/wire_example.py
Exits 0 if the blueprint matches, 1 if it does not. Never edits any file.
"""

import json
import re
import sys
from pathlib import Path

BLUEPRINT = Path(__file__).resolve().parent.parent / "docs" / "protocol_blueprint.md"
SECTION = "### Back-to-Back Messages on the Wire Example"


def frame(message):
    """Framing rule (blueprint #6): compact JSON, UTF-8, then exactly one 0x0A."""
    return json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"


FLEET = [
    {"name": "Carrier", "length": 5},
    {"name": "Battleship", "length": 4},
    {"name": "Cruiser", "length": 3},
    {"name": "Submarine", "length": 3},
    {"name": "Destroyer", "length": 2},
]

# Player_2's fleet: the opponent_board from the GAME_OVER example in blueprint #2,
# before any shots (every '#' back to 'S', every 'O' back to '.').
PLAYER_2_BOARD = [
    ".........S",
    "......SS.S",
    ".........S",
    ".........S",
    "....SSS...",
    "..........",
    ".......S..",
    ".......S..",
    ".......S..",
    "SSSSS.....",
]

# Everything the server sends to Player_2 in the setup sequence diagram, in order.
MESSAGES = [
    # Written together right after Player_2's CONNECT is accepted.
    {"msg_type": "LOBBY_WAIT", "player_id": "SERVER",
     "payload": {"assigned_id": "Player_2", "players_connected": 2},
     "timestamp": 1727000003},
    {"msg_type": "GAME_START", "player_id": "SERVER",
     "payload": {"opponent_name": "alice", "board_size": 10, "fleet": FLEET},
     "timestamp": 1727000003},
    # Written together right after Player_2's fleet (the 2nd one) is accepted.
    {"msg_type": "FLEET_ACCEPTED", "player_id": "SERVER",
     "payload": {"opponent_ready": True},
     "timestamp": 1727000015},
    {"msg_type": "STATE_UPDATE", "player_id": "SERVER",
     "payload": {"active_player": "Player_1",
                 "your_board": PLAYER_2_BOARD,
                 "tracking_grid": [".........."] * 10,
                 "last_shot": None,
                 "ships_remaining": {"Player_1": 5, "Player_2": 5},
                 "shots_fired": 0},
     "timestamp": 1727000015},
]


def stream_as_text(frames):
    """The stream as the blueprint prints it: each 0x0A byte shown as the two characters \\n."""
    return "".join(f[:-1].decode("utf-8") + "\\n" for f in frames)


def byte_table(frames):
    """One Markdown table row per message: size, first byte, last byte (the 0x0A)."""
    rows, start = [], 0
    for number, (message, f) in enumerate(zip(MESSAGES, frames), 1):
        end = start + len(f) - 1
        rows.append(f"| {number} | `{message['msg_type']}` | {len(f)} bytes | {start} | {end} |")
        start = end + 1
    return rows


def main():
    frames = [frame(m) for m in MESSAGES]
    problems = []

    # The 17 ship cells of the standard fleet (5 + 4 + 3 + 3 + 2).
    if sum(row.count("S") for row in PLAYER_2_BOARD) != 17:
        problems.append("Player_2's board does not have 17 ship cells")

    for message, f in zip(MESSAGES, frames):
        # Framing rule: the only 0x0A in a frame is the one at the end.
        if f.count(b"\n") != 1 or not f.endswith(b"\n"):
            problems.append(f"{message['msg_type']}: 0x0A is not only at the end")
        # What a receiver does: strip the 0x0A and parse. It must give back the original.
        if json.loads(f[:-1].decode("utf-8")) != message:
            problems.append(f"{message['msg_type']}: does not parse back to the original")

    text = stream_as_text(frames)
    rows = byte_table(frames)
    print(text)
    print()
    print("\n".join(rows))
    print(f"\ntotal: {sum(len(f) for f in frames)} bytes")

    # Compare with the copy in the blueprint.
    section = BLUEPRINT.read_text(encoding="utf-8").split(SECTION, 1)[1]
    # The raw stream is the text block that starts with a message; the readable
    # view and the byte close-up start with "bytes" and "byte:" instead.
    blocks = re.findall(r"```text\n(.*?)\n```", section, re.S)
    doc_text = next((b for b in blocks if b.startswith('{"msg_type"')), "")
    doc_rows = [line for line in section.splitlines() if re.match(r"\| \d+ \| `", line)]
    if doc_text != text:
        problems.append("the stream in the blueprint does not match")
    if doc_rows != rows:
        problems.append("the byte table in the blueprint does not match")

    if problems:
        print("\nPROBLEMS:\n- " + "\n- ".join(problems))
        sys.exit(1)
    print("blueprint matches: stream and table are byte for byte correct")


if __name__ == "__main__":
    main()
