# SPECIFICATION2.md

# CR-QGeo: Congestion- and Reliability-Aware Q-Learning Geographic Routing

## 1. Purpose

This specification defines a new routing protocol for the UavNetSimTest codebase:

**CR-QGeo — Congestion- and Reliability-Aware Q-Learning Geographic Routing**

CR-QGeo is an isolated extension of the existing QGeo routing protocol.

The goal is **not** to replace QGeo's Q-learning framework. The goal is to improve the feedback used by QGeo so that learned next-hop choices account for:

1. Geographic progress toward the destination.
2. Queue congestion at the selected next hop.
3. Predicted reliability/stability of the wireless link.

This specification is standalone. The implementation agent must not depend on any previous specification file.

The local working tree may already contain previously implemented protocols such as MC-Greedy or a routing-protocol selector. Preserve any existing work unless this specification explicitly requires an extension.

---

# 2. Core Research Idea

The current QGeo implementation already learns a Q-value for forwarding through neighboring UAVs toward destinations.

Conceptually:

```text
Select next hop
    |
    v
Transmit packet
    |
    v
Receive ACK / feedback
    |
    v
Calculate reward
    |
    v
Update Q-value
    |
    v
Future next-hop choices improve
```

Current QGeo mainly rewards geographic forwarding progress and uses a coarse mobility-aware discount factor.

CR-QGeo keeps the same learning architecture but changes two pieces:

```text
Current QGeo
============

Immediate reward:
    geographic progress

Mobility discount:
    gamma = 0.6 if predicted link remains in range
    gamma = 0.4 otherwise


CR-QGeo
=======

Immediate reward:
    geographic progress
    - congestion penalty

Mobility discount:
    continuous gamma based on predicted link stability
```

The intended result is a routing learner that avoids repeatedly forwarding through highly congested or weakly persistent links even if those links appear geographically attractive.

---

# 3. Protocol Name and Classes

Protocol name:

```text
CR-QGeo
```

Expanded name:

```text
Congestion- and Reliability-Aware Q-Learning Geographic Routing
```

Recommended class names:

```text
CRQGeo
CRQGeoTable
CRQGeoHelloPacket
CRQGeoAckPacket
```

Recommended package:

```text
routing/cr_qgeo/
├── __init__.py
├── cr_qgeo.py
├── cr_qgeo_table.py
└── cr_qgeo_packet.py
```

---

# 4. Existing QGeo Behavior That Must Be Preserved

Before implementing CR-QGeo, inspect the current local versions of:

```text
routing/qgeo/qgeo.py
routing/qgeo/qgeo_table.py
routing/qgeo/qgeo_packet.py
routing/base/base_table.py
entities/drone.py
utils/config.py
phy/large_scale_fading.py
```

The current QGeo implementation is expected to provide the following concepts:

- Periodic Hello packets.
- Neighbor table maintenance.
- Position and velocity information.
- A Q-table indexed approximately as:

```text
Q[next_hop][destination]
```

- Exploration/exploitation next-hop selection.
- Destination success reward.
- Void-area / failed-forwarding penalty.
- Q-value update after receiving a QGeo ACK.
- Mobility prediction used to choose the discount factor.
- Waiting-list behavior.
- ACK-based retransmission integration.

The exact local code is the source of truth for interfaces and names.

Do not rewrite the Q-learning architecture.

Do not modify the baseline QGeo implementation.

---

# 5. What Changes in CR-QGeo

CR-QGeo introduces only two algorithmic changes.

## Change A — Congestion-aware immediate reward

For a successful non-terminal intermediate forwarding step:

```text
Reward =
    GeographicProgress
    - CongestionWeight * CongestionRatio
```

Version 1 default:

```text
CongestionWeight = 0.40
```

Therefore:

```text
Reward =
    GeographicProgress
    - 0.40 * CongestionRatio
```

## Change B — Continuous mobility-aware discount factor

Instead of using only two possible gamma values based on whether a predicted link is inside/outside communication range, compute a continuous link-stability score.

Then map that score to gamma.

Version 1 defaults:

