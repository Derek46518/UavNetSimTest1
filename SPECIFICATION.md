# SPECIFICATION.md

# Mobility- and Congestion-Aware Greedy Routing (MC-Greedy)

## 1. Purpose

This specification defines a new routing protocol for the UavNetSimTest repository:

**Mobility- and Congestion-Aware Greedy Routing (MC-Greedy)**

Repository:

`Derek46518/UavNetSimTest`

The protocol is an extension of the existing Greedy geographic forwarding implementation.

The current Greedy algorithm selects the next-hop neighbor mainly by geographic distance to the destination. MC-Greedy must preserve the basic greedy forwarding rule, but rank valid forward-progress neighbors using three factors:

1. Geographic progress toward the destination.
2. Predicted mobility/link stability.
3. Current neighbor queue congestion.

MC-Greedy is **not** a machine-learning or reinforcement-learning protocol.

The implementation must be minimal, isolated, and easy to compare against the existing Greedy implementation.

---

# 2. Main Design Goal

The existing Greedy routing behavior can be summarized as:

```text
Current UAV
    |
    v
Find all known neighbors
    |
    v
Select the neighbor closest to the destination
    |
    v
Forward packet
```

MC-Greedy changes only the neighbor ranking step:

```text
Current UAV
    |
    v
Find all known neighbors
    |
    v
Keep only neighbors that make positive geographic progress
    |
    v
For each valid neighbor:
    |
    +-- Geographic progress
    |
    +-- Predicted link stability
    |
    +-- Queue congestion
    |
    v
Compute weighted score
    |
    v
Select highest-score neighbor
    |
    v
Forward packet
```

The protocol must continue to behave like Greedy routing: a next-hop candidate is only valid if it is closer to the destination than the current UAV.

---

# 3. Current Repository Behavior

The existing Greedy implementation is located at:

```text
routing/greedy/
├── __init__.py
├── greedy.py
├── greedy_neighbor_table.py
└── greedy_packet.py
```

Important current behavior:

- `routing/greedy/greedy.py`
  - Handles Hello broadcast.
  - Calls the neighbor table to select the next hop.
  - Handles DataPacket, AckPacket, Hello packet, and VfPacket reception.
  - Sends a Hello packet approximately every 0.5 seconds.
  - Uses the existing routing contract:
    - `next_hop_selection(packet)`
    - returns `(has_route, packet, enquire)`.

- `routing/greedy/greedy_neighbor_table.py`
  - Stores neighbor position and update time.
  - Current table structure is effectively:

```text
neighbor_id -> [position, update_time]
```

  - `best_neighbor()` selects the neighbor closest to the destination, but only if it is closer to the destination than the current UAV.

- `routing/greedy/greedy_packet.py`
  - Current Greedy Hello packet contains:
    - source UAV reference
    - current position

- `routing/base/base_table.py`
  - Uses the **last element** of each table entry as the update timestamp.
  - This behavior must not be broken.

- `entities/drone.py`
  - Each Drone already has:
    - `coords`
    - `velocity`
    - `transmitting_queue`
    - `max_queue_size`
    - `routing_protocol`
  - The current routing protocol is hardcoded to DSDV.

- `phy/large_scale_fading.py`
  - Provides `maximum_communication_range()`.

---

# 4. Protocol Definition

## 4.1 Name

**MC-Greedy**

Expanded name:

**Mobility- and Congestion-Aware Greedy Routing**

Suggested class names:

```text
MCGreedy
MCNeighborTable
MCHelloPacket
```

---

# 5. MC-Greedy Information Model

Each UAV participating in MC-Greedy must periodically advertise:

```text
UAV identifier
Current position
Current velocity
Current queue utilization
```

The information must be transmitted through the MC-Greedy Hello packet.

Do **not** directly read another UAV's queue or velocity from `simulator.drones[...]` during route selection.

The routing decision should use information learned through received Hello packets.

This is required so that the routing design remains conceptually distributed.

---

# 6. MC-Greedy Hello Packet

Create:

```text
routing/mc_greedy/mc_packet.py
```

The Hello packet must include:

```python
self.src_drone
self.cur_position
self.cur_velocity
self.queue_ratio
```

Values must be snapshots at packet creation time.

Recommended behavior:

```python
self.cur_position = list(src_drone.coords)
self.cur_velocity = list(src_drone.velocity)
```

Queue ratio:

```python
queue_ratio = src_drone.transmitting_queue.qsize() / src_drone.max_queue_size
```

Then clamp to:

```text
0.0 <= queue_ratio <= 1.0
```

If `max_queue_size <= 0`, use `queue_ratio = 0.0` as a defensive fallback.

The existing Hello packet interval should remain unchanged.

Do not create an additional periodic control process.

---

# 7. Neighbor Table

Create:

```text
routing/mc_greedy/mc_neighbor_table.py
```

The table entry structure must be:

```text
neighbor_id -> [
    position,
    velocity,
    queue_ratio,
    update_time
]
```

Example:

```python
self.table[drone_id] = [
    hello_packet.cur_position,
    hello_packet.cur_velocity,
    hello_packet.queue_ratio,
    cur_time,
]
```

## Important compatibility rule

`update_time` MUST remain the final element.

Do not change this:

```text
[position, velocity, queue_ratio, update_time]
```

into this:

```text
[position, update_time, velocity, queue_ratio]
```

because `BaseTable.get_updated_time()` assumes:

```python
self.table[drone_id][-1]
```

is the update time.

Use the existing `BaseTable.purge()` behavior.

Do not modify `routing/base/base_table.py`.

---

# 8. Candidate Eligibility Rule

MC-Greedy must preserve the current Greedy forward-progress restriction.

For current UAV `i`, candidate neighbor `j`, and destination `D`:

```text
candidate j is valid only when:

distance(j, D) < distance(i, D)
```

If this condition is false:

```text
skip the neighbor
```

This rule prevents MC-Greedy from choosing a low-congestion or stable neighbor that moves the packet backward.

Do not add perimeter routing, recovery routing, backtracking, or route discovery in this version.

If no forward-progress candidate exists, preserve existing Greedy behavior by returning the current UAV's own identifier from `best_neighbor()`.

This allows the existing `greedy.py` / waiting-list behavior to handle the no-route condition.

---

# 9. Routing Score

For each valid candidate neighbor `j`, compute:

```text
Score(j) =
    alpha * Progress(j)
  + beta  * Stability(j)
  - gamma * Congestion(j)
```

Version 1 default weights:

```text
alpha = 0.50
beta  = 0.30
gamma = 0.20
```

Therefore:

```text
Score(j) =
    0.50 * Progress(j)
  + 0.30 * Stability(j)
  - 0.20 * Congestion(j)
```

The candidate with the highest score becomes the next hop.

All three components must be normalized to approximately `[0, 1]`.

---

# 10. Geographic Progress

Let:

```text
d_current = distance(current UAV, destination)
d_neighbor = distance(candidate neighbor, destination)
R_max = maximum communication range
```

Then:

```text
Progress =
    (d_current - d_neighbor) / R_max
```

Clamp:

```text
0.0 <= Progress <= 1.0
```

Pseudo-code:

```python
progress = (current_distance - neighbor_distance) / max_range
progress = max(0.0, min(1.0, progress))
```

Use:

```python
euclidean_distance_3d(...)
```

from the existing utility functions.

Use:

```python
maximum_communication_range()
```

from:

```text
phy/large_scale_fading.py
```

Do not implement a second communication-range calculation.

---

# 11. Mobility / Link Stability

MC-Greedy should estimate whether the current UAV and candidate neighbor are likely to remain close enough to communicate.

Version 1 should use a simple linear future-position prediction.

Prediction horizon:

```text
0.5 seconds
```

Let current UAV position and velocity be:

```text
p_i
v_i
```

and the neighbor information from its most recently received Hello packet be:

```text
p_j
v_j
```

Predict:

```text
p_i_future = p_i + v_i * prediction_time
p_j_future = p_j + v_j * prediction_time
```

Then calculate:

```text
future_distance =
    distance(p_i_future, p_j_future)
```

Mobility stability:

```text
Stability =
    1 - future_distance / R_max
```

Clamp:

```text
0.0 <= Stability <= 1.0
```

Interpretation:

```text
1.0 -> predicted very stable/close
0.5 -> moderate
0.0 -> predicted at or beyond communication range
```

### Version 1 simplification

Do not compensate for Hello-packet measurement age in Version 1.

