# Sprint 4 Network Verification Report

**Course:** CS 457
**Written by:** Landon Holland
**Server hostname:** `server.holland.edu` -> `192.168.20.100`

This report verifies the one-router CML topology the Battleship game runs on (SOW #5). One Cisco IOSv router, `LH-R1`, connects the two client subnets and the server subnet, hands out client addresses with DHCP, and answers DNS for `server.holland.edu`.

| Deliverable | File |
| ----------- | ---- |
| CML topology export | [sprint_4_topology.yaml](sprint_4_topology.yaml) |
| DNS packet capture | [sprint_4_dns_lookup.pcap](sprint_4_dns_lookup.pcap) |
| This report | `sprint_4_network_report.md` |

---

## 1. Topology

TO FILL: CML topology screenshot showing the node names `LH-R1`, `LH-Client1`, `LH-Client2`, `LH-Server`, and the external connector.

![CML topology](screenshots/topology.png)

| Node | Type | Interface | Address | Gateway | DNS server | How it gets its address |
| ---- | ---- | --------- | ------- | ------- | ---------- | ----------------------- |
| `LH-R1` | Cisco IOSv | `Gi0/1` (Subnet A) | `192.168.10.1/24` | | | Static |
| `LH-R1` | | `Gi0/2` (Subnet B) | `192.168.11.1/24` | | | Static |
| `LH-R1` | | `Gi0/3` (Subnet C) | `192.168.20.1/24` | | | Static |
| `LH-R1` | | `Gi0/0` (External Connector) | `192.168.255.x` | | | DHCP from the External Connector |
| `LH-Client1` | Alpine Linux | `eth0` | `192.168.10.2/24` | `192.168.10.1` | `192.168.10.1` | DHCP, `CLIENT1_POOL` |
| `LH-Client2` | Alpine Linux | `eth0` | `192.168.11.2/24` | `192.168.11.1` | `192.168.11.1` | DHCP, `CLIENT2_POOL` |
| `LH-Server` | Alpine Linux | `eth0` | `192.168.20.100/24` | `192.168.20.1` | `192.168.20.1` | Static |

All three subnets are directly connected to `LH-R1`, so it routes between them with connected (`C`) routes and needs no static routes. `Gi0/0` and NAT overload exist only so the nodes can install packages and clone the repository. The game traffic never leaves the three subnets.

---

## 2. Router `LH-R1` Configuration

This is the configuration entered on `LH-R1`, in the order it was entered.

```text
enable
configure terminal
hostname LH-R1
ip routing

! Gateways for the three subnets
interface GigabitEthernet0/1
 description Subnet A - LH-Client1
 ip address 192.168.10.1 255.255.255.0
 ip nat inside
 no shutdown
 exit
interface GigabitEthernet0/2
 description Subnet B - LH-Client2
 ip address 192.168.11.1 255.255.255.0
 ip nat inside
 no shutdown
 exit
interface GigabitEthernet0/3
 description Subnet C - LH-Server
 ip address 192.168.20.1 255.255.255.0
 ip nat inside
 no shutdown
 exit

! Link to the CML External Connector (NAT mode)
interface GigabitEthernet0/0
 description External Connector
 ip address dhcp
 ip nat outside
 no shutdown
 exit

! DHCP: never lease the gateway addresses
ip dhcp excluded-address 192.168.10.1
ip dhcp excluded-address 192.168.11.1
ip dhcp pool CLIENT1_POOL
 network 192.168.10.0 255.255.255.0
 default-router 192.168.10.1
 dns-server 192.168.10.1
 exit
ip dhcp pool CLIENT2_POOL
 network 192.168.11.0 255.255.255.0
 default-router 192.168.11.1
 dns-server 192.168.11.1
 exit

! Authoritative DNS for the game server
ip domain lookup
ip dns server
ip host server.holland.edu 192.168.20.100

! NAT overload (PAT) for all three subnets out Gi0/0
access-list 1 permit 192.168.10.0 0.0.0.255
access-list 1 permit 192.168.11.0 0.0.0.255
access-list 1 permit 192.168.20.0 0.0.0.255
ip nat inside source list 1 interface GigabitEthernet0/0 overload

end
write memory
```

TO FILL: if anything was entered differently in CML, change it here so this block matches the router.

---

## 3. Router Verification

### 3.1 `show ip interface brief`

Shows `Gi0/1`, `Gi0/2`, and `Gi0/3` with their gateway addresses, all `up` / `up`.

```text
TO FILL: paste the output of "show ip interface brief" on LH-R1
```

### 3.2 `show ip route`

Shows `192.168.10.0/24`, `192.168.11.0/24`, and `192.168.20.0/24` as connected (`C`) routes, so `LH-R1` routes between the three subnets without any static route.

```text
TO FILL: paste the output of "show ip route" on LH-R1
```

### 3.3 `show ip dhcp binding`

Shows an active lease for each client, on its own subnet: `192.168.10.2` for `LH-Client1` and `192.168.11.2` for `LH-Client2`.

```text
TO FILL: paste the output of "show ip dhcp binding" on LH-R1
```

### 3.4 `show hosts`

Shows the static A record `server.holland.edu` -> `192.168.20.100`.

```text
TO FILL: paste the output of "show hosts" on LH-R1
```

---

## 4. Game Server `LH-Server` (Static Address)

Commands entered on `LH-Server`:

```text
sudo ip addr add 192.168.20.100/24 dev eth0
sudo ip link set eth0 up
sudo ip route add default via 192.168.20.1
echo "nameserver 192.168.20.1" | sudo tee /etc/resolv.conf
```

The default route matters: without it the server could receive a packet from `192.168.10.x` or `192.168.11.x` but could not send the reply.

`ip addr show eth0` and `ip route` show `192.168.20.100/24` and `default via 192.168.20.1`:

```text
TO FILL: paste "ip addr show eth0" and "ip route" from LH-Server
```

---

## 5. Clients `LH-Client1` and `LH-Client2` (DHCP, Ping, DNS)

Each client brought up `eth0` and asked `LH-R1` for a lease:

```text
sudo ip link set eth0 up
sudo udhcpc -i eth0
```

### 5.1 `LH-Client1` (Subnet A)

The lease, default route, and DNS server from `CLIENT1_POOL` (`ip addr show eth0`, `ip route`, `cat /etc/resolv.conf`):

```text
TO FILL: paste the udhcpc output, "ip addr show eth0", "ip route", and "cat /etc/resolv.conf" from LH-Client1
```

Zero-loss ping to the game server across `LH-R1` (`ping -c 4 192.168.20.100`):

```text
TO FILL: paste "ping -c 4 192.168.20.100" from LH-Client1 (should end with 0% packet loss)
```

Name resolution through `LH-R1` (`nslookup -type=A server.holland.edu`):

```text
TO FILL: paste "nslookup -type=A server.holland.edu" from LH-Client1 (should answer 192.168.20.100 from server 192.168.10.1)
```

### 5.2 `LH-Client2` (Subnet B)

```text
TO FILL: paste the udhcpc output, "ip addr show eth0", "ip route", and "cat /etc/resolv.conf" from LH-Client2
```

```text
TO FILL: paste "ping -c 4 192.168.20.100" from LH-Client2
```

```text
TO FILL: paste "nslookup -type=A server.holland.edu" from LH-Client2 (should answer 192.168.20.100 from server 192.168.11.1)
```

`-type=A` is used because Alpine's `nslookup` also asks for an AAAA (IPv6) record by default, and `LH-R1` only has the IPv4 A record. The game client asks for the A record only: `socket.gethostbyname()` is IPv4-only (`client.py`, `resolve`).

---

## 6. Wireshark DNS Capture

The capture `sprint_4_dns_lookup.pcap` was taken on the `LH-Client1` to `LH-R1` link while `LH-Client1` ran `nslookup -type=A server.holland.edu`. Display filter: `dns`.

TO FILL: annotated Wireshark screenshot of the query and the response, with the response's answer section expanded.

![DNS query and response in Wireshark](screenshots/wireshark_dns.png)

The annotations are here rather than inside the capture file: a `.pcap` cannot store Wireshark packet comments (only `.pcapng` can), and the deliverable must be a `.pcap`.

| Packet | Source | Destination | Protocol | What it shows |
| ------ | ------ | ----------- | -------- | ------------- |
| TO FILL (number) | TO FILL (expected `192.168.10.2`) | TO FILL (expected `192.168.10.1`) | DNS (UDP, destination port 53) | **Standard query:** `LH-Client1` asks its DHCP-assigned DNS server, `LH-R1`, for the A record of `server.holland.edu`. The source port is a random high port. |
| TO FILL (number) | TO FILL (expected `192.168.10.1`) | TO FILL (expected `192.168.10.2`) | DNS (UDP, source port 53) | **Standard query response:** `LH-R1` answers from its own host table (`ip host`) with one A record, `server.holland.edu` -> `192.168.20.100`. The transaction ID matches the query's, and the destination port is the query's source port. |

TO FILL: the transaction ID seen in both packets: `0x____`.

---

## 7. Rubric Checklist

| Rubric item | Evidence |
| ----------- | -------- |
| 1. One router, three subnets, server static IP and default route, interfaces up/up | #1 table and screenshot, #2 configuration, #3.1, #3.2, #4 |
| 2. Separate DHCP pools with excluded gateways, default router, and DNS server; leases for both clients | #2 configuration, #3.3, #5.1 and #5.2 lease output |
| 3. `ip dns server` and `ip host server.holland.edu 192.168.20.100`; both clients resolve it | #2 configuration, #3.4, both `nslookup` outputs in #5 |
| 4. Zero-loss ping from both clients; DNS capture with query and response | Both `ping` outputs in #5, #6, `sprint_4_dns_lookup.pcap` |
| 5. YAML export with initialed node names; this report | `sprint_4_topology.yaml`, #1 screenshot, this report |