```text
GammaMin = 0.30
GammaMax = 0.90
```

---

# 6. What Does NOT Change

The following QGeo behaviors must remain unchanged unless required only for class-name adaptation:

```text
Q-table structure
learning rate
exploration schedule
best-Q exploitation behavior
random exploration behavior
destination terminal reward
void-area penalty
failed-transmission penalty
waiting-list behavior
Hello scheduling
packet lifetime behavior
ACK timing
MAC behavior
PHY behavior
mobility model
energy model
metrics
```

CR-QGeo must still be recognizable as QGeo with improved reward/reliability feedback.

---

# 7. Immediate Reward Definition

## 7.1 Geographic progress

For:

```text
previous hop = i
current receiving UAV = j
destination = D
```

let:

```text
d_prev = distance(i, D)
d_cur  = distance(j, D)
R_max  = maximum communication range
```

Then:

```text
Progress =
    (d_prev - d_cur) / R_max
```

Use the repository's existing:

```python
euclidean_distance_3d(...)
```

and:

```python
maximum_communication_range()
```

Do not duplicate these utilities.

### Important

Do not clamp geographic progress unless the existing QGeo implementation already does so.

Preserve current QGeo reward scaling as much as possible.

The congestion term should be added to the existing progress reward, not replace it.

---

# 8. Congestion Definition

Congestion is the queue occupancy of the receiving next-hop UAV.

Use:

```text
CongestionRatio =
    transmitting_queue.qsize()
    / max_queue_size
```

Clamp to:

```text
0.0 <= CongestionRatio <= 1.0
```

If:

```text
max_queue_size <= 0
```

use:

```text
CongestionRatio = 0.0
```

as a defensive fallback.

## 8.1 When congestion must be sampled

For an intermediate UAV receiving a data packet:

1. Check whether the local transmitting queue has capacity using the existing logic.
2. Before enqueuing the newly received packet, snapshot the current queue ratio.
3. Enqueue the packet using the existing behavior.
4. Use the snapshot as the congestion term in the reward.

This avoids counting the current packet itself as pre-existing congestion.

Pseudo-code:

```python
queue_ratio = (
    self.my_drone.transmitting_queue.qsize()
    / self.my_drone.max_queue_size
)

queue_ratio = max(0.0, min(1.0, queue_ratio))

self.my_drone.transmitting_queue.put(packet_copy)

reward = progress - congestion_weight * queue_ratio
```

Do not change queue capacity or drop behavior.

---

# 9. Reward Rules by Outcome

CR-QGeo must use the following priority.

## Case 1 — Destination reached

Preserve the existing QGeo terminal success reward.

Expected default:

```text
reward = r_max
```

Do not subtract congestion at the destination.

Terminal delivery success takes priority over the congestion penalty.

## Case 2 — Intermediate node accepted the packet and has a non-void forwarding state

Use:

```text
reward =
    geographic_progress
    - congestion_weight * congestion_ratio
```

Default:

```text
congestion_weight = 0.40
```

## Case 3 — Intermediate node is in a void-area condition

Preserve the existing QGeo void-area penalty.

Expected behavior:

```text
reward = r_min
max_q = 0
```

Do not mix the congestion reward with the void penalty.

## Case 4 — Queue is full

Preserve the existing behavior:

```text
drop / do not ACK
```

Do not create a special new ACK for queue-full failure.

The previous sender's existing ACK-timeout / penalize mechanism should eventually apply the existing failure penalty.

## Case 5 — No ACK / failed transmission

Preserve the existing `penalize()` behavior.

Expected:

```text
reward = r_min
```

Do not create a second failure penalty.

---

# 10. Continuous Mobility Reliability

The current QGeo implementation already predicts future distance between the current UAV and the selected next-hop UAV during Q-value updates.

CR-QGeo must reuse that prediction mechanism.

Do not introduce a new trajectory model.

Do not add machine learning.

Do not change the Gauss-Markov mobility model.

---

# 11. Link Stability Score

Let:

```text
future_distance = predicted distance between sender and selected next hop
R_max = maximum communication range
```

