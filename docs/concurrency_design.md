# Battleship Server Concurrency Design

**Course:** CS 457
**Written by:** Landon Holland

---

## 1. Concurrency Model

The server uses **Option B: non-blocking I/O multiplexing**. It runs one thread with one `selectors.DefaultSelector`, and every socket is set to non-blocking with `sock.setblocking(False)`. All messages, error codes, and states named here are defined in [`protocol_blueprint.md`](protocol_blueprint.md) and [`fsm_specification.md`](fsm_specification.md).

### How it works

- The selector watches the listening socket and every client socket at the same time.
- Each pass of the event loop asks the selector which sockets are ready to read or write, then calls the handler for each ready socket one at a time.
- A handler does its work and returns. It never waits on a socket, so the loop is always free to service the other player.
- Each connection keeps its own receive buffer and send buffer on the selector key's `data` (blueprint #6, The Receiver Algorithm). A message that arrives in pieces waits in its receive buffer, and a message that cannot be sent in full waits in its send buffer.
- The selector is called with a timeout, so the loop wakes up to check the 500 s placement and turn timers even when no socket has data (blueprint #5, Timeouts).

### Why Option B

| Reason | What it means for this game |
| ------ | --------------------------- |
| **The workload is small** | Two players, one shot at a time, and the largest message (`STATE_UPDATE`) is about 550 bytes. There is no heavy work to spread across threads, so threads would add risk without adding speed |
| **Only one thing ever changes the game state** | One thread runs every handler, each handler finishes before the next one starts. Two handlers can never change the boards or `active_player` at the same time, so race conditions are ruled out by design, not by locks |
| **Frames never mix on the wire** | Every outgoing message is added whole to the end of that connection's send buffer, and only the event loop writes from it. Two messages for the same player can never be cut into each other |
| **Timers fit in the same loop** | The 500 s timers are checked by the same thread on every pass. No timer thread and no `settimeout` is needed |
| **It matches the spec already written** | The receiver algorithm (blueprint #6), the termination handlers (blueprint #7), and the buffer caps (blueprint #5) were all written for a single-threaded `selectors` loop |

### Why I did not go with Option A (a thread per client)

A thread per client would work, but every benefit above would have to be rebuilt by hand:

- **Shared state needs a lock.** Both client threads read and write the same session: the boards, `active_player`, the shot counts, and the seat list. Every check-then-change (for example "is it this player's turn? then fire") would need to hold a `threading.Lock`, or both players could act on the same turn.
- **Sockets are shared too.** When a shot ends the game, the shooter's thread has to send `GAME_OVER` to the opponent's socket while the opponent's own thread may be writing an `ERROR` to it. Without a second lock per socket, two `sendall` calls can mix their bytes mid-frame and break the newline framing (blueprint #6).
- **Timers need their own thread.** A thread blocked in `recv()` cannot check a 500 s deadline, so the design would need `settimeout` or a separate timer thread, which is one more thing touching the session.
- **More locks means more ways to deadlock.** A game lock plus a lock per socket can deadlock if two threads take them in a different order.

### The trade-off

The one weakness of a single thread is that one slow handler stalls everyone. So the rule for this server is that **no handler may block**: no blocking calls, no `sendall`, no `settimeout`, no `sleep`. Section 3 covers how the server stays inside that rule and why it keeps the game state safe without any locks.

---

## 2. Connection Lifecycle

Every client socket goes through the same five stages. The listening socket goes through only the first one, and it stays open for as long as the server runs.

| Stage | Triggered by | What the server does | FSM state | Spec |
| ----- | ------------ | -------------------- | --------- | ---- |
| 1. Listen | The server process starts | Opens port 5000 and registers the listening socket with the selector | `INIT` | FSM #4 |
| 2. Accept | The listening socket is readable | Accepts the new socket, makes it non-blocking, gives it its own buffers, registers it | Any | This section |
| 3. Registration | The client's first `CONNECT` | Assigns a seat (`Player_1` or `Player_2`) and replies `LOBBY_WAIT` or rejects and closes | `WAITING_FOR_PLAYERS` | Blueprint #2, `CONNECT` |
| 4. Active servicing | The socket is readable or writable, or a timer runs out | Reads and handles messages, writes queued messages, checks the 500 s timers | `FLEET_PLACEMENT`, `PLAYER_TURN` | Blueprint #5, #6, #7 |
| 5. Teardown | The player is lost or the game ended | Stops reading, closes the socket once its send buffer is empty, unregisters it before `close()` | `GAME_OVER`, `CLEANUP` | Blueprint #5, #7 |

### 2.1 Listen

This happens once in `INIT`:

1. Create a TCP socket: `socket.socket(socket.AF_INET, socket.SOCK_STREAM)`.
2. Set `SO_REUSEADDR`, so the server can be restarted right away without waiting for the old port 5000 to be released by the OS.
3. `bind(("", 5000))`. The empty host means every interface, so clients reach it at `192.168.20.100` (SOW 5.1) through `server.holland.edu`.
4. `listen()`, then `setblocking(False)`, so `accept()` can never stall the loop.
5. Register it with `sel.register(lsock, selectors.EVENT_READ, data=None)`. A `data` of `None` is how the event loop tells the listening socket apart from client sockets, which always carry a connection object.

The listening socket is never closed between games. `CLEANUP` only closes the two client sockets, so the next two players can connect as soon as a game ends (blueprint #5, What each machine does, step 5).

### 2.2 Accept

When the selector reports the listening socket as readable, a client has finished the TCP handshake:

1. Call `accept()` once. It returns the new socket and the client's address. If it raises `BlockingIOError` (the client gave up before the server got to it), nothing happens and the loop moves on.
2. Call `setblocking(False)` on the new socket. Every socket the server uses is non-blocking.
3. Create the socket's connection object and register the socket with `selectors.EVENT_READ` and `data=conn`.

The connection object holds everything that belongs to one socket and nothing that belongs to the game:

| Field | Starts as | What it is |
| ----- | --------- | ---------- |
| `frames` | an empty `FrameBuffer` | The receive buffer and the receiver algorithm (blueprint #6) |
| `out` | an empty `bytearray` | The send buffer. Whole frames are added to the end, and the loop writes from the front |
| `player_id` | `None` | The ID assigned to this socket, set at registration. Every later message is checked against it (FSM #6) |
| `closing` | `False` | Becomes `True` once the socket is being closed or the game has ended. Nothing more is read from it after that |

Accepting a socket does not give it a seat. It is accepted in every state, so a 3rd client is never left hanging in the OS backlog. It only finds out the room is full when it sends `CONNECT` (2.3).

### 2.3 Registration

A socket becomes a player when its first `CONNECT` is accepted. The server runs the `CONNECT` steps from blueprint #2 in order, and the first one that fails decides the reply:

1. The message fails a shape check (for example a `display_name` that is not 1 to 20 letters `a` to `z`), or `player_id` is not `null`: `ERROR` (`MALFORMED`). The socket stays open.
2. The socket already has a `player_id`: `ERROR` (`WRONG_PHASE`). The socket stays open.
3. The `version` is not `"0.0"`: `ERROR` (`VERSION_MISMATCH`), then the socket is closed.
4. Both seats are taken: `ERROR` (`ROOM_FULL`), then the socket is closed.
5. Otherwise the server assigns the next seat in join order, sets `conn.player_id`, stores the display name, adds the socket to the session's seat list, and replies `LOBBY_WAIT`.

When the 2nd seat is filled, the server goes through `GAME_START` in the same event-loop step: it sends `GAME_START` to both players, starts both 500 s placement timers, and moves to `FLEET_PLACEMENT` (FSM #4).

An unseated socket that sends anything other than `CONNECT` gets `ERROR` (`MALFORMED`), because only `CONNECT` may have a `null` `player_id` and the socket has no ID for any other value to match (blueprint #1, Player ID Validation).

If `Player_1` is lost while waiting in the lobby, the server closes the socket, wipes the ID, and frees the seat. The next client to connect becomes `Player_1` (blueprint #5, Not a game end).

### 2.4 Active Servicing

Once both players are seated, every pass of the event loop does three things:

1. **Wait.** `sel.select(timeout=1.0)` returns the sockets that are ready, or an empty list after 1 second if none are.
2. **Service each ready socket, one at a time.**
   - Listening socket (`data` is `None`): accept, as in 2.2.
   - Readable client socket: `on_readable`. It calls `recv(4096)` once, feeds the bytes to `conn.frames`, and handles every complete message in arrival order (blueprint #6, The Receiver Algorithm). Each message goes through the shape checks and then the FSM.
   - Writable client socket: `on_writable`. It calls `send()` once, removes only the bytes that went out from the front of `conn.out`, and stops watching for write readiness once `conn.out` is empty (blueprint #7, In Code).
3. **Check timers.** `check_timers(time.monotonic())` looks for a placement or turn timer that has reached 500 s. That player is lost (blueprint #5, Timeouts).

**Why write readiness is only watched sometimes.** A healthy socket can almost always take more bytes, so a socket registered for `EVENT_WRITE` all the time would be reported ready on every pass and the loop would spin at 100% CPU. So a client socket is registered for `EVENT_READ` only. Queuing a message adds `EVENT_WRITE` with `sel.modify`, and `on_writable` removes it once the send buffer is empty.

**Why a 1 second timeout.** The timeout only decides how often the loop wakes up when nothing is happening. With 1 second, a 500 s timer fires at most 1 second late, and an idle server wakes once a second, which costs nothing.

### 2.5 Teardown

A socket is torn down in one of two ways.

**One socket on its own.** This is a rejected client (`ROOM_FULL`, `VERSION_MISMATCH`) or `Player_1` lost in the lobby. The game is not affected.

1. Set `conn.closing`. Nothing more is read from the socket.
2. If an `ERROR` is waiting in `conn.out`, keep the socket registered until `on_writable` has sent it, so the client sees why it was closed.
3. `close_connection`: `sel.unregister(sock)` first, then `sock.close()` (blueprint #7, Closing a Socket Safely).

**The whole game.** This is every game end in the blueprint #5 table, whether the fleet was destroyed or a player was lost.

1. Queue `GAME_OVER` to each player the server can still reach.
2. Set `closing` on both connections. Any bytes that still arrive are discarded (blueprint #5, What each machine does, step 2).
3. Close each socket as soon as its send buffer is empty, so `GAME_OVER` is handed to the OS before the FIN. A socket that is already gone (EOF, reset, send buffer overflow) is closed right away and its buffers are thrown away.
4. When both sockets are closed, run `CLEANUP`: discard the session (boards, fleets, both IDs, `active_player`, shot counts, timers).
5. Go back to `WAITING_FOR_PLAYERS`. The listening socket is still registered, so new clients can connect immediately.

In both cases a socket is unregistered before it is closed, and its connection object is dropped with it. A closed socket that stayed registered would be reported readable on every pass and spin the loop (blueprint #7, The 0 Byte EOF Rule).
