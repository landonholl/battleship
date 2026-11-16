"""Battleship console client (CS 457).

Usage:  python3 client.py -i <server hostname> -p <port>
        e.g. python3 client.py -i server.holland.edu -p 5000

The client keeps no game state. It draws what the server sends and only
asks the player for input when the protocol says it is their move
(blueprint #2, "Client handling" of each message). It is one player's
console, so it may block on its own socket and on input().
"""

import argparse
import random
import select
import socket
import string
import sys
from collections import deque

from framing import FrameBuffer, build_message, encode_message
from validate import NAME_PATTERN

VERSION = "0.0"        # blueprint #2, CONNECT
RECV_SIZE = 4096       # blueprint #6 step 2
# ERROR codes after which the server closes the connection (blueprint #3).
CLOSING_CODES = ("ROOM_FULL", "VERSION_MISMATCH", "FRAME_TOO_LARGE")
LEGEND = "S ship   X hit   # sunk   O miss   . water / not fired at"


class QuitGame(Exception):
    """The player typed quit (or stdin closed)."""


# ----- command line and connection (Sprint 3 2.1, 2.2; SOW 5.3) -----

def port_number(text):
    """argparse type for -p: an integer from 1024 to 65535."""
    try:
        port = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a port number")
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError(
            f"{port} is out of range (use 1024 to 65535)")
    return port


def parse_args():
    """Client CLI: -h (help), -i <hostname> and -p <port> (both required)."""
    parser = argparse.ArgumentParser(
        description="Battleship console client for CS 457. Connects to the "
                    "game server over TCP.",
        epilog="example: python3 client.py -i server.holland.edu -p 5000")
    parser.add_argument("-i", dest="host", metavar="SERVER_HOSTNAME",
                        required=True,
                        help="server DNS hostname (or IP address), resolved "
                             "through DNS, e.g. server.holland.edu")
    parser.add_argument("-p", dest="port", metavar="PORT", required=True,
                        type=port_number,
                        help="server TCP port, 1024 to 65535 "
                             "(5000 in the CML deployment)")
    return parser.parse_args()


def resolve(hostname):
    """DNS lookup (SOW 5.3). A failed lookup exits cleanly with status 1."""
    try:
        return socket.gethostbyname(hostname)
    except (socket.gaierror, UnicodeError):
        print(f"[ERROR] Unable to resolve DNS hostname '{hostname}'.")
        print("Please check your Cisco router DNS configuration "
              "('ip dns server' / 'ip host') or verify domain spelling.")
        sys.exit(1)


def connect(hostname, ip, port):
    """TCP connect. Reported apart from a DNS failure (SOW 5.3)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((ip, port))
    except ConnectionRefusedError:
        print(f"[ERROR] {hostname} ({ip}) refused the connection on port "
              f"{port}. Is server.py running there with -p {port}?")
        sys.exit(1)
    except OSError as error:
        print(f"[ERROR] Could not reach {hostname} ({ip}) on port {port}: "
              f"{error.strerror or error}.")
        sys.exit(1)
    return sock


class ServerLink:
    """The client's one connection: framing.py out, FrameBuffer in (#6)."""

    def __init__(self, sock):
        self.sock = sock
        self.frames = FrameBuffer()
        self.pending = deque()          # complete messages not handled yet
        self.player_id = None           # from LOBBY_WAIT (#1)

    def send(self, msg_type, payload):
        """Send one framed message with this client's player_id (#1, #6)."""
        frame = encode_message(build_message(msg_type, self.player_id,
                                             payload))
        try:
            self.sock.sendall(frame)
        except OSError:
            lost_connection()

    def receive(self):
        """Next complete message, or None on EOF or reset (#6, #7)."""
        while not self.pending:
            # Wait at most 0.5 s at a time so Ctrl+C also works on Windows.
            ready, _, _ = select.select([self.sock], [], [], 0.5)
            if not ready:
                continue
            try:
                data = self.sock.recv(RECV_SIZE)
            except (ConnectionResetError, ConnectionAbortedError):
                return None
            if data == b"":
                return None             # the 0 byte EOF rule (#7)
            for message in self.frames.feed(data):
                if message is None:
                    print("[warning] ignored a malformed server message")
                else:
                    self.pending.append(message)
        return self.pending.popleft()


