"""Battleship game server (CS 457).

Usage:  python3 server.py -p <port>      (5000 in the CML deployment)

One thread, one selectors.DefaultSelector, non-blocking sockets, and a
receive and send buffer per connection (docs/concurrency_design.md #2).
The game rules live in game.py, the MALFORMED checks in validate.py, and
the framing in framing.py.
"""

import argparse
import selectors
import socket
import sys
import time

from framing import MAX_BUFFER, FrameBuffer, encode_message
from game import Game, log
from validate import validate

TICK = 1.0             # concurrency 2.4: an idle loop wakes once a second
RECV_SIZE = 4096       # blueprint #6 step 2: one recv(4096) per readiness
CONNECT_TIMEOUT = 30   # blueprint #5, Timeouts: 30 s to get a seat


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
    """Server CLI: -h (help) and -p <port> (required)."""
    parser = argparse.ArgumentParser(
        description="Battleship game server for CS 457. Listens on "
                    "0.0.0.0 (every interface) for two players.",
        epilog="example: python3 server.py -p 5000")
    parser.add_argument("-p", dest="port", metavar="PORT", required=True,
                        type=port_number,
                        help="TCP port to listen on, 1024 to 65535 "
                             "(5000 in the CML deployment)")
    return parser.parse_args()


class Connection:
    """Everything that belongs to one client socket (concurrency 2.2).

    Kept on the selector key's data. Nothing here belongs to the game.
    """

    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.frames = FrameBuffer()     # receive buffer (blueprint #6)
        self.out = bytearray()          # send buffer: whole frames, in order
        self.player_id = None           # set when CONNECT is accepted
        self.closing = False            # set at teardown (concurrency 2.5)
        self.connected_at = time.monotonic()   # 30 s connect timer

    def label(self):
        """How the log names this connection."""
        return self.player_id or f"{self.addr[0]}:{self.addr[1]}"


class Server:
    """The event loop and the socket side of the server (concurrency 2.6)."""

    def __init__(self):
        self.sel = selectors.DefaultSelector()
        self.conns = set()              # every open client connection
        self.game = Game(self)

    def open_listener(self, port):
        """INIT (concurrency 2.1): bind 0.0.0.0:<port>, register as None."""
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind(("0.0.0.0", port))
        lsock.listen()
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)
        log(f"listening on 0.0.0.0:{port}")
        self.game.transition("WAITING_FOR_PLAYERS")

    def on_accept(self, lsock):
        """Accept (concurrency 2.2): no seat until CONNECT."""
        try:
            sock, addr = lsock.accept()
        except (BlockingIOError, ConnectionAbortedError):
            return              # the client left before we got to it
        except OSError:
            return              # e.g. out of file descriptors; next pass
        sock.setblocking(False)
        conn = Connection(sock, addr)
        self.conns.add(conn)
        self.sel.register(sock, selectors.EVENT_READ, data=conn)
        log(f"accepted connection from {conn.label()}")

    def is_open(self, conn):
        """A closed socket reports fileno -1 (concurrency 2.6)."""
        return conn.sock.fileno() != -1

    def queue_message(self, conn, message):
        """Add one whole frame to conn.out (blueprint #5, #7).

        Nothing is queued to a closing connection. Over 64 KB waiting means
        the client is not reading: that player is lost (#5 row 7).
        """
        if conn.closing or not self.is_open(conn):
            return
        conn.out += encode_message(message)
        if len(conn.out) > MAX_BUFFER:
            log(f"send buffer over 64 KB for {conn.label()}")
            conn.out.clear()
            self.game.player_lost(conn)
            return
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.modify(conn.sock, events, data=conn)

    def close_now(self, conn):
        """Closing a Socket Safely (#7): unregister first, then close."""
        if not self.is_open(conn):
            return
        self.sel.unregister(conn.sock)
        conn.sock.close()
        conn.out.clear()
        self.conns.discard(conn)
        log(f"closed connection {conn.label()}")
        self.game.on_closed(conn)

    def on_readable(self, conn):
        """Read handler (blueprint #6 The Receiver Algorithm, #7 In Code)."""
        try:
            data = conn.sock.recv(RECV_SIZE)
        except BlockingIOError:
            return                      # not ready after all; not a loss
        except (ConnectionResetError, ConnectionAbortedError):
            self.game.player_lost(conn)     # abrupt drop (#5 row 4)
            return
        if data == b"":
            self.game.player_lost(conn)     # clean close, EOF (#5 row 3)
            return
        if conn.closing:
            return                      # read, but thrown away (#5 step 2)
        for message in conn.frames.feed(data):
            if message is None:
                self.game.send_error(conn, "MALFORMED", None)
            else:
                self.dispatch(conn, message)
            if conn.closing or not self.is_open(conn):
                return                  # the rest of this recv() is dropped
        if conn.frames.too_large:       # step 8 (#5 row 6)
            self.game.send_error(conn, "FRAME_TOO_LARGE", None)
            self.game.player_lost(conn, flush=True)

    def dispatch(self, conn, message):
        """Shape checks first (MALFORMED, #3), then the FSM (game.py)."""
        problem = validate(message, conn)
        if problem is not None:
            code, rejected_type = problem
            self.game.send_error(conn, code, rejected_type)
            return
        self.game.handle(conn, message)

    def on_writable(self, conn):
        """Write handler (#7 In Code): one send(), keep what did not go."""
        try:
            sent = conn.sock.send(conn.out)
        except BlockingIOError:
            return                      # OS buffer full; try again later
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.game.player_lost(conn)     # the peer is gone (#5 row 4)
            return
        del conn.out[:sent]
        if not conn.out:
            self.sel.modify(conn.sock, selectors.EVENT_READ, data=conn)

    def check_timers(self, now):
        """30 s connect timer here, then the game's timers (#5, Timeouts)."""
        for conn in list(self.conns):
            if conn.player_id is None and \
                    now - conn.connected_at >= CONNECT_TIMEOUT:
                log(f"{conn.label()} never got a seat (30 s)")
                self.close_now(conn)
            elif conn.closing and not conn.out:
                self.close_now(conn)    # last message sent, now close
        self.game.check_timers(now)

    def run(self):
        """The event loop (concurrency 2.6). The only wait is select()."""
        while True:
            for key, mask in self.sel.select(timeout=TICK):
                conn = key.data
                if conn is None:
                    self.on_accept(key.fileobj)
                    continue
                if mask & selectors.EVENT_READ and self.is_open(conn):
                    self.on_readable(conn)
                if mask & selectors.EVENT_WRITE and self.is_open(conn):
                    self.on_writable(conn)
                if conn.closing and not conn.out and self.is_open(conn):
                    self.close_now(conn)    # GAME_OVER or ERROR sent
            self.check_timers(time.monotonic())


def main():
    args = parse_args()
    server = Server()
    try:
        server.open_listener(args.port)     # INIT
    except OSError as error:
        print(f"[ERROR] Cannot listen on 0.0.0.0:{args.port}: "
              f"{error.strerror or error}. Is another server using it?")
        sys.exit(1)
    try:
        server.run()
    except KeyboardInterrupt:
        log("server stopped (Ctrl+C)")


if __name__ == "__main__":
    main()