Do not add Kalman filters, trajectory prediction models, machine learning, or historical motion windows.

The objective is a minimal two-day implementation.

---

# 12. Congestion

Congestion is represented by the queue utilization reported by the candidate neighbor.

```text
Congestion =
    current transmitting queue size / maximum queue size
```

The Hello packet already carries this as:

```python
queue_ratio
```

Therefore route selection can simply use:

```python
congestion = queue_ratio
```

Clamp to `[0, 1]` when the Hello packet is created.

High congestion is bad, so it is subtracted from the score.

---

# 13. Next-Hop Selection Pseudo-code

The target logic is:

```python
def best_neighbor(self, my_drone, dst_drone):

    current_distance = euclidean_distance_3d(
        my_drone.coords,
        dst_drone.coords
    )

    max_range = maximum_communication_range()

    best_id = my_drone.identifier
    best_score = float("-inf")

    for neighbor_id, entry in self.table.items():

        neighbor_position = entry[0]
        neighbor_velocity = entry[1]
        queue_ratio = entry[2]

        neighbor_distance = euclidean_distance_3d(
            neighbor_position,
            dst_drone.coords
        )

        # Preserve original greedy behavior.
        if neighbor_distance >= current_distance:
            continue

        progress = calculate_progress(...)

        stability = calculate_stability(...)

        congestion = queue_ratio

        score = (
            0.50 * progress
            + 0.30 * stability
            - 0.20 * congestion
        )

        if score > best_score:
            best_score = score
            best_id = neighbor_id
            self.have_void_area = 0

    return best_id
```

Do not add randomness to next-hop selection.

If scores are exactly equal, keeping the first best candidate encountered is acceptable for Version 1.

---

# 14. Required New Files

Create only these new protocol files:

```text
routing/mc_greedy/__init__.py
routing/mc_greedy/mc_greedy.py
routing/mc_greedy/mc_neighbor_table.py
routing/mc_greedy/mc_packet.py
```

The implementation should reuse as much of the existing Greedy behavior as possible.

---

# 15. Allowed Existing Files to Modify

For the protocol implementation, modifications are permitted only in:

```text
entities/drone.py
utils/config.py
```

Optional experimental parameterization may additionally modify:

```text
simulator/simulator.py
```

Do not modify other existing files unless there is an unavoidable compatibility problem.

If an unexpected dependency requires changing another existing file, STOP and report the issue instead of making the change automatically.

---

# 16. Routing Protocol Selector

The current `Drone` hardcodes DSDV.

Add a routing selector to:

```text
utils/config.py
```

Recommended:

```python
ROUTING_PROTOCOL = "dsdv"
```

Keep `"dsdv"` as the default so this change does not silently alter existing simulator behavior.

Supported values for this task:

```text
"dsdv"
"greedy"
"mc_greedy"
```

In:

```text
entities/drone.py
```

instantiate the appropriate protocol.

Conceptually:

```python
if config.ROUTING_PROTOCOL == "greedy":
    self.routing_protocol = Greedy(self.simulator, self)

elif config.ROUTING_PROTOCOL == "mc_greedy":
    self.routing_protocol = MCGreedy(self.simulator, self)

else:
    self.routing_protocol = Dsdv(self.simulator, self)
```

Do not delete DSDV support.

Do not make MC-Greedy the permanent hardcoded protocol.

---

# 17. MC-Greedy Protocol Class

`routing/mc_greedy/mc_greedy.py` should be based on the existing:

```text
routing/greedy/greedy.py
```

Keep the following behavior unchanged unless required by MC-Greedy:

```text
Hello scheduling
channel assignment
control-packet metric accounting
DataPacket handling
ACK generation
ACK processing
SIFS handling
retransmission interactions
waiting_list behavior
VfPacket handling
packet expiry behavior
```

Only protocol-specific changes should include:

```text
GreedyHelloPacket -> MCHelloPacket
GreedyNeighborTable -> MCNeighborTable
class Greedy -> class MCGreedy
imports
```

`next_hop_selection()` must continue returning:

```python
(has_route, packet, enquire)
```

Do not change this interface.

`check_waiting_list()` should use the new MC neighbor table's `best_neighbor()`.

---

# 18. Packet Reception

When receiving:

```python
MCHelloPacket
```

