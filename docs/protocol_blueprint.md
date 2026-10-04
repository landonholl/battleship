# Battleship Application Protocol Blueprint

**Course:** CS 457 - Computer Networks
**Author:** Landon Holland

---

## 1. Message Envelope

Every message in both directions is a JSON object that uses the same 4 field envelope. Only the contents of `payload` change between message types.

| Field       | Type           | Required | Description                                                                                                                     |
| ----------- | -------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `msg_type`  | string         | yes      | The message type, one of the types defined in this document (`CONNECT`, `MOVE`, `STATE_UPDATE`)                            |
| `player_id` | string or null | yes      | The sender's ID. Clients send `Player_1` or `Player_2` once assigned, or `null` before assignment. The server always sends `"SERVER"` |
| `payload`   | object         | yes      | Fields specific to `msg_type`. May be an empty object `{}`                                                                      |
| `timestamp` | integer        | yes      | Unix time in seconds when the message was sent                                                                                  |

Unknown fields are ignored by the receiver so that hopefully the schema can grow in later sprints without breaking an older client.

### Player ID Assignment

- A client has no ID when it connects, so `player_id` is `null` on its 1st `CONNECT`.
- The server stores the current player IDs and assigns one to the client in its `LOBBY_WAIT` reply. The 1st client to connect is `Player_1` and the 2nd is `Player_2`. The client uses the assigned ID in every message after that.
- IDs are wiped when a player disconnects and when a new game starts, so ID assignment is done again for every game.
- A game cannot start until both players have been assigned an ID.

### Player ID Validation

The server checks `player_id` on all client messages before acting on it:

- `null` is only allowed on `CONNECT`. Any other message with a `null` `player_id` is rejected with `ERROR` (`MALFORMED`).
- The server knows what ID it assigned to what socket. A message whose `player_id` does not match the ID assigned to the socket it arrived on is rejected with `ERROR` (`MALFORMED`), so a client (hopefully) cannot act as its opponent by copying the other player's ID.
- A rejected message changes no game state, and the `ERROR` goes only to the client that sent it.

---

## 2. Message Types

### `CONNECT`

- **Direction:** Client -> Server
- **Purpose:** The client asks to join the game room. This is the 1st message a client sends, and the only message allowed to have a `null` `player_id`.

**Payload:**

| Field          | Type   | Required | Description                                         |
| -------------- | ------ | -------- | --------------------------------------------------- |
| `display_name` | string | yes      | The name shown to the opponent                      |
| `version`      | string | yes      | The protocol version the client speaks, e.g. `"0.0"` |

**Server handling:**

1. Check that `player_id` is `null`.
2. If the room has an open slot, assign the next ID in join order (`Player_1`, then `Player_2`), store the display name, and reply with `LOBBY_WAIT`.
3. Once both IDs are assigned, send `GAME_START` to both players.
4. If both slots are already taken, reply with `ERROR` and do not assign ID.

```json
{
  "msg_type": "CONNECT",
  "player_id": null,
  "payload": {
    "display_name": "PLACEHOLDER",
    "version": "0.0"
  },
  "timestamp": 1727000000
}
```

### `LOBBY_WAIT`

- **Direction:** Server -> Client
- **Purpose:** The server's reply to a successful `CONNECT`. It gives the client its `player_id` for the current game and reports how many players are in the room. Both client gets thier ID this way.

**Payload:**

| Field               | Type    | Required | Description                                                       |
| ------------------- | ------- | -------- | ----------------------------------------------------------------- |
| `assigned_id`       | string  | yes      | `Player_1` or `Player_2` for now. The client uses this ID from now on     |
| `players_connected` | integer | yes      | `1` or `2`. The number of players in the room, including this one |

The assigned ID goes in the payload because the envelope's `player_id` on server messages is always `"SERVER"`.

**Client handling:**

1. Store `assigned_id` and use it as `player_id` in every message after this.
2. If `players_connected` is `1`, show that it is waiting for an opponent.
3. If `players_connected` is `2`, `GAME_START` follows immediately.

```json
{
  "msg_type": "LOBBY_WAIT",
  "player_id": "SERVER",
  "payload": {
    "assigned_id": "Player_1",
    "players_connected": 1
  },
  "timestamp": 1727000001
}
```

### `GAME_START`

- **Direction:** Server -> both clients
- **Purpose:** Both players have IDs, so the game starts. Sent to each client right after the second players `LOBBY_WAIT`. It tells each client who it is playing and the rules for this game, and moves both clients into fleet placement.

**Payload:**