Compute:

```text
Stability =
    1 - future_distance / R_max
```

Clamp:

```text
0.0 <= Stability <= 1.0
```

Pseudo-code:

```python
stability = 1.0 - future_distance / max_range
stability = max(0.0, min(1.0, stability))
```

Interpretation:

```text
Stability = 1.0
    -> very strong predicted persistence

Stability = 0.5
    -> moderate predicted persistence

Stability = 0.0
    -> at or beyond predicted communication range
```

---

# 12. Continuous Discount Factor

Map stability to gamma:

```text
gamma =
    GammaMin
    + (GammaMax - GammaMin) * Stability
```

Version 1 defaults:

```text
GammaMin = 0.30
GammaMax = 0.90
```

Equivalent:

```text
gamma = 0.30 + 0.60 * Stability
```

Examples:

```text
Stability = 0.00 -> gamma = 0.30
Stability = 0.25 -> gamma = 0.45
Stability = 0.50 -> gamma = 0.60
Stability = 0.75 -> gamma = 0.75
Stability = 1.00 -> gamma = 0.90
```

This replaces only the current binary gamma choice.

Do not otherwise change the Q-learning update.

---

# 13. Q-Learning Update

Preserve the current QGeo update form.

Conceptually:

```text
Q <- (1 - learning_rate) * Q
     + learning_rate *
       (reward + gamma * (1 - terminal_flag) * max_q)
```

The only intended changes are:

```text
reward:
    geographic progress
    -> geographic progress - congestion penalty

gamma:
    binary mobility value
    -> continuous mobility reliability value
```

Do not change:

```text
learning_rate
terminal flag behavior
max_q calculation
destination indexing
Q-table shape
```

unless required to match the local QGeo interface.

---

# 14. Next-Hop Selection

CR-QGeo must preserve current QGeo next-hop selection.

The protocol should continue to choose actions from learned Q-values using the existing exploration/exploitation policy.

Do not add a second weighted next-hop score.

Do not use:

```text
Q-value - queue penalty
```

during action selection.

Do not directly combine geographic distance, queue ratio, or mobility into the next-hop selector.

Those signals belong in learning feedback.

This distinction is important:

```text
MC-Greedy:
    metrics -> immediate action score

CR-QGeo:
    metrics -> reward/reliability feedback -> Q-learning -> future actions
```

---

# 15. Exploration Policy

Preserve the existing QGeo exploration logic exactly.

Do not change:

```text
exploration probability
exploration decay
random neighbor choice
tie-breaking behavior
```

The purpose of this protocol is not to test a new exploration policy.

---

# 16. Hello Packets

CR-QGeo should preserve QGeo Hello scheduling and its required mobility information.

The CR-QGeo Hello packet must carry at least:

```text
source UAV
current position
current velocity
```

No queue-ratio field is required for the core Version 1 algorithm.

Reason:

```text
Congestion is sampled by the actual receiving next-hop UAV at packet reception time,
then incorporated into the ACK reward.
```

This provides fresher congestion feedback than relying on a possibly stale Hello advertisement.

Do not add a second control-message process.

Do not change the Hello interval.

Do not change the simulated Hello packet size in Version 1.

---

# 17. ACK Packet

Create an isolated CR-QGeo ACK packet class based on the existing QGeo ACK structure.

It must continue to carry the information required by the existing learning loop, expected to include concepts such as:

```text
source UAV
source position
source velocity
destination/previous sender
acked packet
void-area flag
reward
max_q
channel information
```

Do not redesign ACK semantics.

The congestion penalty should already be incorporated into the `reward` value before the ACK is created.

No separate congestion field is required in Version 1.

---

# 18. Neighbor Table

Create an isolated:

```text
CRQGeoTable
```

based on the current QGeo table.

Preserve:

```text
neighbor position
neighbor velocity
update timestamp
Q-table
void-area judgment
get_max_q_value()
best_neighbor()
```

The expected neighbor entry remains conceptually:

```text
neighbor_id -> [
    position,
    velocity,
    update_time
]
```

