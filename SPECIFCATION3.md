# SPECIFCATION3.md

# MACG — GMDC-Inspired Mobility-Aware Clustered Greedy Routing

## 1. Purpose

This specification defines a new routing protocol for the UavNetSimTest codebase:

**MACG — Mobility-Aware Clustered Greedy Routing**

MACG is **inspired by the clustering concepts of GMDC**, but it is **not a full implementation of GMDC**.

The protocol combines:

1. Mobility-aware clustering.
2. Cluster Heads (CHs).
3. Gateways (GWs) for inter-cluster connectivity.
4. Dynamic cluster maintenance.
5. Simple deterministic Greedy forwarding.

The research hypothesis is:

> A large UAV swarm may benefit more from hierarchical mobility-aware organization than from making every individual next-hop decision increasingly complicated.

The forwarding layer therefore stays Greedy. Mobility is used primarily to organize the swarm into stable clusters.

---

## 2. Design Position

MACG is:

```text
GMDC-inspired mobility-aware clustering
+
Greedy forwarding
```

MACG is **not**:

```text
full GMDC
MC-Greedy with another weighted score
QGeo / reinforcement learning
```

Do not describe MACG as the original GMDC protocol.

---

## 3. What MACG Borrows from GMDC

MACG deliberately adopts the following ideas:

### 3.1 Mobility similarity

Nodes are grouped using both:

```text
spatial proximity
+
velocity similarity
```

### 3.2 Nomination-based CH formation

Each node nominates the neighboring node with the highest mobility similarity. Nodes receiving enough nominations become CH candidates.

For Version 1, a successful candidate becomes the final CH.

### 3.3 Cluster association

Non-CH nodes join the visible CH with the highest mobility similarity.

### 3.4 Gateway concept

A member with a one-hop neighbor belonging to a different cluster becomes a gateway candidate.

### 3.5 Bidirectional maintenance

CHs periodically announce their presence. Members respond. Missing responses cause membership cleanup or re-association.

---

## 4. GMDC Features Intentionally Excluded

Do **not** implement the following in MACG Version 1:

```text
mixed-strategy game theory
Nash-equilibrium calculation
payoff matrices
full GMDC CH/GW game election
TDMA slot scheduling
separate intra/inter-cluster frequency bands
CH data aggregation
GS-specific routing
full GMDC cluster-merging algorithm
round-based energy-balancing CH rotation
full network-lifetime optimization
```

The purpose of this protocol is to isolate:

```text
mobility-aware hierarchy
+
Greedy forwarding
```

---

## 5. Motivation

Previous behavior suggests the following architectural tradeoff:

```text
DSDV
  global routing state
  strong in small networks
  increasingly expensive/stale as scale and mobility rise

Q-learning routing
  requires exploration and learning
  topology may change while Q-values are converging

Greedy
  local information
  no convergence
  no learning
  low forwarding complexity
  strong scalability
```

Greedy still treats the entire swarm as one flat network. MACG adds structure:

```text
                    UAV swarm
                       |
             mobility clustering
                       |
       +---------------+---------------+
       |               |               |
    Cluster A       Cluster B       Cluster C
       |               |               |
      CH-A            CH-B            CH-C
     / | \            / | \           / | \
 members            members         members
       |               |               |
      GW-A ---------- GW-B ---------- GW-C
```

The idea is not to make Greedy more intelligent. The idea is to make the topology it operates on better organized.

---

## 6. Protocol and Package Names

Protocol display name:

```text
MACG
```

Expanded name:

```text
Mobility-Aware Clustered Greedy Routing
```

Research description:

```text
GMDC-inspired clustered Greedy routing
```

Routing selector key:

```text
"macg"
```

Recommended package:

```text
routing/macg/
├── __init__.py
├── macg.py
├── macg_neighbor_table.py
├── macg_cluster_manager.py
└── macg_packet.py
```

---

## 7. Module Responsibilities

### 7.1 `macg.py`

Main routing protocol.

Responsibilities:

```text
DataPacket next-hop selection
DataPacket reception
normal data ACK behavior
waiting-list behavior
hierarchical forwarding stages
interaction with ClusterManager
Greedy forwarding to arbitrary targets
flat-Greedy fallback
```

Use the existing Greedy protocol as the behavioral reference for ordinary packet forwarding, ACKs, and waiting-list handling.

Do not modify the original Greedy implementation.

### 7.2 `macg_neighbor_table.py`

Stores state learned from MACG Hello/control packets.

