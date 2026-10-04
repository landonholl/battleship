# CS 457 Project Statement of Work (SOW) & Protocol Specification Template

**Student Name:** [Landon Holland]
**Date:** [2026-09-19]
**Course:** CS 457 - Computer Networks
**Target Server Domain:** `server.holland.edu`
**Github:** https://github.com/landonholl/battleship

---

## 1. Game Selection & Scope (Sprint 0)

> Planning is going to be an iterative process through the sprints so you don't have to have all the details now. Focus on big overview concepts. You will be updating the SOW as we plan.
> You have a lot of freedom to choose a game. There are a couple caveats.

> - It must run in the console. The lab nodes won't be able to handle extensive graphics.
> - It has to be self-contained. You can use a internet-connector to download you code, but because the architecture must run 5 nodes you won't be able to run
> - You are encouraged to use python, but I'm not going to make it a strict requirement. The instructor and TA's ability to help with C or Rust, etc will be diminished in other languages.

### 1.1 Game Overview

- **Chosen Game:** Battleship
- **Player Capacity:** 2 Players (Simulated via 2 CML Client nodes)
- **Game Summary:** Each player has a 10x10 grid and secretly places a fleet of five ships (Carrier 5, Battleship 4, Cruiser 3, Submarine 3, Destroyer 2) horizontally or vertically, with no overlapping or out of bounds placements. Once both fleets are set, players alternate firing one shot per turn at a coordinate on the opponents grid, such as B7. The server checks the shot against the hidden fleet and reports hit, miss, or sunk, then sends each player an updated view: their own fleet with incoming shots marked, and a tracking grid showing the results of their own shots. A ship is sunk once every cell it occupies has been hit. Players never see the opponents ship positions, only the outcome of the shots they take.

### 1.2 Core Game Rules & Win/Draw Conditions

- **Turn Mechanics:** The server is the only authority on whose turn it is. After both players finish ship placement, the server assigns the first turn to Player 1 and stores the active player ID in the game state. When a `MOVE` arrives, the server compares the senders player ID to the active player ID. If they do not match, the move is rejected with an `ERROR` message and the state is left unchanged, so a client cannot fire out of turn or fire twice in a row. If they do match, the server validates the position (on the board, not already fired at by that player), resolves the shot, flips the active player ID to the opponent, and sends each player its own `STATE_UPDATE` telling it whose turn it is now. Clients only display a prompt for input when the update names them as the active player, but the enforcement is server side so a modified client still cannot take an extra turn.
- **Victory Condition:** A player wins by sinking all five of the opponents ships. The server tracks the remaining unhit cells for every ship, and after each shot it checks whether the defending player has any ship cells left. When that count reaches zero, the server moves to `GAME_OVER` and sends each player its own `GAME_OVER` with the winners player ID and a final tally of shots taken and hits landed. No further moves are accepted after that point.
- **Draw/Tie Condition:** A true draw is not possible in Battleship. Players alternate single shots, so only the player who just fired can reduce the opponents fleet to zero, and the win check runs immediately after each shot. That means both fleets can never be eliminated on the same turn. The game instead ends early in two non-win cases: if a client disconnects or goes 500 seconds without a valid move during turns, the server sends `GAME_OVER` to the remaining player as the winner (a forfeit) with reason `OPPONENT_DISCONNECTED`; if a client disconnects or goes 500 seconds without a valid fleet during fleet placement, no shots have been fired, so the server sends `GAME_OVER` with no winner and reason `OPPONENT_DISCONNECTED`; if both clients are lost, nothing is sent and no winner is recorded. In every case the server then closes both client connections, runs `CLEANUP`, and goes back to `WAITING_FOR_PLAYERS` for the next game. Every way a game can end is listed in `docs/protocol_blueprint.md` #5.

---

## 2. Application-Layer Messaging Protocol Blueprint (Sprint 1 Deliverable)

### 2.1 Message Transport & Serialization Format

