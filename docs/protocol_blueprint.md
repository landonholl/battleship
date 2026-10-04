# Battleship Application Protocol Blueprint

**Course:** CS 457 - Computer Networks
**Author:** Landon Holland

---

## 1. Message Envelope

Every message in both directions is a single JSON object that uses the same four field envelope. Only the contents of `payload` change between message types.

| Field       | Type           | Required | Description                                                                                                                     |
| ----------- | -------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `msg_type`  | string         | yes      | The message type, one of the types defined in this document (`CONNECT`, `MOVE`, `STATE_UPDATE`)                            |
| `player_id` | string or null | yes      | The sender's ID. Clients send `Player_1` or `Player_2` once assigned, or `null` before assignment. The server always sends `"SERVER"` |
| `payload`   | object         | yes      | Fields specific to `msg_type`. May be an empty object `{}`                                                                      |
| `timestamp` | integer        | yes      | Unix time in seconds when the message was sent                                                                                  |

Unknown fields are ignored by the receiver so the schema can grow in later sprints without breaking an older client.

### Player ID Assignment

- A client has no ID when it connects, so `player_id` is `null` on its first `CONNECT`.
- The server stores the current player IDs and assigns one to the client in its `LOBBY_WAIT` reply. The first client to connect becomes `Player_1` and the second becomes `Player_2`. The client uses the assigned ID in every message after that.
- IDs are wiped when a player disconnects and when a new game starts, so ID assignment is redone for every game.
- A game cannot start until both players have been assigned IDs.

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