def lost_connection():
    """Connection ended without GAME_OVER (blueprint #5)."""
    print("\n[ERROR] The connection to the server was lost.")
    sys.exit(1)


# ----- input -----

def ask(prompt):
    """input(). Echoes the answer when stdin is piped, so logs show it."""
    try:
        answer = input(prompt)
    except EOFError:
        raise QuitGame()
    if not sys.stdin.isatty():
        print(answer)
    return answer.strip()


def parse_cell(text):
    """'B7' -> (1, 6): the letter is the row, the number the column (#2)."""
    text = text.strip().upper()
    if len(text) < 2 or text[0] not in string.ascii_uppercase \
            or not text[1:].isdecimal():
        return None
    return ord(text[0]) - ord("A"), int(text[1:]) - 1


def cell_name(row, col):
    """(1, 6) -> 'B7'."""
    return f"{chr(ord('A') + row)}{col + 1}"


# ----- drawing (blueprint #4, Sprint 3 2.4) -----

def grid_lines(grid):
    """A grid with row letters A, B, ... and column numbers 1, 2, ..."""
    lines = ["  " + "".join(f"{c + 1:>3}" for c in range(len(grid)))]
    for r, row in enumerate(grid):
        lines.append(f" {chr(ord('A') + r)}"
                     + "".join(f"{ch:>3}" for ch in row))
    return lines


def print_grids(left_title, left, right_title=None, right=None):
    """One grid, or two side by side."""
    a = grid_lines(left)
    if right is None:
        print(left_title)
        print("\n".join(a))
        return
    b = grid_lines(right)
    width = len(a[0]) + 5
    print(f"{left_title:<{width}}{right_title}")
    for x, y in zip(a, b):
        print(f"{x:<{width}}{y}")


# ----- fleet placement (blueprint #2, GAME_START client handling) -----

def ship_cells(row, col, length, orientation):
    """Cells a ship covers: "H" runs right, "V" runs down (#2)."""
    if orientation == "H":
        return [(row, col + i) for i in range(length)]
    return [(row + i, col) for i in range(length)]


def fits(cells, taken, size):
    """On the board and not on another ship. The server checks again."""
    return all(0 <= r < size and 0 <= c < size and (r, c) not in taken
               for r, c in cells)


def preview(size, taken):
    """The fleet placed so far."""
    grid = ["".join("S" if (r, c) in taken else "." for c in range(size))
            for r in range(size)]
    print_grids("Your fleet so far", grid)


def random_layout(size, fleet):
    """Place every ship from GAME_START's fleet at random."""
    ships, taken = [], set()
    for ship in fleet:
        while True:
            orientation = random.choice("HV")
            row, col = random.randrange(size), random.randrange(size)
            cells = ship_cells(row, col, ship["length"], orientation)
            if fits(cells, taken, size):
                break
        taken.update(cells)
        ships.append({"name": ship["name"], "row": row, "col": col,
                      "orientation": orientation})
    preview(size, taken)
    return ships