- **Transport Protocol:** TCP
- **Serialization Format:** JSON, UTF-8. Every message will be a single JSON object with the fields defined in 2.2. JSON is chosen over delimited text because `STATE_UPDATE` will probably carry nested structures like two 10x10 grids.
- **Framing Mechanism:** Newline-delimited (`\n`) JSON payloads. Each message is serialized with compact `json.dumps`, a single `\n` is appended, and the result is added to the connection's send buffer and written with non-blocking `send()` calls whenever the socket is writable (3.1). Because `json.dumps` escapes control characters inside strings, a literal newline byte never appears inside a payload, so `\n` is an unambiguous frame boundary. TCP delivers a byte stream instead of discrete messages, each connection keeps its own receive buffer: bytes from `recv` are appended to that buffer, complete frames are split off at each `\n` and parsed, and any partial frame stays buffered until the rest arrives. The buffer is capped at 64 KB, and a client that exceeds it without sending a delimiter is sent `ERROR` (`FRAME_TOO_LARGE`) and dropped. Each send buffer is also capped at 64 KB, so a client that stops reading cannot grow the server's memory. The full framing rule, raw wire examples, and the receiver algorithm are in `docs/protocol_blueprint.md` #6. This format was chosen because it will be directly readable in Wiresharks Follow TCP Stream feature, which will help debugging.

### 2.2 Message Schema Definitions

#### Message Envelope:

Full field tables and sample JSON for every message are in `docs/protocol_blueprint.md` #2. Every message, in both directions, uses the same envelope: `msg_type` (string), `player_id` (string, or `null` only on a client's first `CONNECT`, and `"SERVER"` on server-originated messages), `payload` (object, may be empty), and `timestamp` (integer Unix seconds). Unknown fields are ignored by the receiver so the schema can grow in later sprints without breaking an older client.

#### Message Types:

1. `CONNECT` (Client -> Server): Request to join the game room. Payload carries a display name (1 to 20 lowercase letters, `a` to `z` only) and the protocol version the client speaks.
2. `LOBBY_WAIT` (Server -> Client): Acknowledges the join, assigns the `player_id` for the current game (`Player_1` / `Player_2`) in join order, so the first client to connect becomes `Player_1` and the second becomes `Player_2`, and reports that the server is waiting for the second player.
3. `GAME_START` (Server -> Clients): Both players connected. Payload contains the opponents display name, the board dimensions (10x10), and the fleet manifest (ship name and length for all five ships). Both clients move into fleet placement on receipt.
4. `PLACE_FLEET` (Client -> Server): Submits all five ship placements at once, each as ship name, start coordinate, and orientation (`H` or `V`). The server validates that every ship is in bounds, matches its required length, and does not overlap another ship. An invalid layout is answered with `ERROR` and the player stays in placement. A valid layout is answered with `FLEET_ACCEPTED`.
5. `FLEET_ACCEPTED` (Server -> Client): Confirms that a fleet layout passed every check and is final. Its `opponent_ready` field is `false` for the first player to place, who then waits, and `true` for the second, after which both players get their first `STATE_UPDATE`.
6. `MOVE` (Client -> Server): Fire one shot at a coordinate on the opponents grid. This is only allowed when the sender is the active player and both fleets are placed.
7. `STATE_UPDATE` (Server -> Client): Sent individually to each player, **NOT** broadcast identically. Payload contains the active player ID, and the receiving player's own board with incoming shots marked, and that player's tracking grid of its own shots, and the result of the most recent shot (`HIT`, `MISS`, or `SUNK`, plus the ship name when sunk), and the count of ships still afloat on each side, and the total number of valid shots fired so far this game. A player never receives the opponents ship positions, only the outcome of shots already taken.
8. `GAME_OVER` (Server -> Clients): Terminal notification, and the last message on the connection: the server closes both connections after it. Payload carries the winning `player_id` (or `null` when there is no winner), a `reason` (`FLEET_DESTROYED` or `OPPONENT_DISCONNECTED`), per player statistics (shots and hits; accuracy is computed by the client), and a final showing of both fleets (no fleet reveal if the game ended during fleet placement).
9. `ERROR` (Server -> Client): Rejection of a client message. Payload carries a machine readable `code`, a human readable `message`, and `rejected_type`, the `msg_type` of the rejected message (`null` if it could not be parsed). The error is sent only to the offending client.
10. `DISCONNECT` (Client -> Server): The player is quitting on purpose. The server wipes the sender's `player_id` and closes its socket. If the opponent is still connected, they receive `GAME_OVER` with reason `OPPONENT_DISCONNECTED`: as the winner during turns, or with no winner during fleet placement. Their connection is then closed too, and the server runs `CLEANUP`. There is no automatic reconnect: to play again, a player runs the client again.

