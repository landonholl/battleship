"""Server game logic: the state machine in docs/fsm_specification.md.

Implements blueprint #2 (each client message's "Server handling" steps),
#4 (Board Encoding), and #5 (Game End and Cleanup, Timeouts). It only sees
messages that already passed validate.py, and it never touches a socket:
every send and close goes through the server object passed in as `net`
(server.py), which owns the selector and the send buffers.

Only two things are stored per game: each player's fleet and each player's
fired-at cells. Every board, count, and score is computed from them when a
message is built (concurrency_design.md 4.1), so they can never disagree.
"""

import time

from framing import build_message

BOARD_SIZE = 10                        # blueprint #2, GAME_START
FLEET = [                              # blueprint #2, GAME_START
    {"name": "Carrier", "length": 5},
    {"name": "Battleship", "length": 4},
    {"name": "Cruiser", "length": 3},
    {"name": "Submarine", "length": 3},
    {"name": "Destroyer", "length": 2},
]
SHIP_LENGTHS = {ship["name"]: ship["length"] for ship in FLEET}
VERSION = "0.0"                        # blueprint #3, VERSION_MISMATCH
PLAYER_IDS = ("Player_1", "Player_2")  # blueprint #1, Player ID Assignment
PLACEMENT_TIMEOUT = 500                # blueprint #5, Timeouts (seconds)
TURN_TIMEOUT = 500
GAME_OVER_TIMEOUT = 10

# Human readable text for each error code (blueprint #3).
ERROR_TEXT = {
    "MALFORMED": "The server could not understand that message.",
    "FRAME_TOO_LARGE": "More than 64 KB arrived without a newline.",
    "VERSION_MISMATCH": "This server only speaks protocol version 0.0.",
    "ROOM_FULL": "Both seats are taken. Try again when this game ends.",
    "WRONG_PHASE": "That message is not allowed right now.",
    "INVALID_PLACEMENT": "Every ship must be placed once, H or V, fully on "
                         "the board, with no two ships overlapping.",
    "OUT_OF_TURN": "It is not your turn.",
    "INVALID_COORD": "That cell is off the board.",
    "ALREADY_FIRED": "You already fired at that cell.",
}


def log(text):
    """Server console log: one timestamped line per event."""
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


def other(player_id):
    """The opponent's ID."""
    return "Player_2" if player_id == "Player_1" else "Player_1"


def cell_name(cell):
    """(1, 6) -> 'B7' (blueprint #2, MOVE): letter is the row."""
    return f"{chr(ord('A') + cell[0])}{cell[1] + 1}"


def on_board(row, col):
    """INVALID_COORD / INVALID_PLACEMENT bounds check (blueprint #2)."""
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE


def ship_cells(row, col, length, orientation):
    """PLACE_FLEET (#2): "H" runs right, "V" runs down from the start."""
    if orientation == "H":
        return [(row, col + i) for i in range(length)]
    return [(row + i, col) for i in range(length)]


def check_layout(ships):
    """PLACE_FLEET step 2 (#2): return {name: cells}, or None if invalid."""
    names = [ship["name"] for ship in ships]
    if sorted(names) != sorted(SHIP_LENGTHS):   # each ship once, no others
        return None
    fleet, taken = {}, set()
    for ship in ships:
        if ship["orientation"] not in ("H", "V"):
            return None
        cells = ship_cells(ship["row"], ship["col"],
                           SHIP_LENGTHS[ship["name"]], ship["orientation"])
        if not all(on_board(r, c) for r, c in cells) or taken & set(cells):
            return None                         # off the board, or overlap
        taken.update(cells)
        fleet[ship["name"]] = cells
    return fleet