| Field           | Type             | Required | Description                                                       |
| --------------- | ---------------- | -------- | ----------------------------------------------------------------- |
| `opponent_name` | string           | yes      | The opponent's `display_name` from their `CONNECT`                |
| `board_size`    | integer          | yes      | Width and height of the square grid. `10` for a 10x10 board       |
| `fleet`         | array of objects | yes      | The ships each player must place. Each object has `name` (string) and `length` (integer) |

The client hardcodes zero game rules. It draws the board and builds its placement prompts from `board_size` and `fleet`, so the server will hopefully be the only source of truth for the rules.

**Client handling:**

1. Store `opponent_name`, `board_size`, and `fleet`.
2. Enter fleet placement and prompt the player to place every ship in `fleet`.
3. Send the layout to the server in `PLACE_FLEET`.

```json
{
  "msg_type": "GAME_START",
  "player_id": "SERVER",
  "payload": {
    "opponent_name": "PLACEHOLDER",
    "board_size": 10,
    "fleet": [
      { "name": "Carrier",    "length": 5 },
      { "name": "Battleship", "length": 4 },
      { "name": "Cruiser",    "length": 3 },
      { "name": "Submarine",  "length": 3 },
      { "name": "Destroyer",  "length": 2 }
    ]
  },
  "timestamp": 1727000002
}
```

### `PLACE_FLEET`

- **Direction:** Client -> Server
- **Purpose:** The client submits its whole fleet layout at once, one entry per ship listed in `GAME_START`.

**Payload:**

| Field   | Type             | Required | Description                                      |
| ------- | ---------------- | -------- | ------------------------------------------------ |
| `ships` | array of objects | yes      | One object per ship in the fleet, described below |

Each object in `ships`:

| Field         | Type    | Required | Description                                                                 |
| ------------- | ------- | -------- | --------------------------------------------------------------------------- |
| `name`        | string  | yes      | Ship name, matching a `name` from the `GAME_START` fleet                     |
| `row`         | integer | yes      | Row of the ship's starting cell, `0` to `board_size - 1`                     |
| `col`         | integer | yes      | Column of the ship's starting cell, `0` to `board_size - 1`                  |
| `orientation` | string  | yes      | `"H"`: the ship runs right from the start cell. `"V"`: it runs down from the start cell |

The client does not send a ship's length. The server looks it up from the fleet by `name`, so a client cannot change a ship's size.

**Server handling:**

1. Validate the layout:
   - every ship in the fleet appears only once, and no other names appear
   - `orientation` is `"H"` or `"V"`
   - every cell of every ship is on the board
   - no 2 ships share a cell