#### Error Codes:

- `OUT_OF_TURN`: a `MOVE` arrived from the player who is not the active player.
- `ALREADY_FIRED`: the target coordinate was already fired at by this player.
- `INVALID_COORD`: the coordinate is outside the 10x10 grid.
- `INVALID_PLACEMENT`: a ship in the fleet layout is missing, repeated, or unknown, has an orientation other than `H` or `V`, runs off the board, or overlaps another ship.
- `WRONG_PHASE`: the message type is not legal in the current FSM state, such as a `MOVE` sent during placement.
- `MALFORMED`: the server could not understand the message: invalid JSON, a missing or wrong-type field, a bad `player_id`, an unknown `msg_type`, or a server-only message type sent by a client.
- `FRAME_TOO_LARGE`: the client sent more than 64 KB without a newline. The server sends this error and then closes the connection.
- `VERSION_MISMATCH`: the `CONNECT` version is not one the server speaks. The server sends this error and then closes the connection.
- `ROOM_FULL`: a `CONNECT` arrived while both player slots are taken. The server sends this error and then closes the connection.

#### Board Encoding:

Each grid is a list of 10 strings of 10 characters. On a players own board: `.` water, `S` an undamaged ship cell, `X` a hit on a ship still afloat, `#` a cell of a sunk ship, `O` an opponent shot that missed. On the tracking grid: `.` not yet fired at, `X` a hit on a ship still afloat, `#` a cell of a ship the player sank, `O` a miss. Ship positions are only ever encoded in the board belonging to the player receiving the message.

#### Example JSON Protocol Schema:

```json
{
  "msg_type": "MOVE",
  "player_id": "Player_1",
  "payload": {
    "row": 1,
    "col": 6
  },
  "timestamp": 1727000000
}
```

```json
{
  "msg_type": "PLACE_FLEET",
  "player_id": "Player_1",
  "payload": {
    "ships": [
      { "name": "Carrier",    "row": 0, "col": 0, "orientation": "H" },
      { "name": "Battleship", "row": 2, "col": 3, "orientation": "V" },
      { "name": "Cruiser",    "row": 6, "col": 5, "orientation": "H" },
      { "name": "Submarine",  "row": 7, "col": 1, "orientation": "V" },
      { "name": "Destroyer",  "row": 9, "col": 8, "orientation": "H" }
    ]
  },
  "timestamp": 1727000001
}
```

```json
{
  "msg_type": "STATE_UPDATE",
  "player_id": "SERVER",
  "payload": {
    "active_player": "Player_2",
    "your_board": [
      "SSSSS.....",
      "..........",
      "...S......",
      "...S......",
      "...X......",
      "...S.....O",
      ".....SSS..",
      ".S........",
      ".S........",
      ".S......SS"
    ],
    "tracking_grid": [
      "..........",
      "......X...",
      "..........",
      ".....O....",
      "..........",
      "..........",
      "..........",
      "..........",
      "........O.",
      ".........."
    ],
    "last_shot": {
      "shooter": "Player_1",
      "row": 1,
      "col": 6,
      "result": "HIT",
      "ship_sunk": null
    },
    "ships_remaining": { "Player_1": 5, "Player_2": 5 },
    "shots_fired": 5
  },
  "timestamp": 1727000002
}
```

---

### 2.3 Game State Machine (FSM) Design (Sprint 1 Deliverable)

