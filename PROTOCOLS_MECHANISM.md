# Routing Protocol Mechanisms in UavNetSim

This document explains how the routing protocols in this simulator actually work, at the
mechanism level, starting with the two original/baseline protocols shipped with the
simulator: **DSDV** (proactive, table-driven) and **Greedy** (reactive-free, position-based
forwarding). Later revisions of this document will cover the additional protocols
(QGeo, CR-QGeo, MACG, MC-Greedy, Q-Routing, QMR, QFANET, OPAR, GRAd) added on top of these two.

Both protocols plug into the same network-layer contract used by every routing module in
this codebase:

```
routing_protocol.next_hop_selection(packet)   -> (has_route, packet_or_control_pkt, enquire)
routing_protocol.packet_reception(packet, src_drone_id)
```

`entities/drone.py`'s `feed_packet()` loop pulls a packet off `transmitting_queue`, and if it's
a `DataPacket`, calls `next_hop_selection()` to ask the routing layer for a next hop before
handing it to the MAC layer (`entities/drone.py:257`). If no route is available, the packet is
parked on `waiting_list` and retried later. `packet_reception()` is the dual entry point,
invoked whenever a packet arrives from the MAC layer (`entities/drone.py:400`), and is where
each protocol updates its own tables and handles `DataPacket`/`AckPacket`/hello-packet logic.

Both protocols also share:
- A per-drone `rng_routing` seeded from `drone.identifier + seed + 10`, used only to jitter
  hello-packet timing.
- A `check_waiting_list()` background process that periodically re-attempts delivery for
  packets that had no route at the time they were generated/received, dropping them once
  `creation_time + deadline` (`config.PACKET_LIFETIME`) has passed.
- Hello packets broadcast every `hello_interval = 0.5e6 μs` (0.5 s) plus a random jitter of
  1000–2000 μs, to desynchronize neighboring drones' broadcasts and reduce collisions.
- A generic `BaseTable` (`routing/base/base_table.py`) providing `is_item`, `purge`,
  `get_updated_time`, etc., with a shared entry lifetime of `entry_life_time = 2e6 μs` (2 s)
  for entries not otherwise explicitly aged out.

---

## 1. DSDV — Destination-Sequenced Distance Vector

**Files:** `routing/dsdv/dsdv.py` (`Dsdv`), `routing/dsdv/dsdv_routing_table.py`
(`DsdvRoutingTable`), `routing/dsdv/dsdv_packet.py` (`DsdvHelloPacket`)

DSDV is the simulator's **proactive** protocol: every drone continuously maintains a full
routing table to every other drone in the network, built by exchanging periodic table
broadcasts, in the classic Perkins & Bhagwat (1994) style.

### 1.1 Routing table structure

`DsdvRoutingTable.table` is a dict keyed by destination drone id:

```
table[dst_id] = [next_hop_id, metric (hop count), seq_num, updated_time]
```

- **next_hop_id** — id of the neighbor to forward through to reach `dst_id`.
- **metric** — hop count to `dst_id` (`inf` once the route is known to be broken).
- **seq_num** — DSDV's freshness counter, *owned by the destination itself*. Every drone
  seeds its own entry with an **even** sequence number: `identifier * 2`
  (`dsdv_routing_table.py:36`). Even numbers mean "live route originating at this node";
  DSDV's convention (not currently exercised by anything else in this codebase) is that odd
  numbers signal a broken route.
- **updated_time** — simulation time (μs) the entry was last refreshed, used for expiry.

### 1.2 Table exchange (hello packets)

`DsdvHelloPacket` (`dsdv_packet.py`) carries the sender's entire routing table
(`self.routing_table = routing_table`) plus a `packet_type` tag, either:
- `'periodic'` — the regular heartbeat, sent every `hello_interval` (0.5 s) + jitter by
  `broadcast_hello_packet_periodically()`. Each time a drone sends its own periodic
  broadcast it bumps its **own** sequence number by 2 first
  (`self.routing_table.table[my_id][2] += 2`, `dsdv.py:93`), keeping it even and
  monotonically increasing — this is what lets neighbors distinguish a newer advertisement
  of the same route from a stale one.
- `'immediate'` — a triggered update, fired only when a broken link is detected
  (see §1.3), and *re-flooded* by every drone that receives it for the first time.

### 1.3 Broken-link detection and triggered updates

`detect_broken_link_periodically()` runs every `purge_interval` (0.5 s) and calls
`routing_table.purge()`:

```python
for key in list(self.table):
    if key is not self.my_drone.identifier:
        if updated_time + entry_life_time < now:      # entry_life_time = 2e6 us
            expired_next_hop = self.table[key][0]
            for key2 in list(self.table):              # invalidate everything routed
                if self.table[key2][0] == expired_next_hop:  # through the dead neighbor
                    self.table[key2][1] = float('inf')
                    self.table[key2][2] += 1            # bump seq_num (now odd -> "broken")
                    self.table[key2][3] = now
            flag = 1
```

Any destination whose entry hasn't been refreshed in 2 s is presumed unreachable through its
current next hop; every other destination table entry that was routed *through that same next
hop* is invalidated too (metric set to infinity, sequence number incremented by one — making
it odd, the broken-route marker). If anything was invalidated, `dsdv.py` immediately broadcasts
an `'immediate'` hello with the whole (now partially invalidated) table
(`dsdv.py:65-85`). Any drone that receives an `'immediate'` packet for the first time
re-broadcasts it verbatim to its own neighbors (tracked via `processed_hello_packet` to avoid
infinite re-flooding), so the broken-link notification propagates network-wide by flood — this
is the "trigger update" half of classic DSDV.

### 1.4 Table update rule (Bellman-Ford-style, sequence-number-gated)

On receipt of any hello packet, `update_item()` walks every destination in the sender's
advertised table (`dsdv_routing_table.py:39-53`) and applies DSDV's standard acceptance rule:

```python
if dst_id not in self.table:                      # never seen -> accept
    accept
elif seq_num > self.table[dst_id][2]:              # strictly newer info -> accept
    accept
elif seq_num == self.table[dst_id][2]:
    if metric < self.table[dst_id][1]:             # same freshness, shorter path -> accept
        accept
else:
    pass                                            # stale info -> ignore
```

Accepted entries are installed as `[sender_id, metric + 1, seq_num, now]` — i.e., the
sender becomes the next hop, and the hop count is the sender's advertised metric plus one for
the hop to reach the sender.

### 1.5 Next-hop selection and forwarding

`next_hop_selection()` is a pure table lookup: `has_entry(dst_id)` returns the stored
`next_hop_id` if the destination is known and its metric isn't `inf`; otherwise it returns the
drone's own id, which `dsdv.py` interprets as "no route" (`has_route = False`), parking the
packet on `waiting_list` until a table update supplies a route or the packet's deadline expires.
There is no reactive route discovery (`enquire` is always `False`) — DSDV in this
implementation is purely proactive.

### 1.6 Data-packet and ACK handling

Once a next hop is chosen, `packet_reception()` on the receiving drone either delivers the
packet to the transport/metrics layer (if it's the destination) or re-queues it on its own
`transmitting_queue` for further forwarding (store-and-forward), and unicasts an `AckPacket`
back to the previous hop either way — this hop-by-hop ACK/retransmission behavior is identical
across all routing protocols in this codebase and is handled by the MAC layer
(`CsmaCa.send_ack` / `unblock_wait_ack`), not by DSDV itself.

### 1.7 Cost model and known behavior

DSDV's control traffic is **O(n)** per periodic broadcast per node (whole table each time) and
its triggered updates flood the entire network on every detected break, so total control
overhead grows with both node count and topology churn (mobility). This is a proactive,
always-fresh-table design: it gives the shortest available hop-count route whenever its tables
are converged, but its control-packet volume — periodic broadcasts plus triggered
flood-on-break — scales with network size and mobility, which is the direct cause of the
"DSDV wins at low density/short duration, collapses at high density/long duration" pattern
described in `Experiment.md`.

---

## 2. Greedy — Geographic Greedy Forwarding

**Files:** `routing/greedy/greedy.py` (`Greedy`), `routing/greedy/greedy_neighbor_table.py`
(`GreedyNeighborTable`), `routing/greedy/greedy_packet.py` (`GreedyHelloPacket`)

Greedy is the simulator's **stateless, position-based** protocol (a simplified 3D greedy-forwarding
scheme in the GPSR/geographic-routing family — see the file's reference [1]). It carries no
multi-hop routing table at all: every forwarding decision is made purely from the current
positions of one-hop neighbors.

### 2.1 Neighbor table structure

`GreedyNeighborTable.table` is a dict keyed by neighbor drone id:

```
table[neighbor_id] = [position (x, y, z), updated_time]
```

There is no destination/hop-count/sequence-number information at all — this is a **1-hop
neighbor position cache**, not a routing table.

### 2.2 Hello exchange

`GreedyHelloPacket` (`greedy_packet.py`) carries only the sender's current 3D coordinates
(`self.cur_position = src_drone.coords`) — no table, no sequence number. Every drone
broadcasts one every `hello_interval` (0.5 s) + jitter (`greedy.py:46-70`). On receipt,
`add_item()` simply overwrites (or inserts) that neighbor's position and timestamp
(`greedy_neighbor_table.py:32-42`) — last-writer-wins, no acceptance/freshness logic needed
since there's nothing to compare (positions aren't versioned; the newest hello is always
authoritative). Entries older than `entry_life_time` (2 s, inherited from `BaseTable`) are
dropped by `purge()`, called at the start of every `next_hop_selection()`
(`greedy.py:87`) — so the neighbor set used for a forwarding decision is always freshly culled.

