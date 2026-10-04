Write a standalone Python 3 script, tools/wire_example.py, using only the
standard library. It builds and checks the "Back-to-Back Messages on the Wire
Example" in docs/protocol_blueprint.md #6. Do not edit the blueprint.

Constraints:
- Serialize every message with exactly the framing rule in blueprint #6:
  json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n".
  No indent, no other serializer, no sockets.
- Use only message types and fields defined in blueprint #2, with the types
  given there. Do not add or rename fields.
- The messages, in order, are what the server sends to Player_2 in the setup
  sequence diagram:
  1. LOBBY_WAIT: assigned_id "Player_2", players_connected 2
  2. GAME_START: opponent_name "alice", board_size 10, the 5-ship fleet
  3. FLEET_ACCEPTED: opponent_ready true (Player_2 placed second)
  4. STATE_UPDATE: the first update, so active_player "Player_1",
     last_shot null, shots_fired 0, ships_remaining 5 and 5,
     tracking_grid all ".", and your_board = the opponent_board from the
     GAME_OVER example in #2 with every "#" turned back into "S" and every
     "O" into "."
- Timestamps: 1727000003 for messages 1 and 2, 1727000015 for 3 and 4.
- Print the stream as one line with each 0x0A shown as the two characters \n,
  then a Markdown table with columns: Message, Size on the wire, First byte, Last byte
  with byte positions counted from 0.
- Check that the board has 17 ship cells, that each frame contains exactly
  one 0x0A and only at the end, that json.loads of each frame gives back the
  original message, and that the stream and table in the blueprint match the
  output byte for byte. Print every problem found and exit 1 if there are any.
- Keep it short and commented so I can explain every line.