MC-Greedy must call:

```python
self.neighbor_table.add_item(packet, current_time)
```

This stores:

```text
position
velocity
queue ratio
timestamp
```

All existing behavior for:

```text
DataPacket
AckPacket
VfPacket
```

should remain functionally equivalent to the existing Greedy implementation.

Do not redesign packet reception.

---

# 19. Configuration Constants

Add protocol-specific constants to:

```text
utils/config.py
```

Recommended names:

```python
MC_GREEDY_PROGRESS_WEIGHT = 0.50
MC_GREEDY_STABILITY_WEIGHT = 0.30
MC_GREEDY_CONGESTION_WEIGHT = 0.20

MC_GREEDY_PREDICTION_TIME = 0.50  # seconds
```

Use these constants from `mc_neighbor_table.py`.

Do not hardcode the same values in multiple files.

Optional defensive check:

```text
progress weight + stability weight + congestion weight does not have to sum to 1 mathematically,
but Version 1 defaults should remain 0.50 / 0.30 / 0.20.
```

---

# 20. Optional Experiment Configuration

This is secondary to the protocol implementation.

Only implement after MC-Greedy runs correctly.

## UAV speed

The homogeneous UAV speed is currently hardcoded in the simulator.

Optionally add:

```python
DRONE_SPEED = 10
```

to `utils/config.py`.

Then use it in `simulator/simulator.py`.

This allows tests such as:

```text
5 m/s
10 m/s
15 m/s
20 m/s
25 m/s
```

Do not modify the Gauss-Markov mobility algorithm.

## Packet generation rate

The current Poisson traffic rate is hardcoded in `entities/drone.py`.

Optionally add:

```python
PACKET_GENERATION_RATE = 5
```

to `utils/config.py`.

Then use:

```python
rate = config.PACKET_GENERATION_RATE
```

This allows tests such as:

```text
5 packets/s
10 packets/s
15 packets/s
20 packets/s
```

Do not change the Poisson traffic-generation logic.

---

# 21. Logging

Temporary diagnostic logging is allowed.

Recommended diagnostic information:

```text
current UAV
candidate neighbor ID
progress
stability
congestion
final score
selected next hop
```

Prefer:

```python
logger.debug(...)
```

rather than large amounts of new `INFO` logging.

Do not permanently flood normal simulations with per-candidate INFO logs.

---

# 22. Implementation Order

The AI agent must implement in this order.

## Step 1 — Inspect current implementation

Read:

```text
routing/greedy/greedy.py
routing/greedy/greedy_neighbor_table.py
routing/greedy/greedy_packet.py
routing/base/base_table.py
entities/drone.py
utils/config.py
phy/large_scale_fading.py
```

Confirm actual class/function names before editing.

Do not assume the specification's pseudo-code is a byte-for-byte replacement.

---

## Step 2 — Create MC-Greedy package

Create:

```text
routing/mc_greedy/
```

with:

```text
__init__.py
mc_greedy.py
mc_neighbor_table.py
mc_packet.py
```

Start from copies/adaptations of the existing Greedy protocol where appropriate.

Do not edit the baseline Greedy files.

---

## Step 3 — Implement MCHelloPacket

Add snapshot fields:

```text
position
velocity
queue ratio
```

Preserve the existing Packet inheritance and constructor behavior.

---

## Step 4 — Implement MCNeighborTable

Store:

```text
[position, velocity, queue_ratio, update_time]
```

Ensure update time remains the final field.

Reuse BaseTable behavior.

---

## Step 5 — Implement scoring helpers

Implement logically separate helpers for:

```text
geographic progress
mobility stability
```

Congestion may use the stored queue ratio directly.

Keep helper functions small and deterministic.

---

## Step 6 — Implement best_neighbor()

Requirements:

1. Determine current UAV-to-destination distance.
2. Iterate current neighbor-table entries.
3. Reject neighbors that do not make positive geographic progress.
4. Calculate normalized progress.
5. Calculate normalized predicted stability.
6. Read normalized congestion.
7. Calculate weighted score.
8. Select highest-scoring candidate.
9. If no valid candidate exists, return current UAV identifier.

---

## Step 7 — Implement MCGreedy protocol class

Adapt existing Greedy class.

Use:

```text
MCHelloPacket
MCNeighborTable
```

Keep existing packet/ACK/waiting-list behavior unchanged.

---

## Step 8 — Add protocol selector

Modify only:

```text
utils/config.py
entities/drone.py
```

Add selectable:

```text
dsdv
greedy
mc_greedy
```

Keep DSDV as the default.

---

## Step 9 — Syntax/import validation

Before running a simulation:

- Ensure all imports resolve.
- Ensure no circular import was introduced.
- Ensure new package has `__init__.py`.
- Ensure class names match imports.
- Ensure `next_hop_selection()` keeps the existing return contract.

---

## Step 10 — Smoke test

Run a short simulation using:

```text
ROUTING_PROTOCOL = "mc_greedy"
```

Verify:

```text
simulation starts
Hello packets are sent
MCHelloPackets are received
neighbor table receives position/velocity/queue
next-hop selection executes
DataPackets are forwarded
ACK behavior still works
simulation completes
metrics still print
```

The first test is about correctness, not performance improvement.

---

## Step 11 — Baseline regression test

Switch to:

```text
ROUTING_PROTOCOL = "greedy"
```

Run again.

Verify the original Greedy protocol still works.

Do not accept the implementation if baseline Greedy has been changed or broken.

---

## Step 12 — Optional experiment parameterization

Only after Steps 1–11 succeed:

- add configurable homogeneous speed
- add configurable packet generation rate

Do not alter the mobility or traffic models themselves.

---

# 23. Guardrails

These rules are mandatory.

## 23.1 Do not modify the existing Greedy protocol

Do not edit:

```text
routing/greedy/greedy.py
routing/greedy/greedy_neighbor_table.py
routing/greedy/greedy_packet.py
```

The existing Greedy implementation is the experimental baseline.

---

## 23.2 Do not modify unrelated network modules

Do not modify:

```text
mac/
phy/
energy/
mobility/
topology/
allocation/
path_planning/
visualization/
simulator/metrics.py
entities/packet.py
routing/base/
```

Exception:

```text
simulator/simulator.py
```

may be changed only for optional `DRONE_SPEED` parameterization.

Do not refactor these modules.

---

## 23.3 Do not change MAC/PHY behavior

Do not change:

```text
CSMA/CA
ACK handling
ACK timeout
retransmission limit
SINR model
path-loss model
collision behavior
channel assignment
bit rate
transmitting power
```

MC-Greedy is a routing-layer experiment.

---

## 23.4 Do not change mobility behavior

Do not modify:

```text
Gauss-Markov equations
position update interval
direction update interval
boundary behavior
velocity update equations
```

Velocity is only consumed as routing information.

---

## 23.5 Do not change metrics

Do not modify:

```text
PDR
E2E delay
throughput
hop count
routing load
collision count
MAC delay
```

Use the existing `Metrics` implementation as-is.

---

## 23.6 Do not introduce ML/RL

Do not add:

```text
PyTorch
TensorFlow
Q-learning
DQN
PPO
MAPPO
neural networks
training loops
replay buffers
```

MC-Greedy is deterministic heuristic routing.

---

## 23.7 Do not redesign queue behavior

Do not change:

```text
queue.Queue
max_queue_size
queue drop behavior
feed_packet()
blocking()
waiting_list
```

Only observe queue utilization.

---

## 23.8 Do not add direct global neighbor-state access

Route selection must not do this:

```python
neighbor = self.simulator.drones[neighbor_id]
queue = neighbor.transmitting_queue.qsize()
velocity = neighbor.velocity
```

for MC-Greedy decision data.

Use information stored from MCHelloPacket.

The current UAV's own live state may be used directly.

---

## 23.9 Do not alter Hello scheduling

Reuse the Greedy Hello interval.

Do not create a second periodic neighbor-state broadcast.

Do not change Hello frequency unless separately requested.

---

## 23.10 Do not alter Hello packet simulated size in Version 1

For this prototype, keep the existing configured Hello packet length.

The additional Python object fields are treated as metadata for the routing experiment.

Do not change global packet-length constants or MAC timing to account for the new fields in Version 1.

Document this as a model simplification if necessary.

---

## 23.11 Avoid broad refactoring

Do not:

```text
rename unrelated classes
move directories
rewrite Drone
rewrite BaseTable
introduce new architecture/framework layers
format the entire repository
change unrelated imports
```