class Game:
    """One game session and the FSM state (fsm_specification.md #4)."""

    def __init__(self, net):
        self.net = net          # server.py: queue_message, close_now, is_open
        self.state = "INIT"
        self.reset()

    def reset(self):
        """CLEANUP (#5 step 4): discard the whole session."""
        self.seats = {}                 # player_id -> connection
        self.names = {}                 # player_id -> display_name
        self.fleets = {}                # player_id -> {ship name: cells}
        self.fired = {pid: [] for pid in PLAYER_IDS}   # cells, in order
        self.active_player = None
        self.placement_started = {}     # player_id -> placement timer start
        self.turn_started = None        # active player's turn timer start
        self.game_over_at = None        # 10 s game over timer start

    def transition(self, new_state):
        """Move the FSM and log it, so the console shows every transition."""
        log(f"[FSM] {self.state} -> {new_state}")
        self.state = new_state

    # ----- sending (always through server.py's queue_message) -----

    def send(self, conn, msg_type, payload):
        """Queue one server message; player_id is always "SERVER" (#1)."""
        self.net.queue_message(conn,
                               build_message(msg_type, "SERVER", payload))

    def send_error(self, conn, code, rejected_type, text=None):
        """ERROR (#2): goes only to the sender and changes no state."""
        log(f"ERROR {code} -> {conn.label()}")
        self.send(conn, "ERROR", {"code": code,
                                  "message": text or ERROR_TEXT[code],
                                  "rejected_type": rejected_type})

    def reject_and_close(self, conn, code):
        """ROOM_FULL and VERSION_MISMATCH (#3): ERROR, then close once sent."""
        self.send_error(conn, code, "CONNECT")
        conn.closing = True

    def reachable(self, conn):
        """A player the server can still send GAME_OVER to (#5)."""
        return self.net.is_open(conn) and not conn.closing

    # ----- dispatch (blueprint #2, "Server handling") -----

    def handle(self, conn, message):
        """Run the handler for a message that already passed validate()."""
        handlers = {
            "CONNECT": self.on_connect,
            "PLACE_FLEET": self.on_place_fleet,
            "MOVE": self.on_move,
            "DISCONNECT": self.on_disconnect,
        }
        handlers[message["msg_type"]](conn, message["payload"])

    def on_connect(self, conn, payload):
        """CONNECT steps 2 to 6 (#2). Step 1 (player_id null) is validate's."""
        if conn.player_id is not None:                 # step 2
            self.send_error(conn, "WRONG_PHASE", "CONNECT",
                            "You already have a seat in this game.")
            return
        if payload["version"] != VERSION:              # step 3
            self.reject_and_close(conn, "VERSION_MISMATCH")
            return
        if self.state != "WAITING_FOR_PLAYERS" or len(self.seats) == 2:
            self.reject_and_close(conn, "ROOM_FULL")   # step 6
            return
        # Step 4: the next seat in join order. Only Player_1 can be seated
        # in the lobby, so a freed seat is always Player_1's.
        player_id = "Player_1" if "Player_1" not in self.seats else "Player_2"
        conn.player_id = player_id
        self.seats[player_id] = conn
        self.names[player_id] = payload["display_name"]
        log(f"{conn.label()} joined as {payload['display_name']}")
        self.send(conn, "LOBBY_WAIT", {"assigned_id": player_id,
                                       "players_connected": len(self.seats)})
        if len(self.seats) == 2:                       # step 5
            self.start_game()

    def start_game(self):
        """GAME_START (transient): GAME_START to both, placement timers."""
        self.transition("GAME_START")
        now = time.monotonic()
        self.placement_started = {pid: now for pid in PLAYER_IDS}
        self.transition("FLEET_PLACEMENT")
        for pid in PLAYER_IDS:
            self.send(self.seats[pid], "GAME_START", {
                "opponent_name": self.names[other(pid)],
                "board_size": BOARD_SIZE,
                "fleet": FLEET,
            })

    def on_place_fleet(self, conn, payload):
        """PLACE_FLEET steps 1 to 5 (#2), FSM FLEET_PLACEMENT."""
        pid = conn.player_id
        if self.state != "FLEET_PLACEMENT" or pid in self.fleets:   # step 1
            self.send_error(conn, "WRONG_PHASE", "PLACE_FLEET")
            return
        fleet = check_layout(payload["ships"])                      # step 2
        if fleet is None:                                           # step 3
            self.send_error(conn, "INVALID_PLACEMENT", "PLACE_FLEET")
            return
        self.fleets[pid] = fleet                                    # step 4
        del self.placement_started[pid]     # stop this player's timer
        log(f"{pid} fleet accepted")
        if len(self.fleets) < 2:
            self.send(conn, "FLEET_ACCEPTED", {"opponent_ready": False})
            return
        # Step 5: both fleets stored. Turns begin with Player_1 active.
        # State changes first, then the messages (concurrency 4.2 step 1).
        self.active_player = "Player_1"
        self.turn_started = time.monotonic()
        self.transition("PLAYER_TURN")
        self.send(conn, "FLEET_ACCEPTED", {"opponent_ready": True})
        self.broadcast_state()

    def on_move(self, conn, payload):
        """MOVE (#2): PLAYER_TURN, EVALUATE_MOVE, CHECK_WIN."""
        pid = conn.player_id
        if self.state != "PLAYER_TURN":                             # check 1
            self.send_error(conn, "WRONG_PHASE", "MOVE")
            return
        if pid != self.active_player:                               # check 2
            self.send_error(conn, "OUT_OF_TURN", "MOVE",
                            "It is not your turn. "
                            f"Waiting for {self.active_player}.")
            return
        self.transition("EVALUATE_MOVE")
        cell = (payload["row"], payload["col"])
        if not on_board(*cell):                                     # check 3
            self.send_error(conn, "INVALID_COORD", "MOVE")
            self.transition("PLAYER_TURN")     # same turn, timer running
            return
        if cell in self.fired[pid]:                                 # check 4
            self.send_error(conn, "ALREADY_FIRED", "MOVE")
            self.transition("PLAYER_TURN")
            return
        self.turn_started = None               # valid shot: stop the timer
        self.fired[pid].append(cell)
        result, sunk = self.last_result(pid)
        log(f"{pid} fires at {cell_name(cell)}: {result}"
            + (f" ({sunk})" if sunk else ""))
        self.transition("CHECK_WIN")
        defender = other(pid)
        if self.ships_remaining(defender) == 0:
            self.end_game(pid, "FLEET_DESTROYED")
            return
        self.active_player = defender          # flip only here (FSM #6)
        self.turn_started = time.monotonic()
        self.transition("PLAYER_TURN")
        self.broadcast_state()

    def on_disconnect(self, conn, payload):
        """DISCONNECT (#2): no reply; the sender is a lost player (FSM #3)."""
        log(f"{conn.label()} sent DISCONNECT")
        self.player_lost(conn)

    # ----- scores and boards, computed from fleets + fired cells (#4) -----

    def ship_at(self, owner, cell):
        """Name of owner's ship on this cell, or None for water."""
        for name, cells in self.fleets.get(owner, {}).items():
            if cell in cells:
                return name
        return None

    def is_sunk(self, owner, name):
        """Every cell of the ship has been fired at by the opponent."""
        shots = self.fired[other(owner)]
        return all(cell in shots for cell in self.fleets[owner][name])

    def ships_remaining(self, owner):
        """Ships with at least one cell not hit (STATE_UPDATE)."""
        return sum(1 for name in self.fleets.get(owner, {})
                   if not self.is_sunk(owner, name))

    def last_result(self, shooter):
        """HIT, MISS, or SUNK for the shooter's last cell (#2, last_shot)."""
        name = self.ship_at(other(shooter), self.fired[shooter][-1])
        if name is None:
            return "MISS", None
        if self.is_sunk(other(shooter), name):
            return "SUNK", name
        return "HIT", None

    def own_board(self, owner):
        """your_board / opponent_board (#4): own ships, opponent's shots."""
        shots = set(self.fired[other(owner)])
        rows = []
        for r in range(BOARD_SIZE):
            row = ""
            for c in range(BOARD_SIZE):
                name = self.ship_at(owner, (r, c))
                if name is None:
                    row += "O" if (r, c) in shots else "."
                elif self.is_sunk(owner, name):
                    row += "#"
                else:
                    row += "X" if (r, c) in shots else "S"
            rows.append(row)
        return rows

    def tracking_grid(self, shooter):
        """tracking_grid (#4): shooter's hits and misses, never an "S"."""
        defender, shots = other(shooter), set(self.fired[shooter])
        rows = []
        for r in range(BOARD_SIZE):
            row = ""
            for c in range(BOARD_SIZE):
                name = self.ship_at(defender, (r, c))
                if (r, c) not in shots:
                    row += "."
                elif name is None:
                    row += "O"
                else:
                    row += "#" if self.is_sunk(defender, name) else "X"
            rows.append(row)
        return rows

    def stats(self):
        """GAME_OVER stats (#2): valid shots and hits per player."""
        return {pid: {"shots": len(self.fired[pid]),
                      "hits": sum(1 for cell in self.fired[pid]
                                  if self.ship_at(other(pid), cell))}
                for pid in PLAYER_IDS}

    def broadcast_state(self):
        """STATE_UPDATE to each player, its own view, in one step (4.2)."""
        shooter = other(self.active_player)
        last_shot = None
        if self.fired[shooter]:                # null before any shot
            row, col = self.fired[shooter][-1]
            result, sunk = self.last_result(shooter)
            last_shot = {"shooter": shooter, "row": row, "col": col,
                         "result": result, "ship_sunk": sunk}
        shared = {
            "active_player": self.active_player,
            "last_shot": last_shot,
            "ships_remaining": {pid: self.ships_remaining(pid)
                                for pid in PLAYER_IDS},
            "shots_fired": sum(len(self.fired[pid]) for pid in PLAYER_IDS),
        }
        for pid in PLAYER_IDS:
            self.send(self.seats[pid], "STATE_UPDATE", {
                "active_player": shared["active_player"],
                "your_board": self.own_board(pid),
                "tracking_grid": self.tracking_grid(pid),
                "last_shot": shared["last_shot"],
                "ships_remaining": shared["ships_remaining"],
                "shots_fired": shared["shots_fired"],
            })

    # ----- game end, lost players, cleanup (#5, FSM #3) -----

    def end_game(self, winner, reason):
        """Enter GAME_OVER: GAME_OVER to each reachable player (#5)."""
        self.transition("GAME_OVER")
        self.placement_started, self.turn_started = {}, None
        self.game_over_at = time.monotonic()   # 10 s game over timer
        in_turns = len(self.fleets) == 2       # else it ended in placement
        stats = self.stats()
        reachable = [pid for pid in PLAYER_IDS
                     if pid in self.seats and self.reachable(self.seats[pid])]
        log(f"game over: winner {winner}, {reason}")
        for pid in reachable:
            conn = self.seats[pid]
            self.send(conn, "GAME_OVER", {
                "winner": winner,
                "reason": reason,
                "stats": stats,
                "your_board": self.own_board(pid),
                "opponent_board":
                    self.own_board(other(pid)) if in_turns else None,
            })
            conn.closing = True     # read and discard from now on (#5 step 2)
        if not reachable:
            self.cleanup()

    def player_lost(self, conn, flush=False):
        """trigger_state_transition("CLIENT_DISCONNECTED", conn) (#7).

        The socket is closed right away and its buffers dropped, except with
        flush=True (FRAME_TOO_LARGE), where the queued ERROR is sent first.
        Then the game reacts as fsm_specification.md #3 says.
        """
        if not self.net.is_open(conn):
            return
        pid = conn.player_id
        seated = pid is not None and self.seats.get(pid) is conn
        if flush:
            conn.closing = True
        else:
            self.net.close_now(conn)
        if not seated:
            return                      # no seat: no game is affected
        log(f"{pid} lost in {self.state}")
        if self.state == "WAITING_FOR_PLAYERS":
            del self.seats[pid]         # lobby: wipe the ID, free the slot
            del self.names[pid]
            conn.player_id = None
        elif self.state in ("FLEET_PLACEMENT", "PLAYER_TURN"):
            if self.reachable(self.seats[other(pid)]):
                winner = other(pid) if self.state == "PLAYER_TURN" else None
                self.end_game(winner, "OPPONENT_DISCONNECTED")
            else:
                self.cleanup()          # both lost: nothing is sent
        # In GAME_OVER, closing the socket is all; on_closed does the rest.

    def on_closed(self, conn):
        """GAME_OVER -> CLEANUP once both player sockets are closed."""
        if self.state == "GAME_OVER" and not any(
                self.net.is_open(c) for c in self.seats.values()):
            self.cleanup()

    def cleanup(self):
        """CLEANUP (transient): close the rest, wipe, back to the lobby."""
        self.transition("CLEANUP")
        for conn in list(self.seats.values()):
            self.net.close_now(conn)    # unsent bytes are dropped
        self.reset()
        self.transition("WAITING_FOR_PLAYERS")

    def check_timers(self, now):
        """Placement, turn, and game over timers (#5, Timeouts)."""
        expired = []
        if self.state == "FLEET_PLACEMENT":
            expired = [pid for pid, start in self.placement_started.items()
                       if now - start >= PLACEMENT_TIMEOUT]
        elif self.state == "PLAYER_TURN":
            if now - self.turn_started >= TURN_TIMEOUT:
                expired = [self.active_player]
        elif self.state == "GAME_OVER":
            if now - self.game_over_at >= GAME_OVER_TIMEOUT:
                log("game over timer ran out: closing what is left")
                self.cleanup()
            return
        if len(expired) == 2:
            log("both players timed out")
            self.cleanup()              # both lost: straight to CLEANUP
        elif expired:
            log(f"{expired[0]} timed out (500 s)")
            self.player_lost(self.seats[expired[0]])