2. If any check fails, reply `ERROR` (`INVALID_PLACEMENT`). The player stays in fleet placement and can send a corrected `PLACE_FLEET`.
3. If the layout is valid, store it. The server wont send an acknowledgment and just show waiting for simplicity. The client shows that it is waiting for the opponent on its own until the next `STATE_UPDATE`.
4. A layout is final once accepted. Another `PLACE_FLEET` from a player whose valid layout is already stored is rejected with `ERROR` (`WRONG_PHASE`).
5. Once both players have a valid layout, the game moves to turns with `Player_1` as the active player, and the server sends each player a `STATE_UPDATE`.

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
  "timestamp": 1727000010
}
```

### `MOVE`

- **Direction:** Client -> Server
- **Purpose:** The active player fires one shot at a cell on the opponent's grid.

**Payload:**

| Field | Type    | Required | Description                                  |
| ----- | ------- | -------- | -------------------------------------------- |
| `row` | integer | yes      | Target row, `0` to `board_size - 1`          |
| `col` | integer | yes      | Target column, `0` to `board_size - 1`       |

The player types a coordinate like `B7`. As in standard Battleship, the letter is the row and the number is the column. The client will convert it to zero based integers before sending, so the server only ever sees `row` and `col`:

- **Row:** the letter, `A` to `J`, becomes `0` to `9`
- **Column:** the number, `1` to `10`, becomes `0` to `9`

Ex: `B7` becomes `row: 1, col: 6`, like in the sample below.

**Server handling:**

The checks run in this order. The 1st one that fails chooses wht error the player will see.

1. If the game is not in turns (for example, during fleet placement), reply `ERROR` (`WRONG_PHASE`).
2. If the sender is not the active player, reply `ERROR` (`OUT_OF_TURN`).
3. If `row` or `col` is missing, not an integer, or off the board, reply `ERROR` (`INVALID_COORD`).
4. If this player has already fired at that cell, reply `ERROR` (`ALREADY_FIRED`).
5. Otherwise the shot is valid:
   - resolve it against the opponent's fleet as `HIT`, `MISS`, or `SUNK`
   - check whether the opponent has any ship cells left
   - if they have none, send `GAME_OVER` with reason `FLEET_DESTROYED`
   - if they still have ships, switch the active player and send each player a `STATE_UPDATE`

A rejected `MOVE` changes no game state and does not use up the turn, so the player can try again. The `ERROR` goes only to the sender.

```json
{
  "msg_type": "MOVE",
  "player_id": "Player_1",
  "payload": {
    "row": 1,
    "col": 6
  },
  "timestamp": 1727000020
}
```

### `STATE_UPDATE`

- **Direction:** Server -> each client
- **Purpose:** Tells a player the current state of the game. The server builds a separate view for each player and sends it only to that player. It is never broadcast identically, and a player never receives the opponent's ship positions.
- **When it is sent:** once when turns begin (after both fleets are placed), and after every valid shot that does not end the game. A shot that ends the game gets `GAME_OVER` instead.

There is no `phase` field. The message type already tells the client which phase it is in: `GAME_START` means fleet placement, `STATE_UPDATE` means turns, and `GAME_OVER` means the game is over.

**Payload:**

| Field             | Type                | Required | Description                                                                                   |
| ----------------- | ------------------- | -------- | --------------------------------------------------------------------------------------------- |
| `active_player`   | string              | yes      | The player whose turn it is now. The client only prompts for a shot when this is its own ID     |
| `your_board`      | array of strings    | yes      | The receiving player's own board: their ships and the opponent's shots. One string per row     |
| `tracking_grid`   | array of strings    | yes      | The receiving player's shots at the opponent: hits and misses only. One string per row         |
| `last_shot`       | object or null      | yes      | The most recent shot, described below. `null` on the first update, before any shot is fired   |
| `ships_remaining` | object              | yes      | Ships still afloat for each player, keyed by player ID, e.g. `{"Player_1": 5, "Player_2": 4}`  |

Each `last_shot` object:

| Field       | Type           | Required | Description                                               |
| ----------- | -------------- | -------- | --------------------------------------------------------- |
| `shooter`   | string         | yes      | ID of the player who fired                                |
| `row`       | integer        | yes      | Target row                                                |
| `col`       | integer        | yes      | Target column                                             |
| `result`    | string         | yes      | `"HIT"`, `"MISS"`, or `"SUNK"`                            |
| `ship_sunk` | string or null | yes      | Name of the ship that was sunk when `result` is `"SUNK"`, otherwise `null` |

**Client handling:**

1. Redraw both grids from `your_board` and `tracking_grid`. The client keeps no board state of its own.
2. Show the result of `last_shot`, if there is one.
3. If `active_player` is this client's ID, prompt for a shot. Otherwise show that it is waiting for the opponent.

The example below is `Player_1`'s view after five shots, using the `PLACE_FLEET` layout above:

1. `Player_1` fires at D6 (3,5): miss
2. `Player_2` fires at E4 (4,3): hits the Battleship
3. `Player_1` fires at I9 (8,8): miss
4. `Player_2` fires at F10 (5,9): miss
5. `Player_1` fires at B7 (1,6): hit

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
    "ships_remaining": { "Player_1": 5, "Player_2": 5 }
  },
  "timestamp": 1727000030
}
```

### `DISCONNECT`

- **Direction:** Client -> Server
- **Purpose:** The player is quitting on purpose. Sending `DISCONNECT` before closing the socket lets the server tell a deliberate quit apart from a crash or network drop. The opponent sees `OPPONENT_DISCONNECTED` either way.

**Payload:** empty object `{}`. No fields.

**Server handling:**

1. Wipe the sender's `player_id`.
2. If the opponent is still connected, send them `GAME_OVER` with reason `OPPONENT_DISCONNECTED`:
   - During fleet placement, no shots have been fired, so `winner` is `null` and the game resets to `WAITING_FOR_PLAYERS`.
   - During turns, the remaining player is the winner.
   - In the lobby, before `GAME_START`, there is no opponent, so nothing is sent.

   On `GAME_OVER` the remaining client re-`CONNECT`s automatically.
3. Close the sender's socket. The server sends no reply to the leaving client.

A client that has not been assigned an ID yet does not send `DISCONNECT`, since `null` is only allowed on `CONNECT`. It just closes the socket, and the server treats that as a normal connection close.

```json
{
  "msg_type": "DISCONNECT",
  "player_id": "Player_1",
  "payload": {},
  "timestamp": 1727000300
}
```