def choose_layout(size, fleet):
    """Ask for each ship as 'A1 H', or 'r' to place them all at random."""
    print(f"\nPlace your fleet on the {size}x{size} board. For each ship "
          "type its start cell and H (runs right) or V (runs down), "
          "e.g. A1 H.")
    print("Type r to place the whole fleet at random, or quit to leave.")
    ships, taken = [], set()
    for ship in fleet:
        preview(size, taken)
        while True:
            answer = ask(f"{ship['name']} (length {ship['length']}): ")
            answer = answer.upper()
            if answer == "QUIT":
                raise QuitGame()
            if answer == "R":
                return random_layout(size, fleet)
            parts = answer.split()
            cell = parse_cell(parts[0]) if len(parts) == 2 else None
            if cell is None or parts[1] not in ("H", "V"):
                print("  Type a start cell and H or V, e.g. A1 H")
                continue
            cells = ship_cells(*cell, ship["length"], parts[1])
            if not fits(cells, taken, size):
                print("  That runs off the board or onto another ship.")
                continue
            break
        taken.update(cells)
        ships.append({"name": ship["name"], "row": cell[0], "col": cell[1],
                      "orientation": parts[1]})
    preview(size, taken)
    return ships


# ----- the game, one handler per server message type (blueprint #2) -----

