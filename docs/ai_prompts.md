



You are helping write docs/protocol_blueprint.md for a two-player console
Battleship game over TCP (Python, single-threaded `selectors` event loop,
non-blocking sockets). The blueprint is the single source of truth. Read all of
it before writing, especially #3 (Error Codes), #5 (Game End and Cleanup) and
#6 (Message Framing, including the fragmentation, coalescing and "Both at Once"
examples).

Task: write the next subsection of #6, titled "### The Receiver Algorithm". It
explains how a receiver pulls complete messages out of a TCP byte stream. Do not
edit any file. Return only the Markdown for the new subsection.

It must contain:
1. Numbered steps a reader can follow without reading code.
2. A short Python sketch (standard library only, about 40 lines) with a
   `FrameBuffer` class that owns one connection's receive buffer and a
   `feed(data)` method that returns the complete messages in arrival order,
   plus a few lines showing how a read handler calls `recv()` and `feed()`.
3. One or two sentences tying it back to the fragmentation, coalescing and
   "Both at Once" examples above it.

Rules the algorithm must follow, exactly as the blueprint defines them:
- Every connection has its own receive buffer. The server keeps it on the
  selector key's `data`. The client uses the same algorithm.
- On read readiness, call `recv(4096)` once and append the bytes to the end of
  the buffer.
- `recv()` returning `b""` is EOF: the peer closed (blueprint #5 row 3). Do not
  parse anything else from that connection; leftover partial bytes are thrown
  away. Do not describe exception handling in detail; the termination section
  covers it. Just say ConnectionResetError and ConnectionAbortedError from
  recv(), or BrokenPipeError from a later write, mean the player is lost
  (#5 row 4).
- Split on the byte 0x0A BEFORE decoding. A message is complete only when its
  0x0A has arrived. Never try parsing to guess if bytes form a complete message.
- Loop: while the buffer contains 0x0A, take the bytes before the first 0x0A,
  remove them and the 0x0A from the buffer, then decode as UTF-8 and parse with
  json.loads. Keep looping until no 0x0A is left. Never handle only one message
  per recv().
- A frame that is not valid UTF-8, not valid JSON, or not a JSON object is
  rejected with ERROR (MALFORMED) and `rejected_type: null`. An empty frame
  (two 0x0A in a row) is not a special case: it fails json.loads and is
  MALFORMED. A bad frame never desyncs the stream, because the next frame
  starts right after its 0x0A. Shape and game-rule checks (#1, #3) happen after
  this, in the dispatcher, and are not part of this algorithm.
- After the loop, check only the bytes left over (the unfinished message). If
  more than 64 KB (65,536 bytes) has arrived without a 0x0A, the server sends
  ERROR (FRAME_TOO_LARGE) and closes the connection (#5 row 6). Do not apply
  the cap to complete messages that were already split off.
- If handling a message closes the connection or ends the game (#5 "What each
  machine does", step 2), stop: any remaining messages from that recv() are
  discarded.
- Messages from one recv() are handled in order, all in the same event-loop
  step.

Do not:
- add message types, fields, error codes, or limits the blueprint does not
  define
- use threads, blocking calls, socket timeouts, sendall, or any third-party
  library
- parse with a regex, read a length prefix, or split on anything but 0x0A

Style: match the blueprint (short plain sentences, tables or bullets where they
help). Refer to sections as "#5", never with the section sign. No em dashes.
Keep the Python short and commented so the author can explain every line.



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