Responsibilities:

```text
neighbor position
neighbor velocity
neighbor residual energy
neighbor role
neighbor cluster ID
neighbor CH ID
neighbor epoch
last update time
mobility similarity
stale-entry purge
Greedy candidate selection
cross-cluster neighbor discovery
```

Follow the existing `BaseTable` model where appropriate.

### 7.3 `macg_cluster_manager.py`

Owns clustering state and clustering control logic.

Responsibilities:

```text
role
cluster ID
CH ID
cluster epoch
nomination state
CH election
cluster joining
member table
gateway discovery
gateway table
maintenance
member timeout
CH timeout
re-association
cluster diagnostics
```

Data-plane next-hop logic should not contain the entire cluster state machine.

### 7.4 `macg_packet.py`

Defines MACG control packets.

At minimum provide:

```text
MACGHelloPacket
MACGControlPacket
```

`MACGControlPacket` may use a `message_type` string and a compact payload.

Recommended message types:

```text
NOMINATION
CH_DECLARE
JOIN_REQUEST
JOIN_ACCEPT
CLUSTER_STATE
MAINTENANCE
MAINT_RESPONSE
GATEWAY_UPDATE
```

Explicit packet subclasses are also acceptable if they match repository style better.

Do not modify the base Packet class solely for MACG.

---

## 8. Node Roles

Use:

```text
ROLE_UNCLUSTERED = 0
ROLE_CH          = 1
ROLE_GW          = 2
ROLE_CM          = 3
```

Interpretation:

```text
0 = no valid cluster association
1 = Cluster Head
2 = cluster member with inter-cluster gateway connectivity
3 = ordinary Cluster Member
```

Each node tracks:

```text
role
cluster_id
cluster_head_id
cluster_epoch
```

Use:

```text
cluster_id = CH node ID
```

This avoids a global cluster-ID allocator.

---

## 9. Hello Information

Every MACG Hello packet must advertise a snapshot of:

```text
node ID
position
velocity
residual energy
role
cluster_id
cluster_head_id
cluster_epoch
timestamp
```

Copy mutable vectors when creating the packet:

```python
position = list(src_drone.coords)
velocity = list(src_drone.velocity)
```

Do not store a live mutable reference that changes after transmission.

Cluster decisions must be based on local state plus received control information.

Do not inspect another UAV's live cluster-manager state directly.

The same destination-position assumption already used by geographic routing may be preserved.

---

## 10. Neighbor Table

Recommended conceptual entry:

```text
neighbor_id -> [
    position,
    velocity,
    residual_energy,
    role,
    cluster_id,
    cluster_head_id,
    cluster_epoch,
    mobility_similarity,
    update_time
]
```

If `BaseTable.get_updated_time()` uses the last item, `update_time` MUST remain the final field.

Purge stale entries using existing infrastructure.

---

## 11. Mobility Similarity

For neighboring UAVs `i` and `j`:

```text
S_ij = w_position * S_position
       + w_velocity * S_velocity
```

Default weights:

```text
w_position = 0.40
w_velocity = 0.60
```

The weights must sum to 1.

### 11.1 Position similarity

```text
S_position = 1 - ||P_i - P_j|| / R
```

where `R` is the communication-range normalization.

Use the repository's existing:

```python
maximum_communication_range()
```

Clamp:

```text
0 <= S_position <= 1
```

### 11.2 Velocity similarity

```text
S_velocity = 1 - ||V_i - V_j|| / V_diff_max
```

Clamp:

```text
0 <= S_velocity <= 1
```

`V_diff_max` must be a configured normalization value.

Do not scan every UAV's live velocity each time to find a global maximum.

Prefer a constant derived once from the configured speed range. If that is not cleanly available, expose an explicit config value.

### 11.3 Final default formula

```text
S_ij =
    0.40 * clip(1 - distance(i,j)/R, 0, 1)
    +
    0.60 * clip(1 - ||V_i-V_j||/V_diff_max, 0, 1)
```

Clamp final `S_ij` to `[0,1]`.

A high value means the nodes are both geographically close and moving similarly.

---

## 12. Default Timing

Expose these as configuration values.

Recommended Version 1 defaults:

```text
MACG_HELLO_INTERVAL         = 0.5 s
MACG_BOOTSTRAP_DELAY        = 1.0 s
MACG_NOMINATION_WINDOW      = 0.25 s
MACG_CH_DECLARATION_WINDOW  = 0.25 s
MACG_JOIN_WINDOW            = 0.50 s
MACG_MAINTENANCE_INTERVAL   = 1.0 s
MACG_MEMBER_MISS_LIMIT      = 2
MACG_CH_MISS_LIMIT          = 2
MACG_NOMINATION_THRESHOLD   = 2
```

Use repository microsecond conventions where required.

Do not silently tune these after seeing results.

---

## 13. Cluster Formation State Machine

The cluster manager should perform:

```text
BOOTSTRAP
   |
   v
NEIGHBOR DISCOVERY
   |
   v
NOMINATION
   |
   v
CH DECLARATION
   |
   v
JOIN
   |
   v
ACTIVE CLUSTER
   |
   v
MAINTENANCE / RE-ASSOCIATION
```

---

## 14. Bootstrap and Neighbor Discovery

At startup:

1. Start periodic MACG Hello broadcasts.
2. Wait `MACG_BOOTSTRAP_DELAY`.
3. Purge stale neighbors.
4. Ensure mobility similarity is available for every current neighbor.

A node with no neighbors must remain functional and later use the isolated-node fallback.

---

## 15. Nomination Phase

Each unclustered node:

1. Finds the neighbor with the highest mobility similarity.
2. Sends exactly one `NOMINATION` for the current epoch.
3. Tie breakers:
   - higher residual energy,
   - then lower node ID.
4. If no neighbors exist, send no nomination.

Each node maintains:

```text
nomination_count
nominators
```

Ignore duplicate nominations from the same sender.

Ignore messages belonging to an old epoch.

---

## 16. CH Declaration

After the nomination window:

If:

```text
nomination_count >= MACG_NOMINATION_THRESHOLD
```

the node becomes CH:

```text
role = ROLE_CH
cluster_id = own ID
cluster_head_id = own ID
```

Broadcast `CH_DECLARE` containing:

```text
CH ID
position
velocity
residual energy
cluster epoch
```

For Version 1, this node is the final CH.

Do not run a GMDC game-theory election afterward.

---

## 17. CH Fallback Election

The protocol must prevent permanent orphaning.

After the CH declaration window, if a node heard no valid CH declaration:

### Case A: neighbors exist

Use deterministic local fallback priority:

```text
higher nomination count
then higher residual energy
then lower node ID
```

A node self-elects only if it is the strongest locally visible candidate by this rule.

### Case B: no neighbors

Become a singleton CH:

```text
role = ROLE_CH
cluster_id = own ID
cluster_head_id = own ID
```

It may later accept members.

---

## 18. Joining a Cluster

A non-CH node collects current-epoch CH declarations.

For each visible CH, calculate mobility similarity.

Choose:

```text
highest mobility similarity
```

Tie breakers:

```text
higher CH residual energy
then lower CH ID
```

Send `JOIN_REQUEST` including:

```text
member ID
position
velocity
residual energy
cluster epoch
```

---

## 19. CH Join Processing

On valid `JOIN_REQUEST`, the CH:

1. Adds the member to `member_table`.
2. Sends `JOIN_ACCEPT` with:
   - cluster ID,
   - CH ID,
   - cluster epoch.
3. May include a compact member-ID list in `CLUSTER_STATE`.

Do not create a global cluster directory.

---

## 20. Member Join Completion

On `JOIN_ACCEPT`:

```text
role = ROLE_CM
cluster_id = received cluster ID
cluster_head_id = received CH ID
cluster_epoch = received epoch
```

If the request times out:

1. Try the next-best visible CH.
2. If no CH is joinable, apply CH fallback election.

---

## 21. CH Member Table

Each CH maintains at least:

```text
member_id
last_response_time
position
velocity
residual_energy
reported_external_links
```

The CH itself counts as a member of its cluster logically.

The CH must know member IDs so it can recognize whether a DataPacket destination belongs to the current cluster.

---

## 22. Gateway Definition

A gateway candidate is a clustered node that has at least one valid one-hop neighbor in another cluster:

```text
neighbor.cluster_id is valid
AND
neighbor.cluster_id != own cluster_id
```

Do not treat an unclustered neighbor as a valid destination cluster.

A member with cross-cluster connectivity becomes:

```text
ROLE_GW
```

A CH may have direct cross-cluster neighbors without changing `ROLE_CH`.

---

## 23. Gateway Discovery

Each clustered member periodically derives:

```text
external_neighbor_table
```

grouped by neighboring cluster ID.

For every cross-cluster neighbor keep:

```text
neighbor ID
position
velocity
mobility similarity
residual energy
neighbor cluster ID
```

Members report this information through maintenance responses or `GATEWAY_UPDATE`.

Avoid creating a separate high-frequency gateway loop if maintenance already provides the needed data.

---

## 24. CH Gateway Table

Each CH maintains conceptually:

```text
neighbor_cluster_id -> {
    local_gateway_id,
    external_neighbor_id,
    external_neighbor_position,
    cross_link_count,
    cross_link_similarity,
    gateway_energy,
    last_update_time
}
```

MACG Version 1 may use different gateways for different neighboring clusters.

This is a practical adaptation, not an exact reproduction of full GMDC.

---

## 25. Gateway Selection Rule

For each neighboring cluster select the gateway by:

1. Highest number of valid links to that neighboring cluster.
2. If tied, highest mobility similarity of the best cross-cluster link.
3. If tied, highest residual energy.
4. If tied, lower node ID.

No game theory is used.

---

## 26. Cluster Maintenance

Every CH broadcasts `MAINTENANCE` every `MACG_MAINTENANCE_INTERVAL`.

The message includes:

```text
CH ID
cluster ID
cluster epoch
timestamp
```

A CM/GW receiving maintenance from its own CH:

1. Resets its CH-miss counter.
2. Sends `MAINT_RESPONSE`.
3. Includes:
   - member ID,
   - position,
   - velocity,
   - residual energy,
   - external-link/gateway summary.

---

## 27. Member Timeout at CH

If a member misses:

```text
MACG_MEMBER_MISS_LIMIT
```

consecutive maintenance responses, the CH:

```text
removes the member
removes/refreshes gateway entries depending on it
```

Default miss limit:

```text
2
```

---

## 28. CH Timeout at Member

If a CM/GW fails to receive maintenance from its CH for:

```text
MACG_CH_MISS_LIMIT
```

consecutive intervals:

```text
role = ROLE_UNCLUSTERED
cluster_id = None
cluster_head_id = None
```

Then immediately start re-association.

Default miss limit:

```text
2
```

---

## 29. Re-Association

An unclustered node searches current neighbor information for visible CHs.

Select the CH with the highest mobility similarity and run the same join process.

If no CH is available, use local CH fallback election.

Version 1 should prefer:

```text
initial clustering
+
continuous local maintenance
+
local re-association
```

Do not periodically destroy every cluster unless later experiments specifically require it.

---

## 30. Greedy Forwarding Foundation

All DataPacket forwarding remains deterministic and Greedy-based.

Implement a reusable helper conceptually like:

```python
select_greedy_neighbor(
    target_position,
    allowed_cluster_id=None,
    allowed_ids=None,
    excluded_ids=None,
)
```

The helper:

1. Computes current distance to the target.
2. Iterates valid neighbors.
3. Applies optional restrictions.
4. Keeps only neighbors closer to the target than the current UAV.
5. Selects the candidate with minimum distance to the target.
6. Returns own UAV ID if no positive-progress candidate exists.

Do not add mobility, congestion, or Q-values into this forwarding score.

Mobility is used for cluster organization.

---

## 31. Hierarchical Forwarding Overview

```text
Source
  |
  | Greedy inside source cluster toward CH
  v
Source CH
  |
  | select gateway toward destination
  v
Local GW
  |
  | cross-cluster one-hop
  v
Node in next cluster
  |
  | Greedy toward next CH
  v
Next CH
  |
  ...
  v
Destination cluster
  |
  | local Greedy
  v
Destination
```

---

## 32. MACG DataPacket Metadata

Avoid changing the base DataPacket class unless unavoidable.

Add attributes lazily on packet objects when first handled:

```text
macg_stage
macg_target_id
macg_selected_neighbor_cluster
macg_selected_external_neighbor
macg_last_cluster
macg_visited_clusters
```

Recommended stages:

```text
LOCAL
TO_CH
TO_GATEWAY
CROSS_CLUSTER
```

Keep `macg_visited_clusters` bounded, for example to the last 8 clusters.

The existing packet TTL/deadline remains authoritative.

---

## 33. Direct Destination Fast Path

Before applying hierarchy:

If the destination is a valid one-hop neighbor:

```text
send directly to destination
```

Do not route through a CH when direct delivery is possible.

---

## 34. Unclustered Forwarding

If:

```text
role == ROLE_UNCLUSTERED
```

use flat original-style Greedy toward the final destination.