The update timestamp must remain the final field because BaseTable expects the final element to be the update time.

Do not modify `routing/base/base_table.py`.

---

# 19. New Files

Create:

```text
routing/cr_qgeo/__init__.py
routing/cr_qgeo/cr_qgeo.py
routing/cr_qgeo/cr_qgeo_table.py
routing/cr_qgeo/cr_qgeo_packet.py
```

The new package must be independent from the baseline QGeo package.

Do not edit files inside:

```text
routing/qgeo/
```

---

# 20. Existing Files Allowed to Modify

For the core CR-QGeo implementation, modifications are allowed only in:

```text
entities/drone.py
utils/config.py
```

These modifications should only:

```text
import/register CR-QGeo
add CR-QGeo configuration constants
extend the existing routing selector
```

If the local working tree already has a routing selector from previous work, extend it.

Do not replace or simplify it in a way that removes existing protocols.

---

# 21. Routing Selector Compatibility

The local repository may already support values such as:

```text
dsdv
greedy
mc_greedy
```

and may or may not already support:

```text
qgeo
```

The agent must inspect the current local `entities/drone.py` and `utils/config.py`.

Extend the current selector rather than replacing it.

At minimum, CR-QGeo should be selectable as:

```text
"cr_qgeo"
```

If `"qgeo"` is not yet supported by the selector, add it as well so the baseline can be run.

Do not remove any previously supported routing protocol.

Do not change the existing default protocol unless explicitly necessary for a test.

---

# 22. Configuration Constants

Add CR-QGeo-specific constants to:

```text
utils/config.py
```

Recommended:

```python
CR_QGEO_CONGESTION_WEIGHT = 0.40
CR_QGEO_GAMMA_MIN = 0.30
CR_QGEO_GAMMA_MAX = 0.90
```

Use these constants from the CR-QGeo implementation.

Do not hardcode the same values in multiple files.

Do not modify baseline QGeo constants.

---

# 23. Diagnostic Logging

Temporary diagnostic logging is encouraged during validation.

Recommended values:

```text
packet ID
previous-hop ID
current/next-hop ID
geographic progress
queue ratio
congestion penalty
final reward
future distance
stability
gamma
old Q-value
new Q-value
```

Prefer:

```python
logger.debug(...)
```

Avoid flooding normal simulations with new INFO logs.

---

# 24. Implementation Steps

The AI agent must work in the following order.

## Step 1 — Inspect the actual working tree

Read the current local versions of:

```text
routing/qgeo/qgeo.py
routing/qgeo/qgeo_table.py
routing/qgeo/qgeo_packet.py
routing/base/base_table.py
entities/drone.py
utils/config.py
phy/large_scale_fading.py
```

Also inspect any existing:

```text
routing/mc_greedy/
```

only to ensure it is not overwritten.

Do not assume the remote repository exactly matches the local working tree.

## Step 2 — Understand the current QGeo learning flow

Before editing, identify:

```text
where Hello packets are sent
where neighbor state is stored
where best_neighbor() chooses the action
where intermediate reward is calculated
where ACK reward is created
where ACK is processed
where gamma is calculated
where Q is updated
where no-ACK failure is penalized
```

Do not proceed until these locations are understood.

## Step 3 — Create the CR-QGeo package

Create:

```text
routing/cr_qgeo/
```

with:

```text
__init__.py
cr_qgeo.py
cr_qgeo_table.py
cr_qgeo_packet.py
```

Start from the existing QGeo implementation where appropriate.

Rename classes/imports carefully.

Do not edit baseline QGeo files.

## Step 4 — Implement CRQGeoPacket classes

Create isolated:

```text
CRQGeoHelloPacket
CRQGeoAckPacket
```

Preserve QGeo packet semantics.

Hello should contain:

```text
source
position
velocity
```

ACK should preserve all information required for Q-learning.

Do not add unnecessary fields.

## Step 5 — Implement CRQGeoTable

Copy/adapt QGeoTable behavior into:

```text
CRQGeoTable
```

Preserve:

```text
neighbor-table semantics
Q-table initialization
void-area judgment
max-Q lookup
best-neighbor exploration/exploitation
purge behavior
```

Do not change the learning policy here.

## Step 6 — Implement congestion snapshot helper

In `cr_qgeo.py`, add a small helper or equivalent local logic:

```python
def get_queue_ratio(drone):
    ...
```

Requirements:

```text
read transmitting_queue.qsize()
divide by max_queue_size
defensive handling for max_queue_size <= 0
clamp to [0,1]
```

Do not alter queue behavior.

## Step 7 — Modify intermediate reward

At the point where the current QGeo implementation calculates the intermediate geographic reward:

1. Capture queue ratio before enqueuing the received packet.
2. Preserve existing successful enqueue behavior.
3. Preserve existing void-area detection.
4. If non-void:

```text
progress =
    existing geographic progress reward

reward =
    progress
    - CR_QGEO_CONGESTION_WEIGHT * queue_ratio
```

5. If void:

```text
reward = r_min
max_q = 0
```

6. Put the final reward into `CRQGeoAckPacket`.

Do not alter destination reward.

## Step 8 — Implement continuous gamma

Locate the current QGeo code that:

```text
predicts future sender/next-hop positions
computes future distance
chooses gamma = 0.6 or 0.4
```

Preserve the existing future-position prediction method.

Replace only the binary gamma decision with:

```python
max_range = maximum_communication_range()

stability = 1.0 - future_distance / max_range
stability = max(0.0, min(1.0, stability))

gamma = (
    config.CR_QGEO_GAMMA_MIN
    + (
        config.CR_QGEO_GAMMA_MAX
        - config.CR_QGEO_GAMMA_MIN
      ) * stability
)
```

Do not change the rest of the Q update.

## Step 9 — Preserve penalties and terminal behavior

Verify:

```text
destination -> r_max
void area -> r_min
no ACK -> existing penalize() behavior
queue full -> existing drop/no-ACK behavior
```

Do not add duplicate penalties.

## Step 10 — Extend routing selector

Inspect current local selector.

Add:

```text
qgeo
cr_qgeo
```

if needed.

Preserve all existing protocol options.

Do not remove:

```text
mc_greedy
greedy
dsdv
```

or any other local protocol.

## Step 11 — Add CR-QGeo config values

Add only:

```python
CR_QGEO_CONGESTION_WEIGHT = 0.40
CR_QGEO_GAMMA_MIN = 0.30
CR_QGEO_GAMMA_MAX = 0.90
```

unless equivalent local configuration already exists.

Avoid duplicate constants.

## Step 12 — Static validation

Before simulation:

- Verify imports.
- Verify class names.
- Verify no circular imports.
- Verify `routing/cr_qgeo/__init__.py` exists.
- Verify `next_hop_selection()` keeps the expected interface.
- Verify packet-reception remains a SimPy generator where required.
- Verify BaseTable timestamp layout is preserved.
- Verify Q-table shape/indexing is unchanged.

## Step 13 — CR-QGeo smoke test

Run a short simulation with:

```text
ROUTING_PROTOCOL = "cr_qgeo"
```

Verify:

```text
simulation starts
Hello packets work
neighbor table populates
data packets are forwarded
ACKs return
rewards are calculated
Q-values update
continuous gamma is calculated
waiting-list behavior works
simulation completes
existing metrics print
```

The first goal is correctness, not performance.

## Step 14 — QGeo baseline regression test

Run the exact same simulation seed/configuration using:

```text
ROUTING_PROTOCOL = "qgeo"
```

Verify:

```text
baseline QGeo still runs
baseline QGeo code was not modified
metrics still print
```

## Step 15 — Compare debug traces

For at least a few packets, confirm that:

```text
QGeo:
    reward = geographic progress
    gamma = binary 0.6 / 0.4 behavior

CR-QGeo:
    reward = geographic progress - congestion penalty
    gamma = continuous mobility-stability mapping
```

Do not claim CR-QGeo is working merely because the simulation does not crash.

Verify that the new values are actually used.

