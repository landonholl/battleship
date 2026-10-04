# AI Prompting & Constraint Strategy

**Course:** CS 457
**Written by:** Landon Holland

---

Claude (Claude Code in the IDE) is the only AI tool used on this project (SOW #4). This document shows how it is kept to the specification instead of producing generic socket code: a standing system prompt that is in force for every session, narrow prompts for each component, and checks that hold the output to the blueprint.

## 1. Standing System Prompt

Claude Code loads a project instruction file, `CLAUDE.md`, at the start of every session, so these rules apply before any task is given. `CLAUDE.md` is kept out of the repository (it lives in a local, gitignored folder), so its prompt is reproduced here word for word.

What it does:

- **Pins Claude to the blueprint.** The blueprint is the single source of truth, Claude must name the sections a task implements, and it may never change the spec to fit its code.
- **Carries the schema.** It lists the envelope, every message type with its direction, every error code, and every FSM state, each with the blueprint section to read for the details. Anything not on these lists is not allowed.
- **Rules out generic boilerplate by name.** No threads, blocking calls, socket timeouts, `sendall`, `asyncio`, third-party libraries, or other framing. Every function must map to a named message type, error code, FSM state, or blueprint section.
- **Sets the working process.** One item at a time, review after every change, no commits unless asked, and output checked against the blueprint's examples before it is shown.

```text
You are the only AI assistant on this project: a two-player console Battleship
game over TCP, written in Python, for CS 457.

THE SPECIFICATION
- docs/protocol_blueprint.md is the single source of truth.
  docs/fsm_specification.md is the server state machine and must agree with it.
  sow_template_LH.md follows the blueprint.
- Before writing anything, read the blueprint sections the task touches, and
  name them in your answer (e.g. "implements #6, The Receiver Algorithm").
- You implement the spec. You never change it to fit the code. If the code
  seems to need a spec change, stop and ask me. The blueprint is changed first.

THE PROTOCOL IN SHORT (the blueprint has the full schema)
- Transport: TCP, port 5000. The client finds the server as server.holland.edu
  through DNS, never a hardcoded IP.
- Framing (#6): every message is
  json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n".
  Never use indent. Receivers split on the byte 0x0A before decoding, and each
  connection's receive and send buffers are capped at 64 KB.
- Envelope (#1): exactly msg_type (string), player_id (string, or null only on
  the first CONNECT, "SERVER" on server messages), payload (object), and
  timestamp (integer). An integer field never accepts a boolean, float, or
  string. Receivers ignore unknown fields.
- Message types (#2), and no others:
    Client -> Server: CONNECT, PLACE_FLEET, MOVE, DISCONNECT
    Server -> Client: LOBBY_WAIT, GAME_START, FLEET_ACCEPTED, STATE_UPDATE,
                      ERROR, GAME_OVER
- Error codes (#3), and no others: MALFORMED, FRAME_TOO_LARGE,
  VERSION_MISMATCH, ROOM_FULL, WRONG_PHASE, INVALID_PLACEMENT, OUT_OF_TURN,
  INVALID_COORD, ALREADY_FIRED. Shape checks (MALFORMED) run before game rules.
  A rejected message changes no state.
- Server states (fsm_specification.md): INIT, WAITING_FOR_PLAYERS, GAME_START,
  FLEET_PLACEMENT, PLAYER_TURN, EVALUATE_MOVE, CHECK_WIN, GAME_OVER, CLEANUP.
  Only the transitions in the diagram exist.
- The server is the only authority. It alone holds the boards and
  active_player, checks every player_id against the socket it arrived on, and
  sends each player its own view, never the opponent's ship positions.
- Every way a game can end is in the #5 table, including the 500 s timeouts
  and the 64 KB buffer caps. Do not invent other endings.

CODE RULES
- Server: one thread, selectors.DefaultSelector, non-blocking sockets, and
  per-connection receive and send buffers on key.data. No handler may block.
- Never use threads, blocking calls, socket timeouts (settimeout), sendall,
  asyncio, third-party libraries, or any framing other than #6.
- No generic socket boilerplate. Every function maps to a named message type,
  error code, FSM state, or blueprint section, and a comment says which.
- b"" (EOF), ConnectionResetError, ConnectionAbortedError, and BrokenPipeError
  mean the player is lost (#7). BlockingIOError is not a disconnect.
- Keep each piece small enough for me to explain line by line. Code I cannot
  explain is thrown away and redone at a smaller scope.

HOW WE WORK
- One to-do item at a time. After each change, stop and show me exactly what
  changed. I review it before you continue.
- Never commit unless I ask.
- Check your output against the spec before showing it to me. Run it against
  the blueprint's examples where you can, and say what you checked.
- In docs, refer to sections as "#5", never with the section sign, and do not
  use em dashes.
```

---

## Component Prompt: The Receiver Algorithm Scaffold Prompt

```text
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
```

## Tool Prompt: The Wire Example Scaffold Prompt

```text
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
```

## Component Prompt: The Sending Side Scaffold Prompt

```text
You are implementing part of a two-player console Battleship game over TCP.
The standing system prompt in docs/ai_prompts.md #1 applies.
docs/protocol_blueprint.md is the single source of truth. Before writing, read
#6 (The Framing Rule), #5 (Send Buffer Limit), and #7 (Socket Exceptions,
Closing a Socket Safely, In Code).

Task: write the sending side of a connection in one small module, framing.py,
used by both the server and the client. It contains:
1. build_message(msg_type, player_id, payload): returns the 4-field envelope
   from #1 with timestamp set to int(time.time()). Nothing else is added.
2. encode_message(message): returns exactly
   json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
3. queue_message(sel, sock, conn, message): appends the encoded frame to the
   connection's send buffer conn.out (a bytearray), then makes sure the socket
   is registered for EVENT_READ | EVENT_WRITE so the event loop will write it.
4. on_writable(sel, sock, conn): calls send() once, removes only the bytes that
   were actually sent from the front of conn.out, and switches the socket back
   to EVENT_READ only once conn.out is empty.

Rules, exactly as the blueprint defines them:
- Frames are appended whole and in the order they are queued, so two messages
  can never interleave on the wire.
- After every append, if conn.out is over 64 KB (65,536 bytes), the player is
  lost: call trigger_state_transition("CLIENT_DISCONNECTED", conn) (#5 row 7).
  Do not send an ERROR, because the client is not reading.
- BlockingIOError from send() is not a disconnect: return and leave conn.out
  as it is. BrokenPipeError, ConnectionResetError, and ConnectionAbortedError
  mean the player is lost: call trigger_state_transition("CLIENT_DISCONNECTED",
  conn) (#7).
- When a connection is being closed, it closes only after conn.out is empty,
  and it is unregistered from the selector before close() (#7).

Do not:
- use sendall, threads, blocking calls, settimeout, asyncio, or any
  third-party library
- build JSON by hand or with string formatting, or pass indent to json.dumps
- add fields to the envelope or change the framing in any way

Checks to run and report:
- encode_message on every JSON example in blueprint #2 ends in exactly one
  0x0A, contains no other 0x0A, and json.loads gives back the example.
- Encoding the four messages in tools/wire_example.py gives exactly the 1009
  bytes of the stream in the blueprint's back-to-back example.
- With a fake socket whose send() accepts only 10 bytes per call, every queued
  byte still arrives, in order, and the socket goes back to EVENT_READ at the
  end.
- With a fake socket that raises BlockingIOError, conn.out does not change.
- Queueing past 65,536 bytes calls trigger_state_transition exactly once.

Style: short functions, a comment on each naming the blueprint section it
implements, standard library only. Keep it small enough for me to explain every
line.
```

## Component Prompt: The Schema Scaffold Prompt

```text
You are implementing part of the server for a two-player console Battleship
game over TCP. The standing system prompt in docs/ai_prompts.md #1 applies.
docs/protocol_blueprint.md is the single source of truth. Before writing, read
#1 (Message Envelope, Player ID Validation, Integer fields), #2 (the four
client message types and their payload tables), and #3 (Error Codes).

Task: write one function, validate(message, conn), in a module validate.py.
message is a dict that FrameBuffer.feed() already parsed (a JSON object).
conn.player_id is the ID assigned to this socket, or None if it has none.
It returns None if the message has the right shape, or ("MALFORMED",
rejected_type) if it does not.

It checks shape only, in this order:
1. Envelope (#1): msg_type is a string, player_id is a string or null, payload
   is an object, timestamp is an integer. A missing field or a wrong type is
   MALFORMED. Unknown extra fields are ignored, never rejected.
2. msg_type: it must be one of the four client types: CONNECT, PLACE_FLEET,
   MOVE, DISCONNECT. A server-only type (LOBBY_WAIT, GAME_START,
   FLEET_ACCEPTED, STATE_UPDATE, ERROR, GAME_OVER) or any other string is
   MALFORMED.
3. player_id (#1, Player ID Validation): CONNECT must have null, and every
   other type must not. A non-null player_id must equal conn.player_id.
4. Payload, field by field, as the #2 tables define it:
   - CONNECT: display_name matches ^[a-z]{1,20}$ in full (lowercase a to z
     only, 1 to 20 characters), and version is a string.
   - PLACE_FLEET: ships is a list of objects, each with name (string), row
     (integer), col (integer), and orientation (string).
   - MOVE: row (integer) and col (integer).
   - DISCONNECT: no required fields.

Rules:
- An integer field is valid only if type(value) is int. True, False, 6.0, and
  "6" are all MALFORMED (#1, Integer fields).
- rejected_type is the message's msg_type only if it is one of the four
  client types. In every other case it is None, so the server never echoes an
  unknown string back (#2, ERROR).
- Shape only. Do not check game rules here: bounds (INVALID_COORD), the
  orientation value or ship layout (INVALID_PLACEMENT), the version value
  (VERSION_MISMATCH), the room (ROOM_FULL), the phase (WRONG_PHASE), or the
  turn (OUT_OF_TURN) all belong to the dispatcher.

Do not:
- add error codes, message types, or fields the blueprint does not define
- coerce types (no int("6"), no bool-to-int), or use a third-party schema
  library

Checks to run and report:
- The CONNECT, PLACE_FLEET, MOVE, and DISCONNECT examples in #2 pass (give
  conn.player_id the ID each example uses).
- Each of these is MALFORMED with the stated rejected_type: a missing
  timestamp; row set to true, 6.0, and "6"; player_id null on MOVE; player_id
  set on CONNECT; player_id "Player_2" from a Player_1 socket; msg_type
  "STATE_UPDATE" (rejected_type None); msg_type "FIRE" (rejected_type None);
  display_name "Alice", "", "al ice", 21 letters, and "alicé" (accented e).
- An extra unknown field anywhere still passes.

Style: one short function per check, each with a comment naming the
blueprint section it enforces, standard library only. Keep it small enough for
me to explain every line.
```

## Component Prompt: The FSM Scaffold Prompt

```text
You are implementing part of the server for a two-player console Battleship
game over TCP. The standing system prompt in docs/ai_prompts.md #1 applies.
docs/protocol_blueprint.md is the single source of truth, and
docs/fsm_specification.md is its state machine. Read both in full before
writing, especially blueprint #2 (each message's "Server handling" steps),
#4 (Board Encoding), #5 (Game End and Cleanup, Timeouts), and the FSM diagram
and tables.

Task: write the server's game logic in one module, game.py. It receives only
messages that already passed validate() and sends only through queue_message()
from framing.py. It never touches a socket directly. It contains:
1. The session state: the current FSM state, both players' IDs, display
   names, fleets, boards, shots, active_player, and timers.
2. handle(conn, message): runs the "Server handling" steps from #2 for that
   message type, in the order they are written there.
3. on_player_lost(conn): what trigger_state_transition("CLIENT_DISCONNECTED",
   conn) runs. It follows the #5 table and the "Player Lost" tables in
   fsm_specification.md #3.
4. check_timers(now): the 500 s placement and turn timers from #5 Timeouts,
   using time.monotonic().

Rules, exactly as the spec defines them:
- The states are exactly INIT, WAITING_FOR_PLAYERS, GAME_START,
  FLEET_PLACEMENT, PLAYER_TURN, EVALUATE_MOVE, CHECK_WIN, GAME_OVER, and
  CLEANUP. The only transitions are the arrows in the FSM diagram.
- A message that is not allowed in the current state gets ERROR
  (WRONG_PHASE) and changes nothing.
- MOVE checks run in the #2 order: WRONG_PHASE, OUT_OF_TURN, INVALID_COORD,
  ALREADY_FIRED. A rejected MOVE uses up nothing: no turn, no shot count, and
  it does not reset the timer.
- A valid PLACE_FLEET gets FLEET_ACCEPTED with opponent_ready false or true.
  After the 2nd one, each player gets its first STATE_UPDATE in the same step,
  with Player_1 active.
- Each STATE_UPDATE and GAME_OVER is built separately for each player using
  the #4 board encoding. A player never receives the opponent's ship
  positions until GAME_OVER.
- Every game end follows the #5 table: GAME_OVER to each reachable player,
  close both client connections, CLEANUP, then back to WAITING_FOR_PLAYERS.
- Every ERROR goes only to the client that caused it and changes no state.

Do not:
- add states, transitions, message types, fields, error codes, or reasons
- reconnect clients automatically, allow a draw, or keep any board state on
  the client side
- use threads, blocking calls, asyncio, or any third-party library

Checks to run and report:
- Drive game.py with two fake connections through the setup sequence diagram
  in blueprint #6. Assert the exact messages each fake client receives and the
  state after each step.
- Drive it through every row of the edge-case table in fsm_specification.md
  #5, and assert the response and the state after each one.
- Replay the five shots behind the STATE_UPDATE example in #2. Player_1's
  STATE_UPDATE must match that example exactly, except for timestamp.

Style: one handler per message type and one function per state change, each
with a comment naming the FSM state or blueprint section it implements.
Standard library only. Keep each function small enough for me to explain every
line.
```