The data plane must remain functional during startup or re-association.

---

## 35. Same-Cluster Forwarding

If the destination is known to belong to the current cluster:

```text
Greedy directly toward destination
```

Prefer same-cluster neighbors.

If no same-cluster positive-progress candidate exists:

```text
allow flat-Greedy fallback across valid neighbors
```

Do not force every intra-cluster packet through the CH.

---

## 36. Member-to-CH Forwarding

If the current node is CM/GW and the destination is not known to belong to the current cluster:

```text
route toward own CH
```

Use:

```text
target_position = CH position
allowed_cluster_id = own cluster
```

Important:

During this stage, the Greedy target is the CH, not the final destination.

---

## 37. CH Inter-Cluster Decision

When a CH handles a packet whose destination is not in its cluster:

1. Purge stale gateway entries.
2. Inspect available neighboring clusters.
3. Avoid immediately returning to `macg_last_cluster` when alternatives exist.
4. For each gateway option, calculate distance from its advertised external neighbor to the final destination.
5. Select the smallest distance.
6. Tie breakers:
   - higher cross-link mobility similarity,
   - higher gateway energy,
   - lower gateway ID.
7. Set packet metadata for the chosen gateway and external neighbor.
8. Route inside the cluster toward the gateway.

This is cluster-level geographic Greedy.

Do not introduce a weighted learned score.

---

## 38. Prevent Cluster Ping-Pong

When crossing:

```text
Cluster A -> Cluster B
```

set:

```text
macg_last_cluster = Cluster A
```

At Cluster B, do not immediately select Cluster A again if another usable option exists.

Maintain a small recent list:

```text
macg_visited_clusters
```

Recommended cap:

```text
8 cluster IDs
```

Do not allow unbounded packet metadata growth.

---

## 39. CH-to-Gateway Forwarding

After a CH selects a gateway:

```text
macg_stage = "TO_GATEWAY"
macg_target_id = gateway_id
```

Use Greedy toward the gateway's position, preferring nodes in the current cluster.

If the gateway is already a direct neighbor, send directly.

---

## 40. Gateway Cross-Cluster Transfer

At the selected gateway:

1. Validate that the selected external neighbor is still present.
2. Validate that it belongs to the expected different cluster.
3. Forward directly to that external neighbor.
4. Set:

```text
macg_last_cluster = old cluster
macg_stage = "TO_CH"
macg_target_id = None
```

The receiving node then applies normal MACG logic for its new cluster.

---

## 41. Arrival in a New Cluster

On entering a new cluster:

1. Add the cluster ID to recent visited-cluster metadata.
2. If the destination belongs to this cluster, route locally to destination.
3. Otherwise:
   - CH performs a new gateway decision,
   - CM/GW routes toward its CH.

Repeat until delivered or fallback is required.

---

## 42. Destination Cluster Detection

The CH must use its `member_table`:

```text
destination_id in member_table
```

The CH itself also belongs to its cluster.

Members may cache a member-ID list from `CLUSTER_STATE`, but that is optional.

If a normal member cannot determine whether the destination is local:

```text
route toward the CH
```

The CH decides.

Do not create a global cluster-membership oracle.

---

## 43. Required Fallbacks

MACG must fail gracefully.

### Cannot Greedy-route to CH

```text
flat Greedy toward final destination
```

### CH has no valid gateway

```text
flat Greedy toward final destination
```

### Gateway entry became stale

Recompute. If no valid gateway remains:

```text
flat Greedy toward final destination
```

### External neighbor disappeared

Recompute cross-cluster neighbor. If none exists:

```text
clear hierarchical state
flat Greedy toward final destination
```

### Cluster state is incomplete

Prefer safe flat Greedy rather than dropping the packet solely because hierarchy is unavailable.

The principle is:

```text
hierarchical when useful
Greedy-safe when hierarchy is unavailable
```

---

## 44. Data ACK and Waiting List

Reuse existing Greedy behavior for ordinary data forwarding:

```text
ACK creation
SIFS behavior
ACK handling
wait-ACK interruption
retransmission integration
queue removal
waiting-list behavior
packet deadline behavior
```

Do not create a second data reliability mechanism.

Cluster-control messages are separate from normal DataPacket ACKs.

---

## 45. Control Packet Accounting

Every actual MACG clustering message must count as routing control traffic.

Examples:

```text
Hello
Nomination
CH declaration
Join request
Join accept
Cluster state
Maintenance
Maintenance response
Gateway update
```