- **State Transitions:** `INIT` -> `WAITING_FOR_PLAYERS` -> `GAME_START` -> `FLEET_PLACEMENT` -> `PLAYER_TURN` -> `EVALUATE_MOVE` -> `CHECK_WIN` -> (back to `PLAYER_TURN`, or on to `GAME_OVER`) -> `CLEANUP` -> back to `WAITING_FOR_PLAYERS`. The full Mermaid diagram, state table, and edge cases are in `docs/fsm_specification.md`.

Two changes.

A `FLEET_PLACEMENT` state is needed  because Battleship has a setup phase before any shot is fired, and `CHECK_WIN` replaces `CHECK_WIN_DRAW` because, as said in 1.2, a draw cannot happen in this game.

| State                   | Entered when                                      | Server behavior                                                                                                                                                                                                                                                                                                                    | Exits to                                                                                                                    |
| ----------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `INIT`                | Process start                                     | Bind the listening socket on port 5000, initialize an empty game session                                                                                                                                                                                                                                                           | `WAITING_FOR_PLAYERS`                                                                                                     |
| `WAITING_FOR_PLAYERS` | Socket listening, or after `CLEANUP` | Accept connections, assign `Player_1` / `Player_2` on `CONNECT`, reply `LOBBY_WAIT`. A third client is rejected with `ERROR` (`ROOM_FULL`) | `GAME_START` once both players have joined |
| `GAME_START` | Both players have an ID | Send each player `GAME_START` and start each player's 500 s placement timer | `FLEET_PLACEMENT` |
| `FLEET_PLACEMENT` | `GAME_START` was sent | Await `PLACE_FLEET` from each player, validate it, and reply `FLEET_ACCEPTED` to a valid layout. An invalid layout gets `ERROR` (`INVALID_PLACEMENT`) and the player stays in this state. A `MOVE` here is rejected with `WRONG_PHASE` | `PLAYER_TURN` once both fleets are valid, setting the active player to `Player_1` |
| `PLAYER_TURN` | Both fleets placed, or the previous turn resolved | Send each player its own `STATE_UPDATE`, then wait for a `MOVE` from the active player (500 s turn timer). A `MOVE` from the inactive player is rejected with `OUT_OF_TURN` and the state does not change | `EVALUATE_MOVE` on a `MOVE` from the active player |
| `EVALUATE_MOVE`       | Valid sender                                      | Validate the coordinate (in bounds, not already fired at by this player), resolve the shot against the defender's hidden fleet as hit, miss, or sunk, and record it on both the defender's board and the shooter's tracking grid. An invalid coordinate returns`ERROR` and reverts to `PLAYER_TURN` without consuming the turn | `CHECK_WIN`                                                                                                               |
| `CHECK_WIN`           | Shot resolved                                     | Test whether the defender has any unhit ship cells remaining                                                                                                                                                                                                                                                                       | `GAME_OVER` if the defending fleet is destroyed, otherwise `PLAYER_TURN` with the active player flipped to the opponent |
| `GAME_OVER` | Fleet destroyed, or a player was lost | Send each reachable player its own `GAME_OVER` with the winner, the `reason` (`FLEET_DESTROYED` or `OPPONENT_DISCONNECTED`), final statistics, and the reveal of both fleets. Anything else that arrives is discarded | `CLEANUP` |
| `CLEANUP` | Result delivered | Close both client sockets and discard the session state. The listening socket stays open | `WAITING_FOR_PLAYERS` for the next game |