class Match:
    """What the client remembers: names and the rules from GAME_START."""

    def __init__(self, link, my_name):
        self.link = link
        self.my_name = my_name
        self.opp_name = "opponent"
        self.board_size = 0
        self.fleet = []

    def opp_id(self):
        return "Player_2" if self.link.player_id == "Player_1" \
            else "Player_1"

    def name_of(self, player_id):
        if player_id == self.link.player_id:
            return f"you ({self.my_name})"
        return f"{self.opp_name} ({player_id})"

    def send_fleet(self):
        """PLACE_FLEET (#2)."""
        ships = choose_layout(self.board_size, self.fleet)
        self.link.send("PLACE_FLEET", {"ships": ships})
        print("Fleet sent. Waiting for the server to check it...")

    def ask_move(self):
        """MOVE (#2): only when STATE_UPDATE names this player."""
        while True:
            answer = ask("Fire at (e.g. B7, or quit): ").upper()
            if answer == "QUIT":
                raise QuitGame()
            cell = parse_cell(answer)
            if cell is not None:
                break
            print("  Type a row letter and a column number, e.g. B7")
        self.link.send("MOVE", {"row": cell[0], "col": cell[1]})

    def on_lobby_wait(self, p):
        """LOBBY_WAIT: store the assigned ID and use it from now on."""
        self.link.player_id = p["assigned_id"]
        print(f"Joined as {p['assigned_id']} ({self.my_name}).")
        if p["players_connected"] == 1:
            print("Waiting for Player 2 to join...")

    def on_game_start(self, p):
        """GAME_START: store the rules, then place the fleet."""
        self.opp_name = p["opponent_name"]
        self.board_size = p["board_size"]
        self.fleet = p["fleet"]
        print(f"\n=== GAME START: you ({self.link.player_id}) vs "
              f"{self.opp_name} ({self.opp_id()}) ===")
        self.send_fleet()

    def on_fleet_accepted(self, p):
        """FLEET_ACCEPTED: the fleet is final."""
        if p["opponent_ready"]:
            print("Fleet accepted. Both fleets are placed: the battle "
                  "begins!")
        else:
            print(f"Fleet accepted. Waiting for {self.opp_name} to place "
                  "their fleet...")

    def on_state_update(self, p):
        """STATE_UPDATE: redraw, show the last shot, prompt or wait."""
        me, opp = self.link.player_id, self.opp_id()
        print("\n" + "=" * 62)
        shot = p["last_shot"]
        if shot is not None:
            where = cell_name(shot["row"], shot["col"])
            who = "You" if shot["shooter"] == me else self.opp_name
            text = f"{who} fired at {where}: {shot['result']}"
            if shot["ship_sunk"]:
                whose = "their" if shot["shooter"] == me else "your"
                text += f", sank {whose} {shot['ship_sunk']}!"
            print(text)
        print_grids(f"Your fleet ({self.my_name})", p["your_board"],
                    f"Your shots at {self.opp_name}", p["tracking_grid"])
        print(LEGEND)
        left = p["ships_remaining"]
        print(f"Score: ships afloat: you {left.get(me)}, {self.opp_name} "
              f"{left.get(opp)}  |  shots fired this game: "
              f"{p['shots_fired']}")
        if p["active_player"] == me:
            print(">>> Your Turn <<<")
            self.ask_move()
        else:
            print(f"Waiting for {self.opp_name} ({opp}) to fire...")

    def on_error(self, p):
        """ERROR: show it, then retry what failed (#2, ERROR)."""
        print(f"[server] {p['code']}: {p['message']}")
        code, rejected = p["code"], p["rejected_type"]
        if code in CLOSING_CODES:
            print("The server closed the connection.")
            sys.exit(1)
        if rejected == "PLACE_FLEET" and code in ("INVALID_PLACEMENT",
                                                  "MALFORMED"):
            self.send_fleet()
        elif rejected == "MOVE" and code in ("INVALID_COORD",
                                             "ALREADY_FIRED", "MALFORMED"):
            self.ask_move()

    def on_game_over(self, p):
        """GAME_OVER: result, score table, both boards (#2, #5)."""
        me, winner = self.link.player_id, p["winner"]
        print("\n" + "#" * 62 + "\nGAME OVER")
        if winner is None:
            print(f"{self.opp_name} left during fleet placement. "
                  "No winner.")
        elif winner == me and p["reason"] == "FLEET_DESTROYED":
            print(f"YOU WIN! You sank all of {self.opp_name}'s ships.")
        elif winner == me:
            print(f"YOU WIN by forfeit: {self.opp_name} left the game.")
        else:
            print(f"YOU LOSE. {self.opp_name} sank your whole fleet.")
        print(f"\n{'Final score':<26}{'Shots':>6}{'Hits':>6}{'Accuracy':>10}")
        for pid, s in p["stats"].items():
            accuracy = f"{100 * s['hits'] / s['shots']:.0f}%" \
                if s["shots"] else "-"
            print(f"{self.name_of(pid):<26}{s['shots']:>6}{s['hits']:>6}"
                  f"{accuracy:>10}")
        print()
        if p["opponent_board"] is not None:
            print_grids("Your final board", p["your_board"],
                        f"{self.opp_name}'s fleet revealed",
                        p["opponent_board"])
        else:
            print_grids("Your final board", p["your_board"])
        print(LEGEND)

    def play(self):
        """Handle server messages in arrival order until GAME_OVER."""
        handlers = {
            "LOBBY_WAIT": self.on_lobby_wait,
            "GAME_START": self.on_game_start,
            "FLEET_ACCEPTED": self.on_fleet_accepted,
            "STATE_UPDATE": self.on_state_update,
            "ERROR": self.on_error,
            "GAME_OVER": self.on_game_over,
        }
        while True:
            message = self.link.receive()
            if message is None:
                lost_connection()       # EOF without GAME_OVER (#5)
            handler = handlers.get(message.get("msg_type"))
            if handler is not None:     # unknown types are ignored
                handler(message.get("payload", {}))
            if message.get("msg_type") == "GAME_OVER":
                return                  # the EOF after it is expected


def ask_name():
    """display_name: 1 to 20 letters a to z (#2, CONNECT)."""
    while True:
        name = ask("Your display name (1 to 20 letters a-z): ").lower()
        if NAME_PATTERN.fullmatch(name):
            return name
        print("  Use only the letters a to z, no spaces, at most 20.")


def main():
    args = parse_args()
    ip = resolve(args.host)
    print(f"Resolved {args.host} -> {ip}")
    sock = connect(args.host, ip, args.port)
    print(f"Connected to {args.host} ({ip}) on port {args.port}.")
    link = ServerLink(sock)
    try:
        name = ask_name()
        link.send("CONNECT", {"display_name": name, "version": VERSION})
        Match(link, name).play()
    except (QuitGame, KeyboardInterrupt):
        if link.player_id is not None:
            try:
                link.sock.sendall(encode_message(
                    build_message("DISCONNECT", link.player_id, {})))
            except OSError:
                pass                    # already gone; nothing to tell
        print("\nYou left the game.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