Make the smallest change needed to implement the protocol.

---

## 23.12 If the repository conflicts with this specification

If implementation cannot follow the specification because actual code differs materially:

1. Stop.
2. Report the conflict.
3. Identify the smallest required deviation.
4. Do not modify additional modules without approval.

---

# 24. Non-Goals

The following are explicitly outside Version 1:

```text
MARL / MAPPO
Q-learning
GMDC clustering
GNNs
Belief graphs
digital twins
energy-aware routing
adaptive transmit power
MAC optimization
resource allocation
trajectory optimization
perimeter routing
void recovery
multi-path routing
opportunistic forwarder sets
security mechanisms
failure recovery
Hello-message compression
measurement-age compensation
advanced link-lifetime prediction
```

Do not implement these.

---

# 25. Acceptance Criteria

The task is complete only when all of the following are true:

- [ ] Existing Greedy files remain unchanged.
- [ ] `routing/mc_greedy/` exists.
- [ ] `MCHelloPacket` carries position, velocity, and queue ratio.
- [ ] `MCNeighborTable` stores `[position, velocity, queue_ratio, update_time]`.
- [ ] BaseTable timestamp semantics remain compatible.
- [ ] MC-Greedy keeps the positive geographic-progress rule.
- [ ] Geographic progress is normalized.
- [ ] Mobility stability is calculated using a 0.5-second linear prediction.
- [ ] Congestion uses reported queue ratio.
- [ ] Default score is `0.50*progress + 0.30*stability - 0.20*congestion`.
- [ ] `best_neighbor()` returns the current UAV ID when no valid forward-progress neighbor exists.
- [ ] `next_hop_selection()` retains the original return contract.
- [ ] Existing DataPacket / ACK / waiting-list behavior is preserved.
- [ ] A config-based selector can run DSDV, Greedy, or MC-Greedy.
- [ ] DSDV remains the default routing protocol.
- [ ] A short MC-Greedy simulation completes without error.
- [ ] A Greedy baseline simulation still completes without error.
- [ ] Existing metrics still print normally.
- [ ] No unrelated modules have been modified.

---

# 26. Recommended Validation Scenarios

## Basic functional test

```text
10 UAVs
existing simulation time
existing traffic rate
existing mobility configuration
MC-Greedy
```

Goal:

```text
No exceptions
Packets forwarded
Metrics produced
```

## Mobility comparison

After protocol correctness is confirmed:

```text
Greedy vs MC-Greedy
```

at homogeneous speeds:

```text
5 m/s
10 m/s
15 m/s
20 m/s
25 m/s
```

Primary metrics:

```text
PDR
E2E delay
hop count
```

## Congestion comparison

After packet-rate parameterization:

```text
Greedy vs MC-Greedy
```

at:

```text
5 packets/s
10 packets/s
15 packets/s
20 packets/s
```

Primary metrics:

```text
PDR
E2E delay
throughput
```

---

# 27. Expected Research Interpretation

MC-Greedy is expected to differ from normal Greedy when the geographically closest next-hop candidate is:

```text
moving rapidly away from the current UAV
or
highly congested
```

Normal Greedy may still select that neighbor because it only prioritizes destination distance.

MC-Greedy may select a slightly less geographically aggressive candidate if that candidate:

```text
still makes positive progress
has better predicted link stability
has lower queue congestion
```

This creates a reliability/delay versus shortest-geographic-progress tradeoff.

The implementation must not assume MC-Greedy will always outperform Greedy. Experimental results determine that.

---

# 28. Final Protocol Summary

```text
MCHelloPacket
    |
    +-- position
    +-- velocity
    +-- queue ratio
    |
    v
MCNeighborTable
    |
    v
Packet needs next hop
    |
    v
Remove non-forward-progress neighbors
    |
    v
For each remaining neighbor:
    |
    +-- P = normalized geographic progress
    +-- S = predicted link stability
    +-- C = queue congestion
    |
    v
Score = 0.50 P + 0.30 S - 0.20 C
    |
    v
Select highest score
    |
    v
Use existing UavNetSim packet / MAC / ACK behavior
```

The implementation should remain a small routing-layer extension of UavNetSimTest, not a broader simulator redesign.