- **Disconnect Handling:** A player is lost when it sends `DISCONNECT`, its socket closes (an empty `recv`) or resets, it misses a 500 s timeout, or it breaks a 64 KB buffer cap (`docs/protocol_blueprint.md` #5 and #7). This is not a normal transition. From `WAITING_FOR_PLAYERS` the server wipes that player's ID and keeps waiting. From `FLEET_PLACEMENT` no shots have been exchanged, so the server sends the remaining player `GAME_OVER` with no winner and reason `OPPONENT_DISCONNECTED`. From `PLAYER_TURN` the server sends the remaining player `GAME_OVER` as the winner by forfeit, with reason `OPPONENT_DISCONNECTED`. Either way both connections are then closed, and the server runs `CLEANUP` and returns to `WAITING_FOR_PLAYERS`. If both clients are lost, the server goes straight to `CLEANUP` and records no winner.

---

## 3. Game Behavior & Server Concurrency Architecture (Sprint 2 Deliverable)

### 3.1 Server Concurrency Strategy

- **Architecture Choice:** Non-blocking I/O multiplexing with a single threaded event loop. (`selectors.DefaultSelector`). With only two players and a few hundred bytes per turn there is no workload to parallelize, so multiplexing is chosen for correctness. It removes the possibility of concurrent state mutation. Every socket is set non-blocking, and each connection carries its own receive and send buffers on the selector key's `data` object, which is where the partial-frame handling described in 2.1 lives.

- **Synchronization Logic:** Because the server runs one thread, no `threading.Lock` is needed. The shared game state (both boards, the fleet records, and the active player ID) and the client list are only ever touched from inside the event loop, so reads and writes are serialized by construction and a race condition during turn processing is  impossible. Each selector event is processed completely before the next is dispatched, which means a `MOVE` is validated, applied, and answered with `STATE_UPDATE`. This also rules out the failure that threading would introduce here, where two client threads calling `sendall` on the same socket have their bytes combined mid-frame, corrupting the stream. The discipline the event loop needs, and that no handler may block: all socket operations are non-blocking, and a message that cannot be written in full is left in that connection's send buffer, with the socket registered for write readiness until the buffer drains.

### 3.2 State & Score Synchronization Across Clients

- **Turn Enforcement:** The session contains a single `active_player` field, and the server is the only one that reads or writes it. When a `MOVE` is dispatched by the event loop, the server compares the `player_id` on the packet against the socket the frame actually arrived on, so a client cannot impersonate its opponent by reproducing the field. Server then compares it against `active_player`. A mismatch is answered with `ERROR` (`OUT_OF_TURN`) to the offending client only, and no state change will happen. A match moves the FSM to `EVALUATE_MOVE`. The turn is consumed only by a valid shot: a coordinate that is out of bounds or already fired at returns `ERROR` and leaves `active_player` untouched, so a player who mistypes does not lose their turn. Once the shot resolves and the win check completes, the server flips `active_player` to the opponent and both clients learn the new turn from the `active_player` field of the `STATE_UPDATE` they each receive. Clients enable input only when that field names them, but this is for usability, not the enforcement, which is server side.

- **Score & Board Synchronization:** The server holds the only authoritative copy of both boards. Clients store no game state of their own and perform no local prediction: a client does not mark a hit on its tracking grid when it fires, it waits for the server to tell it what happened, which makes client and server divergence (hopefully) impossible. After every state change the server pushes a `STATE_UPDATE` to each connected player, so there is no polling and no request from the client needed. Unlike a symmetric game, this is not a single broadcast: the server builds up a separate redacted view per player, containing that player's own board, that player's tracking grid, the result of the last shot, and the ships-remaining counts for both sides. The scoring data (shots fired, hits, and ships afloat) is recomputed from authoritative state each time instead of being incremented on the client, so the two screens cannot drift apart, or a client can change their turn. Both players are updated after every shot, including the one who is waiting, which should keep the inactive player's screen live. Ordering is guaranteed by two properties already established: TCP delivers each player's frames in order, and the single threaded event loop in 3.1 finishes applying one move before it begins the next, so a client should not render a board state that is older than one it has already displayed.

---

## 4. Coding & AI Implementation Plan (Sprint 3)

- **Permitted AI Tools:** Claude (Claude Code in IDE). No other AI coding tools are used on this project.
- **AI Prompting & Constraint Strategy:** The governing idea is that the protocol blueprint (`docs/protocol_blueprint.md`) and the FSM specification (`docs/fsm_specification.md`) are the specification, and the model helps implement them, never the reverse. Concretely:
  - **Standing instructions every session.** Claude Code loads a project instruction file (`CLAUDE.md`) at the start of every session. It states the rules below, so no session starts unconstrained. Its rules are reproduced in `docs/ai_prompts.md`.
  - **Prompts point at the spec.** Every prompt names the exact blueprint section it implements (e.g. "#6, The Framing Rule") instead of describing the behavior loosely, and lists the message types, fields, and error codes the code may use. Claude may not add message types, fields, error codes, or limits. If the code seems to need a spec change, it stops and asks, and the blueprint is changed first.
  - **Generic boilerplate is ruled out by name.** Prompts forbid threads, blocking calls, socket timeouts, `sendall`, third-party libraries, and any framing other than the newline rule in #6, so the model cannot fall back on a generic socket template.
  - **One small piece at a time, only when needed.** Each prompt covers one component (framing, receiver, schema validator, FSM dispatcher), small enough to review in full. I review every change right after it is made, before moving on.
  - **Output is checked against the spec, not trusted.** Each prompt asks for checks built from the blueprint's own examples (the JSON samples, the wire stream, the fragmentation and coalescing examples), and they are run before anything is committed. For example, `tools/wire_example.py` rebuilds the wire example and fails if the blueprint differs by a single byte. The prompts and the results of these checks are recorded in `docs/ai_prompts.md`.
- **Implementation Risk Management:** Claude Code will scaffold and generate the code, and implementation will hinge on strict human review and understanding, as per the current industry standard with AI models, outlined in the Claude Architect Course. In practice that standard is enforced through the following commitments:
  - **Nothing is committed that I cannot explain.** For any block of generated code I must be able to state which FSM state or message type from Section 2 it implements and why it is written that way. Code I cannot explain is discarded and re-prompted at a smaller scope, not committed and revisited later.
  - **Version control as a rollback path.** Work is committed in small increments at each working state, so a generated change that breaks a previously functioning component can be reverted immediately instead of being debugged under deadline pressure.

---

## 5. CML Multi-Subnet Topology & Wireshark Deployment Plan (Sprint 4 & 5 Deliverable)

> For now you can use the topology below. We may update this when we get to defining subnets.

### 5.1 Subnet & Router Design

- **Subnet A (Client 1):** `192.168.10.0/24` (Interface `Gi0/1` on Router R1)
- **Subnet B (Client 2):** `192.168.11.0/24` (Interface `Gi0/2` on Router R1)
- **Subnet C (Game Server):** `192.168.20.0/24` (Interface `Gi0/1` on Router R2)
- **Router Backbone:** `10.0.0.0/30` (Interface `Gi0/0` on R1 <-> `Gi0/0` on R2)

### 5.2 DHCP Pools & DNS Configuration Plan

- **Router R1 DHCP Pool 1 (`CLIENT1_POOL`):** Leases `192.168.10.10` - `192.168.10.50`, gateway `192.168.10.1`, DNS `10.0.0.2`.
- **Router R1 DHCP Pool 2 (`CLIENT2_POOL`):** Leases `192.168.11.10` - `192.168.11.50`, gateway `192.168.11.1`, DNS `10.0.0.2`.
- **Router R2 Authoritative DNS:** Configured with `ip dns server` and static host mapping `server.[yourlastname].edu` -> `192.168.20.100`.

### 5.3 Deployment Strategy & Wireshark Trace Capture

- **CML Deployment Strategy:** Deploy `server.py` onto Subnet C node (`192.168.20.100`) behind Router R2, and `client.py` onto Subnet A and Subnet B nodes behind Router R1.

- **Name Resolution at the Client:** `client.py` takes the server as the hostname `server.holland.edu` and resolves it at startup with `socket.gethostbyname` rather than connecting to a hardcoded address. The address is therefore never written into the client source, so the DNS service configured on Router R2 in 5.2 is genuinely exercised by the application, and the resolution appears on the wire ahead of the TCP handshake in the capture below. A resolution failure is reported to the player as a distinct error from a refused connection, since the two point at different layers of the topology.

- **Cisco Infrastructure Configuration:** Router R1 DHCP pools (`CLIENT1_POOL`, `CLIENT2_POOL`) and Router R2 authoritative DNS (`ip host server.holland.edu 192.168.20.100`).

- **Wireshark Trace Capture Plan:** Capture DHCP DORA exchange (`dhcp_negotiation.pcap`) and DNS query/response resolution (`dns_lookup.pcap`).
