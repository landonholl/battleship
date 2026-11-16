# Sprint 3 Execution Log

**Course:** CS 457
**Written by:** Landon Holland

This is the console output of `server.py` and three `client.py` sessions on one machine over localhost (`127.0.0.1`), started with the same commands used on CML:

```text
python3 server.py -p 5000
python3 client.py -i localhost -p 5000      (alice, then bob, then eve)
```

The players' keyboard input was typed by a small script, one line at a time at about human speed, so the run can be repeated exactly. The client echoes each answer after its prompt when its input is not a terminal, so every line the player typed shows up in the log right after the prompt. Nothing below was edited.

## What the Run Shows

| Requirement | Where to look |
| ----------- | ------------- |
| Two clients connected at the same time | Server: `Player_1 joined as alice`, `Player_2 joined as bob` |
| FSM transitions | Server: every `[FSM] A -> B` line, from `INIT` through `CLEANUP` and back to `WAITING_FOR_PLAYERS` |
| At least 3 turns | 7 valid shots: alice B7, bob E4, alice B8 (sinks the Destroyer), bob F10, alice E5, bob A1, alice J1 |
| Turn status and scores | Clients: `>>> Your Turn <<<`, `Waiting for bob (Player_2) to fire...`, and the `Score:` line after every shot |
| `STATE_UPDATE` to both players | Both clients redraw after every valid shot, each with only their own fleet |
| Rejected moves change nothing | alice fires at B8 again (`ALREADY_FIRED`), then K1 (`INVALID_COORD`), and is asked again without losing the turn (blueprint #2, `MOVE`) |
| Client-side input checks | alice's first Carrier placement `A8 H` runs off the board and is asked again |
| A 3rd client while a game runs | eve gets `ROOM_FULL` and is closed. The game is not affected (blueprint #3) |
| Game end | bob types `quit`: the client sends `DISCONNECT`, alice wins by forfeit with `OPPONENT_DISCONNECTED` and sees both fleets (blueprint #5, row 2) |
| Reset for the next game | Server: `GAME_OVER -> CLEANUP -> WAITING_FOR_PLAYERS`, then a second full game on the same server (end of this log) |

## Game 1: Server

```text
[17:33:10] listening on 0.0.0.0:5000
[17:33:10] [FSM] INIT -> WAITING_FOR_PLAYERS
[17:33:11] accepted connection from 127.0.0.1:61870
[17:33:11] Player_1 joined as alice
[17:33:12] accepted connection from 127.0.0.1:61871
[17:33:13] Player_2 joined as bob
[17:33:13] [FSM] WAITING_FOR_PLAYERS -> GAME_START
[17:33:13] [FSM] GAME_START -> FLEET_PLACEMENT
[17:33:15] Player_1 fleet accepted
[17:33:18] Player_2 fleet accepted
[17:33:18] [FSM] FLEET_PLACEMENT -> PLAYER_TURN
[17:33:18] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:18] Player_1 fires at B7: HIT
[17:33:18] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:18] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:19] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:19] Player_2 fires at E4: HIT
[17:33:19] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:19] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:19] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:19] Player_1 fires at B8: SUNK (Destroyer)
[17:33:19] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:19] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:20] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:20] Player_2 fires at F10: MISS
[17:33:20] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:20] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:20] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:20] ERROR ALREADY_FIRED -> Player_1
[17:33:20] [FSM] EVALUATE_MOVE -> PLAYER_TURN
[17:33:20] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:20] ERROR INVALID_COORD -> Player_1
[17:33:20] [FSM] EVALUATE_MOVE -> PLAYER_TURN
[17:33:20] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:20] Player_1 fires at E5: HIT
[17:33:20] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:20] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:21] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:21] Player_2 fires at A1: HIT
[17:33:21] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:21] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:21] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:21] Player_1 fires at J1: HIT
[17:33:21] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:21] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:21] accepted connection from 127.0.0.1:61872
[17:33:22] ERROR ROOM_FULL -> 127.0.0.1:61872
[17:33:22] closed connection 127.0.0.1:61872
[17:33:22] Player_2 sent DISCONNECT
[17:33:22] closed connection Player_2
[17:33:22] Player_2 lost in PLAYER_TURN
[17:33:22] [FSM] PLAYER_TURN -> GAME_OVER
[17:33:22] game over: winner Player_1, OPPONENT_DISCONNECTED
[17:33:22] closed connection Player_1
[17:33:22] [FSM] GAME_OVER -> CLEANUP
[17:33:22] [FSM] CLEANUP -> WAITING_FOR_PLAYERS
```

## Game 1: Client 1 (alice, `Player_1`)

```text
Resolved localhost -> 127.0.0.1
Connected to localhost (127.0.0.1) on port 5000.
Your display name (1 to 20 letters a-z): alice
Joined as Player_1 (alice).
Waiting for Player 2 to join...

=== GAME START: you (Player_1) vs bob (Player_2) ===

Place your fleet on the 10x10 board. For each ship type its start cell and H (runs right) or V (runs down), e.g. A1 H.
Type r to place the whole fleet at random, or quit to leave.
Your fleet so far
    1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  .  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  .  .  .
 J  .  .  .  .  .  .  .  .  .  .
Carrier (length 5): A8 H
  That runs off the board or onto another ship.
Carrier (length 5): A1 H
Your fleet so far
    1  2  3  4  5  6  7  8  9 10
 A  S  S  S  S  S  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  .  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  .  .  .
 J  .  .  .  .  .  .  .  .  .  .
Battleship (length 4): C4 V
Your fleet so far
    1  2  3  4  5  6  7  8  9 10
 A  S  S  S  S  S  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  S  .  .  .  .  .  .
 D  .  .  .  S  .  .  .  .  .  .
 E  .  .  .  S  .  .  .  .  .  .
 F  .  .  .  S  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  .  .  .
 J  .  .  .  .  .  .  .  .  .  .
Cruiser (length 3): G6 H
Your fleet so far
    1  2  3  4  5  6  7  8  9 10
 A  S  S  S  S  S  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  S  .  .  .  .  .  .
 D  .  .  .  S  .  .  .  .  .  .
 E  .  .  .  S  .  .  .  .  .  .
 F  .  .  .  S  .  .  .  .  .  .
 G  .  .  .  .  .  S  S  S  .  .
 H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  .  .  .
 J  .  .  .  .  .  .  .  .  .  .
Submarine (length 3): H2 V
Your fleet so far
    1  2  3  4  5  6  7  8  9 10
 A  S  S  S  S  S  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  S  .  .  .  .  .  .
 D  .  .  .  S  .  .  .  .  .  .
 E  .  .  .  S  .  .  .  .  .  .
 F  .  .  .  S  .  .  .  .  .  .
 G  .  .  .  .  .  S  S  S  .  .
 H  .  S  .  .  .  .  .  .  .  .
 I  .  S  .  .  .  .  .  .  .  .
 J  .  S  .  .  .  .  .  .  .  .
Destroyer (length 2): J9 H
Your fleet so far
    1  2  3  4  5  6  7  8  9 10
 A  S  S  S  S  S  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  S  .  .  .  .  .  .
 D  .  .  .  S  .  .  .  .  .  .
 E  .  .  .  S  .  .  .  .  .  .
 F  .  .  .  S  .  .  .  .  .  .
 G  .  .  .  .  .  S  S  S  .  .
 H  .  S  .  .  .  .  .  .  .  .
 I  .  S  .  .  .  .  .  .  .  .
 J  .  S  .  .  .  .  .  .  S  S
Fleet sent. Waiting for the server to check it...
Fleet accepted. Waiting for bob to place their fleet...

==============================================================
Your fleet (alice)                   Your shots at bob
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  S  S  S  S  S  .  .  .  .  .      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .      B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  S  .  .  .  .  .  .      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  S  .  .  .  .  .  .      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  S  .  .  .  .  .  .      E  .  .  .  .  .  .  .  .  .  .
 F  .  .  .  S  .  .  .  .  .  .      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  S  S  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  S  .  .  .  .  .  .  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  S  .  .  .  .  .  .  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  .  S  .  .  .  .  .  .  S  S      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 5, bob 5  |  shots fired this game: 0
>>> Your Turn <<<
Fire at (e.g. B7, or quit): B7

==============================================================
You fired at B7: HIT
Your fleet (alice)                   Your shots at bob
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  S  S  S  S  S  .  .  .  .  .      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .      B  .  .  .  .  .  .  X  .  .  .
 C  .  .  .  S  .  .  .  .  .  .      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  S  .  .  .  .  .  .      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  S  .  .  .  .  .  .      E  .  .  .  .  .  .  .  .  .  .
 F  .  .  .  S  .  .  .  .  .  .      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  S  S  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  S  .  .  .  .  .  .  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  S  .  .  .  .  .  .  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  .  S  .  .  .  .  .  .  S  S      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 5, bob 5  |  shots fired this game: 1
Waiting for bob (Player_2) to fire...

==============================================================
bob fired at E4: HIT
Your fleet (alice)                   Your shots at bob
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  S  S  S  S  S  .  .  .  .  .      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .      B  .  .  .  .  .  .  X  .  .  .
 C  .  .  .  S  .  .  .  .  .  .      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  S  .  .  .  .  .  .      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  X  .  .  .  .  .  .      E  .  .  .  .  .  .  .  .  .  .
 F  .  .  .  S  .  .  .  .  .  .      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  S  S  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  S  .  .  .  .  .  .  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  S  .  .  .  .  .  .  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  .  S  .  .  .  .  .  .  S  S      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 5, bob 5  |  shots fired this game: 2
>>> Your Turn <<<
Fire at (e.g. B7, or quit): B8

==============================================================
You fired at B8: SUNK, sank their Destroyer!
Your fleet (alice)                   Your shots at bob
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  S  S  S  S  S  .  .  .  .  .      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .      B  .  .  .  .  .  .  #  #  .  .
 C  .  .  .  S  .  .  .  .  .  .      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  S  .  .  .  .  .  .      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  X  .  .  .  .  .  .      E  .  .  .  .  .  .  .  .  .  .
 F  .  .  .  S  .  .  .  .  .  .      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  S  S  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  S  .  .  .  .  .  .  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  S  .  .  .  .  .  .  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  .  S  .  .  .  .  .  .  S  S      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 5, bob 4  |  shots fired this game: 3
Waiting for bob (Player_2) to fire...

==============================================================
bob fired at F10: MISS
Your fleet (alice)                   Your shots at bob
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  S  S  S  S  S  .  .  .  .  .      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .      B  .  .  .  .  .  .  #  #  .  .
 C  .  .  .  S  .  .  .  .  .  .      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  S  .  .  .  .  .  .      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  X  .  .  .  .  .  .      E  .  .  .  .  .  .  .  .  .  .
 F  .  .  .  S  .  .  .  .  .  O      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  S  S  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  S  .  .  .  .  .  .  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  S  .  .  .  .  .  .  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  .  S  .  .  .  .  .  .  S  S      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 5, bob 4  |  shots fired this game: 4
>>> Your Turn <<<
Fire at (e.g. B7, or quit): B8
[server] ALREADY_FIRED: You already fired at that cell.
Fire at (e.g. B7, or quit): K1
[server] INVALID_COORD: That cell is off the board.
Fire at (e.g. B7, or quit): E5

==============================================================
You fired at E5: HIT
Your fleet (alice)                   Your shots at bob
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  S  S  S  S  S  .  .  .  .  .      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .      B  .  .  .  .  .  .  #  #  .  .
 C  .  .  .  S  .  .  .  .  .  .      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  S  .  .  .  .  .  .      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  X  .  .  .  .  .  .      E  .  .  .  .  X  .  .  .  .  .
 F  .  .  .  S  .  .  .  .  .  O      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  S  S  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  S  .  .  .  .  .  .  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  S  .  .  .  .  .  .  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  .  S  .  .  .  .  .  .  S  S      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 5, bob 4  |  shots fired this game: 5
Waiting for bob (Player_2) to fire...

==============================================================
bob fired at A1: HIT
Your fleet (alice)                   Your shots at bob
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  X  S  S  S  S  .  .  .  .  .      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .      B  .  .  .  .  .  .  #  #  .  .
 C  .  .  .  S  .  .  .  .  .  .      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  S  .  .  .  .  .  .      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  X  .  .  .  .  .  .      E  .  .  .  .  X  .  .  .  .  .
 F  .  .  .  S  .  .  .  .  .  O      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  S  S  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  S  .  .  .  .  .  .  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  S  .  .  .  .  .  .  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  .  S  .  .  .  .  .  .  S  S      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 5, bob 4  |  shots fired this game: 6
>>> Your Turn <<<
Fire at (e.g. B7, or quit): J1

==============================================================
You fired at J1: HIT
Your fleet (alice)                   Your shots at bob
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  X  S  S  S  S  .  .  .  .  .      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .      B  .  .  .  .  .  .  #  #  .  .
 C  .  .  .  S  .  .  .  .  .  .      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  S  .  .  .  .  .  .      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  X  .  .  .  .  .  .      E  .  .  .  .  X  .  .  .  .  .
 F  .  .  .  S  .  .  .  .  .  O      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  S  S  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  S  .  .  .  .  .  .  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  S  .  .  .  .  .  .  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  .  S  .  .  .  .  .  .  S  S      J  X  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 5, bob 4  |  shots fired this game: 7
Waiting for bob (Player_2) to fire...

##############################################################
GAME OVER
YOU WIN by forfeit: bob left the game.

Final score                Shots  Hits  Accuracy
you (alice)                    4     4      100%
bob (Player_2)                 3     2       67%

Your final board                     bob's fleet revealed
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  X  S  S  S  S  .  .  .  .  .      A  .  .  .  .  .  .  .  .  .  S
 B  .  .  .  .  .  .  .  .  .  .      B  .  .  .  .  .  .  #  #  .  S
 C  .  .  .  S  .  .  .  .  .  .      C  .  .  .  .  .  .  .  .  .  S
 D  .  .  .  S  .  .  .  .  .  .      D  .  .  .  .  .  .  .  .  .  S
 E  .  .  .  X  .  .  .  .  .  .      E  .  .  .  .  X  S  S  .  .  .
 F  .  .  .  S  .  .  .  .  .  O      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  S  S  S  .  .      G  .  .  .  .  .  .  .  S  .  .
 H  .  S  .  .  .  .  .  .  .  .      H  .  .  .  .  .  .  .  S  .  .
 I  .  S  .  .  .  .  .  .  .  .      I  .  .  .  .  .  .  .  S  .  .
 J  .  S  .  .  .  .  .  .  S  S      J  X  S  S  S  S  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
```

## Game 1: Client 2 (bob, `Player_2`)

```text
Resolved localhost -> 127.0.0.1
Connected to localhost (127.0.0.1) on port 5000.
Your display name (1 to 20 letters a-z): bob
Joined as Player_2 (bob).

=== GAME START: you (Player_2) vs alice (Player_1) ===

Place your fleet on the 10x10 board. For each ship type its start cell and H (runs right) or V (runs down), e.g. A1 H.
Type r to place the whole fleet at random, or quit to leave.
Your fleet so far
    1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  .  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  .  .  .
 J  .  .  .  .  .  .  .  .  .  .
Carrier (length 5): J1 H
Your fleet so far
    1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  .  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  .  .  .
 J  S  S  S  S  S  .  .  .  .  .
Battleship (length 4): A10 V
Your fleet so far
    1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  S
 B  .  .  .  .  .  .  .  .  .  S
 C  .  .  .  .  .  .  .  .  .  S
 D  .  .  .  .  .  .  .  .  .  S
 E  .  .  .  .  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  .  .  .
 J  S  S  S  S  S  .  .  .  .  .
Cruiser (length 3): E5 H
Your fleet so far
    1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  S
 B  .  .  .  .  .  .  .  .  .  S
 C  .  .  .  .  .  .  .  .  .  S
 D  .  .  .  .  .  .  .  .  .  S
 E  .  .  .  .  S  S  S  .  .  .
 F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  .  .  .
 J  S  S  S  S  S  .  .  .  .  .
Submarine (length 3): G8 V
Your fleet so far
    1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  S
 B  .  .  .  .  .  .  .  .  .  S
 C  .  .  .  .  .  .  .  .  .  S
 D  .  .  .  .  .  .  .  .  .  S
 E  .  .  .  .  S  S  S  .  .  .
 F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  S  .  .
 H  .  .  .  .  .  .  .  S  .  .
 I  .  .  .  .  .  .  .  S  .  .
 J  S  S  S  S  S  .  .  .  .  .
Destroyer (length 2): B7 H
Your fleet so far
    1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  S
 B  .  .  .  .  .  .  S  S  .  S
 C  .  .  .  .  .  .  .  .  .  S
 D  .  .  .  .  .  .  .  .  .  S
 E  .  .  .  .  S  S  S  .  .  .
 F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  S  .  .
 H  .  .  .  .  .  .  .  S  .  .
 I  .  .  .  .  .  .  .  S  .  .
 J  S  S  S  S  S  .  .  .  .  .
Fleet sent. Waiting for the server to check it...
Fleet accepted. Both fleets are placed: the battle begins!

==============================================================
Your fleet (bob)                     Your shots at alice
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  S      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  S  S  .  S      B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  .  .  .  .  .  .  S      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  .  .  .  .  .  .  S      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  .  S  S  S  .  .  .      E  .  .  .  .  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  S  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  S  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  S  S  S  S  S  .  .  .  .  .      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 5, alice 5  |  shots fired this game: 0
Waiting for alice (Player_1) to fire...

==============================================================
alice fired at B7: HIT
Your fleet (bob)                     Your shots at alice
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  S      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  X  S  .  S      B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  .  .  .  .  .  .  S      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  .  .  .  .  .  .  S      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  .  S  S  S  .  .  .      E  .  .  .  .  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  S  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  S  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  S  S  S  S  S  .  .  .  .  .      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 5, alice 5  |  shots fired this game: 1
>>> Your Turn <<<
Fire at (e.g. B7, or quit): E4

==============================================================
You fired at E4: HIT
Your fleet (bob)                     Your shots at alice
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  S      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  X  S  .  S      B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  .  .  .  .  .  .  S      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  .  .  .  .  .  .  S      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  .  S  S  S  .  .  .      E  .  .  .  X  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  S  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  S  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  S  S  S  S  S  .  .  .  .  .      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 5, alice 5  |  shots fired this game: 2
Waiting for alice (Player_1) to fire...

==============================================================
alice fired at B8: SUNK, sank your Destroyer!
Your fleet (bob)                     Your shots at alice
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  S      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  #  #  .  S      B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  .  .  .  .  .  .  S      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  .  .  .  .  .  .  S      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  .  S  S  S  .  .  .      E  .  .  .  X  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .      F  .  .  .  .  .  .  .  .  .  .
 G  .  .  .  .  .  .  .  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  S  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  S  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  S  S  S  S  S  .  .  .  .  .      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 4, alice 5  |  shots fired this game: 3
>>> Your Turn <<<
Fire at (e.g. B7, or quit): F10

==============================================================
You fired at F10: MISS
Your fleet (bob)                     Your shots at alice
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  S      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  #  #  .  S      B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  .  .  .  .  .  .  S      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  .  .  .  .  .  .  S      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  .  S  S  S  .  .  .      E  .  .  .  X  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .      F  .  .  .  .  .  .  .  .  .  O
 G  .  .  .  .  .  .  .  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  S  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  S  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  S  S  S  S  S  .  .  .  .  .      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 4, alice 5  |  shots fired this game: 4
Waiting for alice (Player_1) to fire...

==============================================================
alice fired at E5: HIT
Your fleet (bob)                     Your shots at alice
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  S      A  .  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  #  #  .  S      B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  .  .  .  .  .  .  S      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  .  .  .  .  .  .  S      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  .  X  S  S  .  .  .      E  .  .  .  X  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .      F  .  .  .  .  .  .  .  .  .  O
 G  .  .  .  .  .  .  .  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  S  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  S  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  S  S  S  S  S  .  .  .  .  .      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 4, alice 5  |  shots fired this game: 5
>>> Your Turn <<<
Fire at (e.g. B7, or quit): A1

==============================================================
You fired at A1: HIT
Your fleet (bob)                     Your shots at alice
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  S      A  X  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  #  #  .  S      B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  .  .  .  .  .  .  S      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  .  .  .  .  .  .  S      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  .  X  S  S  .  .  .      E  .  .  .  X  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .      F  .  .  .  .  .  .  .  .  .  O
 G  .  .  .  .  .  .  .  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  S  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  S  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  S  S  S  S  S  .  .  .  .  .      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 4, alice 5  |  shots fired this game: 6
Waiting for alice (Player_1) to fire...

==============================================================
alice fired at J1: HIT
Your fleet (bob)                     Your shots at alice
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  .  .  .  .  .  .  .  .  .  S      A  X  .  .  .  .  .  .  .  .  .
 B  .  .  .  .  .  .  #  #  .  S      B  .  .  .  .  .  .  .  .  .  .
 C  .  .  .  .  .  .  .  .  .  S      C  .  .  .  .  .  .  .  .  .  .
 D  .  .  .  .  .  .  .  .  .  S      D  .  .  .  .  .  .  .  .  .  .
 E  .  .  .  .  X  S  S  .  .  .      E  .  .  .  X  .  .  .  .  .  .
 F  .  .  .  .  .  .  .  .  .  .      F  .  .  .  .  .  .  .  .  .  O
 G  .  .  .  .  .  .  .  S  .  .      G  .  .  .  .  .  .  .  .  .  .
 H  .  .  .  .  .  .  .  S  .  .      H  .  .  .  .  .  .  .  .  .  .
 I  .  .  .  .  .  .  .  S  .  .      I  .  .  .  .  .  .  .  .  .  .
 J  X  S  S  S  S  .  .  .  .  .      J  .  .  .  .  .  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 4, alice 5  |  shots fired this game: 7
>>> Your Turn <<<
Fire at (e.g. B7, or quit): quit

You left the game.
```

## Game 1: Client 3 (eve, arrives during the game)

```text
Resolved localhost -> 127.0.0.1
Connected to localhost (127.0.0.1) on port 5000.
Your display name (1 to 20 letters a-z): eve
[server] ROOM_FULL: Both seats are taken. Try again when this game ends.
The server closed the connection.
```

## Game 2: A Full Game on the Same Server

Right after game 1's `CLEANUP`, two new clients (carol and dave) connected to the same server process and played until carol sank dave's whole fleet (`FLEET_DESTROYED`). carol placed her fleet at random (`r`). This is the server's side of game 2, followed by the end of carol's screen.

<details>
<summary>Game 2 server console (146 lines)</summary>

```text
[17:33:23] accepted connection from 127.0.0.1:61873
[17:33:24] Player_1 joined as carol
[17:33:24] accepted connection from 127.0.0.1:61874
[17:33:24] Player_2 joined as dave
[17:33:24] [FSM] WAITING_FOR_PLAYERS -> GAME_START
[17:33:24] [FSM] GAME_START -> FLEET_PLACEMENT
[17:33:24] Player_1 fleet accepted
[17:33:25] Player_2 fleet accepted
[17:33:25] [FSM] FLEET_PLACEMENT -> PLAYER_TURN
[17:33:25] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:25] Player_1 fires at J1: HIT
[17:33:25] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:25] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:25] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:25] Player_2 fires at A1: MISS
[17:33:25] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:25] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:25] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:25] Player_1 fires at J2: HIT
[17:33:25] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:25] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:25] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:25] Player_2 fires at A2: MISS
[17:33:25] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:25] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:25] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:25] Player_1 fires at J3: HIT
[17:33:25] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:25] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:26] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:26] Player_2 fires at A3: MISS
[17:33:26] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:26] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:26] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:26] Player_1 fires at J4: HIT
[17:33:26] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:26] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:26] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:26] Player_2 fires at A4: MISS
[17:33:26] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:26] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:26] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:26] Player_1 fires at J5: SUNK (Carrier)
[17:33:26] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:26] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:26] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:26] Player_2 fires at A5: MISS
[17:33:26] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:26] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:26] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:26] Player_1 fires at A10: HIT
[17:33:26] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:26] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:26] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:26] Player_2 fires at A6: HIT
[17:33:26] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:26] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:26] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:26] Player_1 fires at B10: HIT
[17:33:26] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:26] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:26] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:26] Player_2 fires at A7: HIT
[17:33:26] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:26] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:26] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:26] Player_1 fires at C10: HIT
[17:33:26] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:26] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:27] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:27] Player_2 fires at A8: SUNK (Cruiser)
[17:33:27] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:27] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:27] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:27] Player_1 fires at D10: SUNK (Battleship)
[17:33:27] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:27] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:27] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:27] Player_2 fires at A9: MISS
[17:33:27] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:27] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:27] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:27] Player_1 fires at E5: HIT
[17:33:27] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:27] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:27] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:27] Player_2 fires at A10: MISS
[17:33:27] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:27] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:27] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:27] Player_1 fires at E6: HIT
[17:33:27] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:27] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:27] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:27] Player_2 fires at B1: MISS
[17:33:27] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:27] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:27] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:27] Player_1 fires at E7: SUNK (Cruiser)
[17:33:27] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:27] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:27] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:27] Player_2 fires at B2: MISS
[17:33:27] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:27] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:27] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:27] Player_1 fires at G8: HIT
[17:33:27] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:27] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:28] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:28] Player_2 fires at B3: MISS
[17:33:28] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:28] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:28] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:28] Player_1 fires at H8: HIT
[17:33:28] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:28] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:28] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:28] Player_2 fires at B4: MISS
[17:33:28] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:28] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:28] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:28] Player_1 fires at I8: SUNK (Submarine)
[17:33:28] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:28] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:28] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:28] Player_2 fires at B5: MISS
[17:33:28] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:28] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:28] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:28] Player_1 fires at B7: HIT
[17:33:28] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:28] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:28] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:28] Player_2 fires at B6: MISS
[17:33:28] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:28] [FSM] CHECK_WIN -> PLAYER_TURN
[17:33:28] [FSM] PLAYER_TURN -> EVALUATE_MOVE
[17:33:28] Player_1 fires at B8: SUNK (Destroyer)
[17:33:28] [FSM] EVALUATE_MOVE -> CHECK_WIN
[17:33:28] [FSM] CHECK_WIN -> GAME_OVER
[17:33:28] game over: winner Player_1, FLEET_DESTROYED
[17:33:28] closed connection Player_2
[17:33:28] closed connection Player_1
[17:33:28] [FSM] GAME_OVER -> CLEANUP
[17:33:28] [FSM] CLEANUP -> WAITING_FOR_PLAYERS
```

</details>

```text
==============================================================
dave fired at B6: MISS
Your fleet (carol)                   Your shots at dave
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  O  O  O  O  O  #  #  #  O  O      A  .  .  .  .  .  .  .  .  .  #
 B  O  O  O  O  O  O  .  .  .  .      B  .  .  .  .  .  .  X  .  .  #
 C  .  .  .  .  .  .  .  .  .  .      C  .  .  .  .  .  .  .  .  .  #
 D  .  S  .  .  .  .  .  .  .  .      D  .  .  .  .  .  .  .  .  .  #
 E  .  S  .  .  .  .  .  .  S  .      E  .  .  .  .  #  #  #  .  .  .
 F  .  S  .  .  S  S  .  S  S  .      F  .  .  .  .  .  .  .  .  .  .
 G  .  S  .  .  .  .  .  S  S  .      G  .  .  .  .  .  .  .  #  .  .
 H  .  S  .  .  .  .  .  S  .  .      H  .  .  .  .  .  .  .  #  .  .
 I  .  .  .  .  .  .  .  S  .  .      I  .  .  .  .  .  .  .  #  .  .
 J  .  .  .  .  .  .  .  .  .  .      J  #  #  #  #  #  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
Score: ships afloat: you 4, dave 1  |  shots fired this game: 32
>>> Your Turn <<<
Fire at (e.g. B7, or quit): B8

##############################################################
GAME OVER
YOU WIN! You sank all of dave's ships.

Final score                Shots  Hits  Accuracy
you (carol)                   17    17      100%
dave (Player_2)               16     3       19%

Your final board                     dave's fleet revealed
    1  2  3  4  5  6  7  8  9 10         1  2  3  4  5  6  7  8  9 10
 A  O  O  O  O  O  #  #  #  O  O      A  .  .  .  .  .  .  .  .  .  #
 B  O  O  O  O  O  O  .  .  .  .      B  .  .  .  .  .  .  #  #  .  #
 C  .  .  .  .  .  .  .  .  .  .      C  .  .  .  .  .  .  .  .  .  #
 D  .  S  .  .  .  .  .  .  .  .      D  .  .  .  .  .  .  .  .  .  #
 E  .  S  .  .  .  .  .  .  S  .      E  .  .  .  .  #  #  #  .  .  .
 F  .  S  .  .  S  S  .  S  S  .      F  .  .  .  .  .  .  .  .  .  .
 G  .  S  .  .  .  .  .  S  S  .      G  .  .  .  .  .  .  .  #  .  .
 H  .  S  .  .  .  .  .  S  .  .      H  .  .  .  .  .  .  .  #  .  .
 I  .  .  .  .  .  .  .  S  .  .      I  .  .  .  .  .  .  .  #  .  .
 J  .  .  .  .  .  .  .  .  .  .      J  #  #  #  #  #  .  .  .  .  .
S ship   X hit   # sunk   O miss   . water / not fired at
```