---

# 25. Mandatory Guardrails

## 25.1 Do not modify baseline QGeo

Do not edit:

```text
routing/qgeo/qgeo.py
routing/qgeo/qgeo_table.py
routing/qgeo/qgeo_packet.py
```

QGeo is a baseline.

## 25.2 Do not modify previously implemented MC-Greedy

If the local repository contains:

```text
routing/mc_greedy/
```

do not edit or delete it.

Do not reuse MC-Greedy files as CR-QGeo internals.

## 25.3 Do not modify unrelated modules

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
routing/base/
simulator/metrics.py
entities/packet.py
```

CR-QGeo is a routing-layer experiment.

## 25.4 Do not change MAC/PHY

Do not change:

```text
CSMA/CA
ALOHA
ACK timing
ACK timeout
retransmission limits
channel assignment
SINR
path loss
transmit power
bit rate
collision model
```

## 25.5 Do not change mobility

Do not change:

```text
Gauss-Markov equations
position update interval
direction update interval
boundary handling
velocity generation
```

CR-QGeo only consumes existing mobility information.

## 25.6 Do not change queue semantics

Do not change:

```text
MAX_QUEUE_SIZE
queue.Queue implementation
packet enqueue/dequeue behavior
queue-full drop behavior
blocking behavior
waiting-list behavior
```

Only observe queue occupancy.

## 25.7 Do not change existing metrics

Do not modify how the simulator computes:

```text
PDR
E2E delay
throughput
routing load
hop count
collision count
MAC delay
```

## 25.8 Do not introduce deep learning or new RL frameworks

Do not add:

```text
PyTorch
TensorFlow
DQN
PPO
MAPPO
neural networks
replay buffers
training scripts
external RL frameworks
```

CR-QGeo uses the existing tabular Q-learning mechanism.

## 25.9 Do not directly change action selection using congestion

Do not implement:

```text
adjusted_score = Q - congestion
```

or another new next-hop heuristic.

Congestion belongs in reward feedback for Version 1.

## 25.10 Do not redesign exploration

Keep existing QGeo exploration/exploitation unchanged.

## 25.11 Do not redesign ACKs beyond protocol isolation

Create CR-QGeo packet classes, but preserve ACK meaning and timing.

Do not add extra ACK rounds.

Do not create new control-message types.

## 25.12 Do not change Hello interval or packet size

Use existing QGeo scheduling.

For Version 1, keep the same simulated Hello packet length.

## 25.13 Avoid broad refactoring

Do not:

```text
rewrite Drone
rewrite BaseTable
move shared modules
rename unrelated classes
format the whole repository
change unrelated imports
clean up unrelated code
```

Make the smallest isolated implementation.

## 25.14 Preserve existing local work

The local repository may contain changes that are not yet on the remote repository.

Do not reset, checkout over, delete, or overwrite those changes.

Before editing:

```text
inspect git status
inspect relevant diffs
```

If an allowed file already contains prior modifications, merge CR-QGeo support into the current version instead of replacing the file with an older remote copy.

## 25.15 Unexpected dependency rule

If CR-QGeo appears to require changing a file outside the explicitly allowed scope:

1. Stop.
2. Explain the conflict.
3. Identify the smallest required deviation.
4. Do not modify the additional file without approval.

---

# 26. Non-Goals

The following are out of scope:

```text
MC-Greedy redesign
GMDC clustering
hierarchical routing
MAPPO
DQN
deep Q-learning
GNNs
belief graphs
digital twins
energy-aware reward
adaptive transmit power
bandwidth allocation
channel optimization
trajectory optimization
perimeter routing
multipath routing
opportunistic routing
failure injection
security attacks
new mobility models
queue scheduling redesign
new MAC protocols
```

Do not implement these.

---

# 27. Acceptance Criteria

The task is complete only when all conditions below are satisfied.

- [ ] Baseline `routing/qgeo/` files remain unchanged.
- [ ] Existing MC-Greedy files, if present, remain unchanged.
- [ ] `routing/cr_qgeo/` exists.
- [ ] `CRQGeo` uses the existing tabular Q-learning structure.
- [ ] Q-table indexing/shape remains equivalent to QGeo.
- [ ] Exploration/exploitation remains equivalent to QGeo.
- [ ] Destination reward remains `r_max`.
- [ ] Void-area behavior remains equivalent to QGeo.
- [ ] No-ACK penalty remains equivalent to QGeo.
- [ ] Queue-full behavior remains equivalent to QGeo.
- [ ] Intermediate reward includes congestion penalty.
- [ ] Congestion is sampled before enqueuing the newly received packet.
- [ ] Congestion ratio is safely clamped to `[0,1]`.
- [ ] Default congestion weight is `0.40`.
- [ ] Existing future-position prediction is reused.
- [ ] Binary gamma is replaced with continuous stability-based gamma.
- [ ] Default gamma range is `[0.30, 0.90]`.
- [ ] `next_hop_selection()` interface is preserved.
- [ ] Routing selector supports `cr_qgeo`.
- [ ] Routing selector still supports all previously configured protocols.
- [ ] CR-QGeo smoke test completes.
- [ ] QGeo baseline regression test completes.
- [ ] Existing metrics still print normally.
- [ ] No unrelated modules were modified.

---

# 28. Suggested Experimental Comparison

After implementation correctness is established, compare:

```text
QGeo
vs
CR-QGeo
```

using identical:

```text
random seed
number of UAVs
simulation time
traffic rate
mobility settings
MAC/PHY settings
```

Useful metrics:

```text
PDR
E2E delay
throughput
hop count
routing load
MAC delay
```

Recommended stress dimensions:

```text
increasing packet generation rate
increasing UAV speed
increasing UAV count
```

Do not tune CR-QGeo using a different environment than QGeo.

---

# 29. Recommended Ablation After Main Comparison

Only after the main implementation works, optional ablation can compare:

```text
QGeo
    original reward
    original binary gamma