Increment the existing control-packet metric consistently with other routing protocols.

Do not hide hierarchy overhead.

---

## 46. Control Packet Transmission

Use existing simulator/MAC conventions for:

```text
broadcast
unicast
channel assignment
transmitting queue
```

Do not bypass the MAC layer merely to make control messages reliable.

---

## 47. Configuration

Add MACG-specific values to `utils/config.py`.

Recommended:

```python
MACG_POSITION_WEIGHT = 0.40
MACG_VELOCITY_WEIGHT = 0.60

MACG_MAX_VELOCITY_DIFFERENCE = <appropriate value>

MACG_HELLO_INTERVAL = 0.5 * 1e6
MACG_BOOTSTRAP_DELAY = 1.0 * 1e6
MACG_NOMINATION_WINDOW = 0.25 * 1e6
MACG_CH_DECLARATION_WINDOW = 0.25 * 1e6
MACG_JOIN_WINDOW = 0.50 * 1e6

MACG_NOMINATION_THRESHOLD = 2

MACG_MAINTENANCE_INTERVAL = 1.0 * 1e6
MACG_MEMBER_MISS_LIMIT = 2
MACG_CH_MISS_LIMIT = 2

MACG_VISITED_CLUSTER_LIMIT = 8
```

Do not hardcode the same value in multiple files.

---

## 48. Routing Selector

Extend the existing selector with:

```text
"macg"
```

Preserve every existing protocol option.

Original Greedy must remain available as the main baseline.

---

## 49. Files to Create

Create:

```text
routing/macg/__init__.py
routing/macg/macg.py
routing/macg/macg_neighbor_table.py
routing/macg/macg_cluster_manager.py
routing/macg/macg_packet.py
```

---

## 50. Existing Files Allowed to Modify

For normal integration, modify only:

```text
entities/drone.py
utils/config.py
```

If the repository has a dedicated routing registration file, make only the smallest necessary registration change there.

---

## 51. Do Not Modify

Do not modify existing baselines or unrelated modules:

```text
routing/greedy/
routing/mc_greedy/
routing/qgeo/
routing/cr_qgeo/
routing/dsdv/
routing/base/
mac/
phy/
mobility/
energy/
topology/
allocation/
path_planning/
visualization/
simulator/metrics.py
entities/packet.py
```

If implementation appears to require changing one of these, stop and explain why before making the change.

---

## 52. No Learning

Do not add:

```text
Q-learning
DQN
PPO
MAPPO
PyTorch
TensorFlow
neural networks
replay buffers
training loops
exploration schedules
```

MACG is deterministic.

---

## 53. No MC-Greedy-Style Forwarding Score

Do not implement:

```text
distance + mobility - congestion
```

at the next-hop layer.

Mobility is already used to form and maintain clusters.

The data forwarding rule remains geographic Greedy.

---

## 54. No Full GMDC Game Theory

Do not add:

```text
payoff matrix
mixed strategies
Nash equilibrium
game solver
probabilistic CH/GW election
```

This is explicitly outside Version 1.

---

## 55. Protocol-Local Diagnostics

Do not change existing simulator metric definitions.

MACG may maintain internal diagnostics such as:

```text
active cluster count
average cluster size
maximum cluster size
CH count
GW count
unclustered count
join attempts
successful joins
re-associations
member removals
gateway changes
flat-Greedy fallback count
hierarchical inter-cluster forward count
```

Use these to explain behavior, not to replace existing metrics.

---

## 56. Example: Inter-Cluster Routing

Assume:

```text
Cluster A:
  CH = 10
  members = 3,4,5
  gateway to B = 5

Cluster B:
  CH = 20
  members = 11,12,13
```

Source:

```text
UAV 3
```

Destination:

```text
UAV 12
```

Expected mechanism:

```text
UAV 3
  |
  | Greedy target = CH 10
  v
CH 10
  |
  | choose gateway whose external neighbor
  | is geographically best toward destination
  v
GW 5
  |
  | cross-cluster one-hop
  v
node in Cluster B
  |
  | Greedy target = CH 20
  v
CH 20
  |
  | destination 12 is a local member
  v
Greedy toward UAV 12
  |
  v
UAV 12
```

---

## 57. Example: Same Cluster

If source and destination are both in Cluster A:

```text
Source -> Greedy -> ... -> Destination
```

Do not route through the CH unless fallback requires it.

---

## 58. Example: Startup / Unclustered Node