### 2.3 Next-hop selection: pure greedy geographic forwarding

`best_neighbor()` (`greedy_neighbor_table.py:60-79`) implements the greedy-forwarding rule:

```python
best_distance = euclidean_distance_3d(my_drone.coords, dst_drone.coords)   # my own distance
best_id = my_drone.identifier                                              # default: no progress

for each neighbor in table:
    d = euclidean_distance_3d(neighbor.position, dst_drone.coords)
    if d < best_distance:
        best_distance = d
        best_id = neighbor.id
```

The packet is forwarded to whichever one-hop neighbor is geometrically closest to the
destination's *current* position — using straight-line 3D Euclidean distance
(`utils/util_function.euclidean_distance_3d`) — but **only if** that neighbor is strictly
closer to the destination than the current node itself is. If no neighbor makes progress
(a local minimum / "void" — `have_void_area` is set but this simplified implementation does
not include a face-routing/perimeter-mode recovery step, unlike full GPSR), `best_id` stays
equal to `my_drone.identifier`, `next_hop_selection()` reports `has_route = False`
(`greedy.py:94-97`), and the packet is parked on `waiting_list` for retry once the topology
(and thus the neighbor table) changes.

Crucially, this decision requires **zero knowledge of the destination's route** — only the
destination's own known position (carried in the packet as `dst_drone`, effectively perfect
destination-position knowledge in this simulation) and the sender's current one-hop neighbor
positions. There is no multi-hop state to keep consistent, which is the mechanism behind
Greedy's mobility- and scale-robustness relative to DSDV: nothing about its next-hop decision
can go "stale" the way a multi-hop DSDV route can, since it's recomputed from the latest known
positions on every forwarding decision.

### 2.4 Data-packet/ACK handling

Identical pattern to DSDV: on `packet_reception()`, a `DataPacket` addressed to the local drone
is delivered to metrics and ACKed back to the previous hop; otherwise it's re-queued for
further forwarding and still ACKed hop-by-hop. `check_waiting_list()` periodically retries
parked packets against the (possibly now-different) best neighbor.

### 2.5 Cost model and known behavior

Greedy's control overhead is **flat**: one hello packet per drone per interval, carrying only a
position (no table), regardless of network size, density, or how often the topology changes —
there is no analog of DSDV's triggered whole-network flood. This is the direct mechanism behind
Greedy's broad robustness across density, speed, duration, and map-size sweeps in
`Experiment.md`: its per-hop decision cost doesn't scale with anything that's growing in those
experiments. Its known weakness is the classic greedy-forwarding **local minimum** problem
(a node whose neighbors are all farther from the destination than itself, e.g., at the edge of
a void or a sparse map) — which this implementation does not attempt to route around; the
packet simply waits until mobility reshapes the neighbor set enough to find a next hop, or the
packet's deadline expires.

---

## 3. Side-by-side summary

| | DSDV | Greedy |
|---|---|---|
| Style | Proactive, table-driven (distance-vector) | Reactive-free, per-hop geographic |
| State per drone | Full routing table (route to *every* destination) | 1-hop neighbor position cache only |
| Hello packet payload | Entire routing table | Just (x, y, z) position |
| Freshness mechanism | Destination-owned even/odd sequence numbers | None needed — position always "current" |
| Triggered updates | Yes — broken link floods an `'immediate'` update network-wide | No — no network-wide signaling at all |
| Control overhead scaling | Grows with node count and topology churn | Flat — independent of node count/topology churn |
| Next-hop decision cost | O(1) table lookup | O(neighbors) distance comparison, recomputed per packet |
| Failure mode | Broadcast-storm collapse under density/duration/mobility | Local minimum (no recovery/perimeter mode) |
| Route "staleness" risk | Yes — multi-hop table entries can be stale between refreshes | No — decision uses only current 1-hop positions |