QGeo + Congestion
    congestion-aware reward
    original binary gamma

QGeo + Continuous Reliability
    original geographic reward
    continuous gamma

CR-QGeo
    congestion-aware reward
    continuous gamma
```

This helps determine whether gains/losses come from:

```text
congestion feedback
mobility-reliability feedback
or their combination
```

Do not implement this ablation as separate permanent protocols unless requested.

Configuration flags or temporary experimental branches are acceptable later.

---

# 30. Expected Interpretation

CR-QGeo should not be assumed to outperform QGeo.

The hypothesis is:

```text
A next hop that creates strong geographic progress may still be undesirable if:
    its queue is heavily loaded
    or
    the sender-next-hop link is predicted to become unreliable.
```

CR-QGeo attempts to make these properties affect learned long-term Q-values.

If CR-QGeo performs worse, preserve the result and diagnose it rather than changing unrelated simulator behavior to force an improvement.

Possible reasons for poor performance may include:

```text
congestion penalty too strong
queues rarely congest
continuous gamma range too aggressive
simulation too short for Q-values to learn
exploration dominates early behavior
network topology changes faster than learning adapts
```

Do not silently tune parameters until results look better.

Record any parameter changes explicitly.

---

# 31. Final Protocol Summary

```text
                  CR-QGeo
                     |
                     v
            Existing QGeo action
             selection by Q-value
                     |
                     v
              Send DataPacket
                     |
                     v
          Next-hop receives packet
                     |
          +----------+----------+
          |                     |
          v                     v
 Geographic progress      Queue congestion
          |                     |
          +----------+----------+
                     |
                     v
       Reward = Progress - 0.40*C
                     |
                     v
                ACK returns
                     |
                     v
        Predict future link distance
                     |
                     v
       Stability = clip(1-d/Rmax)
                     |
                     v
       gamma = 0.30 + 0.60*Stability
                     |
                     v
            Existing Q update
                     |
                     v
          Future Q-based routing
```

CR-QGeo is therefore:

```text
Existing QGeo
+
congestion-aware reward
+
continuous mobility-reliability discount
```

Nothing more should be added in Version 1.