If a node has not yet formed or joined a cluster:

```text
use flat Greedy
```

Clustering must never make the data plane unusable during bootstrap.

---

# 59. Implementation Order

The AI agent must implement in this order.

## Step 1 — Inspect reference behavior

Read the current:

```text
Greedy protocol
Greedy neighbor table
Greedy packet
BaseTable
Drone routing selector
config
maximum communication range helper
```

Understand:

```text
Hello scheduling
neighbor purge
next_hop_selection interface
DataPacket reception
ACK handling
waiting list
control packet counting
broadcast/unicast conventions
```

Do not edit Greedy.

## Step 2 — Create `routing/macg/`

Create all required files and basic class skeletons.

Make imports resolve before implementing the full protocol.

## Step 3 — Implement MACG packets

Implement Hello and cluster-control packet support.

Confirm control packets can use existing MAC/queue mechanisms.

## Step 4 — Implement MACG neighbor table

Implement storage for:

```text
position
velocity
energy
role
cluster ID
CH ID
epoch
similarity
timestamp
```

Add:

```text
mobility_similarity()
flat Greedy selection
cluster-restricted Greedy selection
cross-cluster neighbor queries
```

## Step 5 — Implement ClusterManager state

Add:

```text
role
cluster_id
cluster_head_id
cluster_epoch
nomination_count
nominators
visible_CHs
member_table
gateway_table
maintenance counters
```

Do not implement inter-cluster data routing yet.

## Step 6 — Implement Hello discovery

Validate:

```text
neighbors appear
similarity is calculated
stale neighbors expire
```

## Step 7 — Implement nomination

Each node nominates its highest-similarity neighbor once per epoch.

Validate duplicate suppression.

## Step 8 — Implement CH declaration and fallback

Implement threshold-based CH declaration and orphan fallback.

Verify connected nodes eventually see a CH.

## Step 9 — Implement join

Implement:

```text
select best CH
JOIN_REQUEST
JOIN_ACCEPT
member_table
member role transition
```

## Step 10 — Implement gateway discovery

After cluster IDs propagate:

```text
detect cross-cluster neighbors
mark gateway candidates
report gateway information
construct CH gateway table
```

## Step 11 — Implement maintenance

Implement:

```text
CH maintenance broadcast
member response
member timeout
CH timeout
re-association
gateway refresh
```

## Step 12 — Implement generic Greedy helper

Validate Greedy forwarding to arbitrary targets:

```text
final destination
CH
gateway
```

Do not add new score factors.

## Step 13 — Implement direct, unclustered, and same-cluster forwarding

Validate these before inter-cluster logic.

## Step 14 — Implement member-to-CH forwarding

Use Greedy target = own CH.

## Step 15 — Implement CH gateway selection

Select the gateway whose external neighbor is geographically best toward the final destination, with defined tie breakers.

## Step 16 — Implement CH-to-GW forwarding

Use intra-cluster Greedy toward selected GW.

## Step 17 — Implement cross-cluster transfer

Gateway sends to its selected external neighbor.

## Step 18 — Implement multi-cluster traversal

Test:

```text
Cluster A -> B -> C -> destination
```

Prevent immediate A/B ping-pong.

## Step 19 — Implement all fallbacks

Test:

```text
missing CH
missing gateway
stale gateway
lost external neighbor
unclustered state
incomplete cluster state
```

Fallback must be flat Greedy.

## Step 20 — Integrate selector and config

Add `"macg"` support without removing any existing option.

## Step 21 — Static validation

Verify:

```text
imports
class names
SimPy generator behavior
packet constructors
BaseTable timestamp layout
routing interface
```

## Step 22 — Smoke test

Use a small network.

Verify:

```text
Hello works
clusters form
CHs exist
members join
gateways appear
maintenance operates
DataPackets deliver
ACKs work
metrics print
no deadlock
```

## Step 23 — Scale test

After correctness:

```text
50 UAVs
100 UAVs
150 UAVs
200 UAVs
```

Primary comparison:

```text
Greedy vs MACG
```

---

## 60. Acceptance Criteria

The implementation is complete only if:

- [ ] Original Greedy code is unchanged.
- [ ] `routing/macg/` exists.
- [ ] MACG Hello uses position and velocity snapshots.
- [ ] Mobility similarity is implemented.
- [ ] Default similarity weights are 0.40 / 0.60.
- [ ] No global live-state clustering oracle is used.
- [ ] Each node nominates its most similar neighbor.
- [ ] Nomination threshold defaults to 2.
- [ ] CH fallback prevents permanent orphaning.
- [ ] Non-CH nodes join the most similar visible CH.
- [ ] CH maintains member state.
- [ ] Cross-cluster links create gateway candidates.
- [ ] Gateway information reaches CH.
- [ ] CH maintains a gateway table.
- [ ] Maintenance uses CH broadcast + member response.
- [ ] Member timeout works.
- [ ] CH-loss re-association works.
- [ ] Direct-neighbor fast path works.
- [ ] Same-cluster Greedy works.
- [ ] CM/GW can route toward CH.
- [ ] CH can choose a gateway.
- [ ] GW can cross cluster boundary.
- [ ] Multi-cluster forwarding works.
- [ ] Immediate cluster ping-pong is reduced/prevented.
- [ ] Flat-Greedy fallbacks work.
- [ ] Existing DataPacket ACK behavior remains compatible.
- [ ] Existing simulator metrics still work.
- [ ] MACG control packets count as routing overhead.
- [ ] No RL is introduced.
- [ ] No GMDC game-theory mechanism is introduced.

---

## 61. Mandatory Guardrails

### Do not modify baselines

Do not modify:

```text
Greedy
MC-Greedy
QGeo
CR-QGeo
DSDV
```

### Do not modify MAC/PHY

Do not change:

```text
CSMA/CA
ALOHA
ACK timeout
retransmission limits
channel assignment
SINR
path loss
transmit power
bit rate
collision logic
```

### Do not modify mobility

Do not change:

```text
Gauss-Markov equations
speed generation
velocity updates
position update interval
boundary logic
```

MACG consumes mobility information. It does not control UAV movement.

### Do not hide clustering overhead

All real cluster signaling must count as control traffic.

### Do not use global clustering state

Do not loop over all simulator drones and inspect their live cluster managers for cluster decisions.

Use:

```text
local state
+
received control packets
+
neighbor table
```

### Do not add a central cluster controller

Clustering must be distributed.

### Do not add game theory

No Nash equilibrium or payoff solver.

### Do not add learning

No training or exploration.

### Do not change metrics

Use existing network metrics unchanged.

### Do not broad-refactor

Do not rewrite unrelated modules just to make MACG cleaner.

---

## 62. Experimental Comparison

Primary comparison:

```text
Greedy
vs
MACG
```

Use identical:

```text
random seed
traffic
mobility
simulation time
PHY/MAC
map size
```

Recommended swarm sizes:

```text
20
50
100
150
200
```

Recommended mobility stress:

```text
10 m/s
20 m/s
30 m/s
40 m/s
```

Use existing metrics:

```text
PDR
end-to-end delay
throughput
routing load
hop count
collisions
MAC delay
```

Useful MACG-local diagnostics:

```text
cluster count
average cluster size
cluster-size variance
gateway count
re-association count
member removal count
flat-Greedy fallback rate
inter-cluster forwarding count
```

---

## 63. Expected Interpretation

Do not assume MACG will always beat Greedy.

A useful result may be:

```text
small swarm:
    Greedy is simpler and faster

large swarm:
    MACG becomes more stable or scalable
```

If MACG performs poorly, investigate:

```text
too many clusters
too few clusters
gateway churn
maintenance overhead
re-association frequency
member-to-CH detours
CH-to-GW detours
flat-Greedy fallback frequency
cluster ping-pong
stale gateway information
similarity normalization
```

Do not alter unrelated simulator behavior to force a positive result.

---

## 64. Final Protocol Summary

```text
                 MACG
                  |
                  v
       Periodic mobility Hello
                  |
                  v
       Calculate mobility similarity
                  |
                  v
       Nominate most similar neighbor
                  |
                  v
             Elect CHs
                  |
                  v
         Members join best CH
                  |
                  v
       Detect cross-cluster links
                  |
                  v
           Build gateway map
                  |
                  v
       Maintain clusters locally
                  |
        +---------+----------+
        |                    |
        v                    v
 same-cluster          different cluster
        |                    |
        v                    v
Greedy to dest         Greedy to CH
                             |
                             v
                       CH selects GW
                             |
                             v
                       Greedy to GW
                             |
                             v
                       cross cluster
                             |
                             v
                        next cluster
```

The central idea is:

```text
Do not make Greedy smarter.

Use mobility-aware clustering to make the large swarm better organized,
then keep forwarding simple.
```

That is the complete scope of MACG Version 1.
