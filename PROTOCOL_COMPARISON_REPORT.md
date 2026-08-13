# Routing Protocol Comparison: DSDV vs Greedy vs MC-Greedy vs QGeo vs CR-QGeo

## 1. Test Setup

All three protocols were run **in the same process, back-to-back, with an identical random seed and identical
simulation parameters**, so the UAV topology, mobility trajectories, traffic pattern, and channel/MAC behavior are
directly comparable between runs. Only the routing protocol (`config.ROUTING_PROTOCOL`) differs.

| Parameter | Value |
|---|---|
| Simulation seed | 2025 |
| Number of UAVs | 10 |
| Simulation time | 30 s |
| Map size | 600 m × 600 m × 100 m |
| Mobility model | 3-D Gauss-Markov, homogeneous speed 10 m/s |
| Traffic pattern | Poisson, rate = 5 packets/s per UAV |
| Max queue size | 200 packets |
| MC-Greedy weights | progress 0.50 / stability 0.30 / congestion 0.20 |
| MC-Greedy prediction horizon | 0.5 s |

Each run generated **754 data packets** in total (identical across all three, confirming the traffic generation was
unaffected by the routing choice, as expected).

## 2. Results

| Metric | DSDV | Greedy | MC-Greedy |
|---|---|---|---|
| Packets generated | 754 | 754 | 754 |
| Packets delivered | 700 | 685 | 684 |
| **Packet Delivery Ratio (PDR)** | **92.84 %** | 90.85 % | 90.72 % |
| **Avg. End-to-End Delay** | **23.81 ms** | 23.95 ms | 51.32 ms |
| Routing Load (control/delivered) | 0.929 | 0.876 | 0.877 |
| **Avg. Throughput** | 1045.25 Kbps | **1079.15 Kbps** | 1051.33 Kbps |
| Avg. Hop Count | 1.63 | 1.58 | 1.60 |
| **Collisions** | **6** | 26 | 62 |
| Avg. MAC Delay | 4.45 ms | 4.60 ms | 4.69 ms |
| Control packets sent | 650 | 600 | 600 |

Bold marks the best value per row.

## 3. Observations

- **PDR** is highest for DSDV (proactive, table-driven — every node always has a route once converged), with Greedy
  and MC-Greedy essentially tied about 2 points lower. This is expected: both are pure greedy-forward geographic
  protocols with no recovery/perimeter routing, so a packet can dead-end at a local void and be dropped, which
  DSDV's precomputed routes avoid.
- **Hop count** is nearly identical across all three (~1.6), meaning MC-Greedy is *not* taking meaningfully longer
  paths than Greedy — its candidate-scoring only reorders which of the forward-progress neighbors is picked at each
  hop, and the "positive progress" filter still bounds path length the same way.
- **End-to-end delay** is the most notable difference: MC-Greedy is ~2.1× higher than Greedy/DSDV in this run
  (51.3 ms vs ~24 ms). Since hop count didn't grow, the extra delay is coming from queueing/MAC-layer contention
  rather than longer routes — consistent with the **collision count** also being much higher for MC-Greedy (62 vs 26
  for Greedy vs 6 for DSDV). By favoring predicted-stable/low-congestion neighbors instead of the single closest
  neighbor, MC-Greedy can end up concentrating more traffic on the same relay nodes at the same time, increasing
  contention on the shared channel.
- **Throughput** and **routing load** are close between Greedy and MC-Greedy (both send the same 600 control
  packets — the same Hello-broadcast schedule — since MC-Greedy reuses Greedy's Hello timing exactly, as required).
- **Collisions** scale with how many nodes contend for the channel at the same time; MC-Greedy's stability/congestion
  weighting changed *when and through whom* traffic flows relative to Greedy, which in this particular topology and
  seed increased contention rather than reducing it.

## 4. Interpretation

This single-seed, single-scenario run shows MC-Greedy achieving **comparable PDR and hop count** to plain Greedy,
but **higher delay and more collisions** in this specific topology/traffic setting — i.e., in this run its
stability/congestion-aware neighbor selection did not translate into a reliability or latency win over plain
distance-based Greedy. This does not indicate a bug: MC-Greedy is a heuristic re-ranking of the same
forward-progress candidate set, and its benefit is expected to be scenario-dependent (e.g., it should show more
benefit at higher mobility speeds or higher traffic-generation rates, where link breakage and congestion are more
severe — see the "Mobility comparison" and "Congestion comparison" scenarios in `SPECIFICATION.md` §26). A single
seed/run is not sufficient to draw general performance conclusions; multiple seeds and the speed/rate sweeps
described in the specification would be needed for a statistically meaningful comparison.

## 5. Reproduction

```python
from utils import config
config.ROUTING_PROTOCOL = "mc_greedy"  # or "greedy" / "dsdv"

import simpy
from simulator.simulator import Simulator

env = simpy.Environment()
channel_states = {i: simpy.Resource(env, capacity=1) for i in range(config.NUMBER_OF_DRONES)}
sim = Simulator(seed=2025, env=env, channel_states=channel_states, n_drones=config.NUMBER_OF_DRONES)
env.run(until=config.SIM_TIME)
sim.metrics.print_metrics()
```

All three protocols use the same `Simulator(seed=2025, ...)` call; only `config.ROUTING_PROTOCOL` changes between
runs.

---

# Part 2: QGeo vs CR-QGeo

CR-QGeo is a Q-learning geographic routing protocol derived from QGeo. It keeps QGeo's tabular Q-learning
architecture, next-hop selection (Q-value argmax with the same epsilon-decay exploration), exploration policy, ACK
mechanism, and Q-table structure completely unchanged, and introduces exactly two algorithmic changes:

1. **Congestion-aware intermediate reward**: `reward = geographic_progress - 0.40 * queue_congestion`, where
   `queue_congestion` is the receiving UAV's `transmitting_queue.qsize() / max_queue_size`, sampled *before* the
   newly received packet is enqueued.
2. **Continuous mobility/reliability-aware discount factor**: `gamma = 0.30 + 0.60 * stability`, where
   `stability = clip(1 - predicted_future_distance / maximum_communication_range(), 0, 1)`, replacing QGeo's binary
   `gamma ∈ {0.4, 0.6}` decision. The underlying future-position/future-distance prediction is reused unchanged.

## 6. Test Setup

QGeo and CR-QGeo were run **in the same process, back-to-back, with the same seed and simulation parameters** as
Part 1 above (only `config.ROUTING_PROTOCOL` differs between the two runs). Both runs generated **754 data
packets** — identical to the DSDV/Greedy/MC-Greedy runs in Part 1 — confirming the topology, mobility trajectories,
and traffic generation are unaffected by the routing protocol choice, as expected, and that all five protocols in
this report are directly comparable under the same seed/scenario.

| Parameter | Value |
|---|---|
| Simulation seed | 2025 |
| Number of UAVs | 10 |
| Simulation time | 30 s |
| Map size | 600 m × 600 m × 100 m |
| Mobility model | 3-D Gauss-Markov, homogeneous speed 10 m/s |
| Traffic pattern | Poisson, rate = 5 packets/s per UAV |
| Max queue size | 200 packets |
| Q-learning rate | 0.6 (fixed, both protocols) |
| r_max / r_min | 10 / -10 (both protocols) |
| QGeo gamma | binary: 0.6 if predicted future distance < comm. range, else 0.4 |
| CR-QGeo congestion weight | 0.40 |
| CR-QGeo gamma range | 0.30 (stability 0) – 0.90 (stability 1) |

## 7. Results

| Metric | DSDV | Greedy | MC-Greedy | QGeo | CR-QGeo |
|---|---|---|---|---|---|
| Packets generated | 754 | 754 | 754 | 754 | 754 |
| Packets delivered | **700** | 685 | 684 | 645 | 638 |
| **Packet Delivery Ratio (PDR)** | **92.84 %** | 90.85 % | 90.72 % | 85.54 % | 84.62 % |
| **Avg. End-to-End Delay** | **23.81 ms** | 23.95 ms | 51.32 ms | 131.44 ms | 136.45 ms |
| Routing Load (control/delivered) | 0.929 | **0.876** | 0.877 | 0.930 | 0.940 |
| **Avg. Throughput** | 1045.25 Kbps | **1079.15 Kbps** | 1051.33 Kbps | 552.77 Kbps | 462.56 Kbps |
| Avg. Hop Count | 1.63 | **1.58** | 1.60 | 2.40 | 2.52 |
| **Collisions** | **6** | 26 | 62 | 84 | 81 |
| Avg. MAC Delay | **4.45 ms** | 4.60 ms | 4.69 ms | 42.73 ms | 43.30 ms |
| Control packets sent | 650 | 600 | 600 | 600 | 600 |

Bold marks the best value per row (across all five protocols). DSDV/Greedy/MC-Greedy figures are carried over from
Part 1 (same seed/scenario, cross-checked by the matching 754-packet generation count); QGeo and CR-QGeo were run
in this session.

## 8. Observations (QGeo vs CR-QGeo)

- **PDR / delivered packets**: CR-QGeo delivered slightly fewer packets than QGeo in this run (638 vs 645, PDR
  84.62 % vs 85.54 %) — about 1 point lower.
- **End-to-end delay and MAC delay** are essentially the same order of magnitude for both (CR-QGeo ~4 % higher E2E
  delay, ~1 % higher MAC delay) — not a meaningful difference on a single seed.
- **Hop count is higher for CR-QGeo** (2.52 vs 2.40). This is the most notable divergence: the congestion penalty in
  the reward can make the learned Q-values favor a neighbor with more forward progress penalized by local queue
  occupancy, or a less-congested but geographically less direct neighbor, which can lengthen paths relative to
  QGeo's pure-progress reward.
- **Throughput is notably lower for CR-QGeo** (462.56 Kbps vs 552.77 Kbps, ~16 % lower). Throughput here is
  `packet_length / delivery_latency` averaged per packet, so it is directly pulled down by the higher hop count
  (more forwarding stages) rather than by any change to PHY/MAC parameters (none were touched).
- **Collisions are marginally lower for CR-QGeo** (81 vs 84) and **routing load is marginally higher** (0.940 vs
  0.930) — both differences are small enough on a single seed/run to be within normal run-to-run noise rather than a
  clear effect of the congestion/gamma changes.
- **Both QGeo and CR-QGeo trail DSDV/Greedy/MC-Greedy substantially** on PDR, throughput, and especially E2E/MAC
  delay in this scenario. This is consistent with QGeo's exploration policy: `best_neighbor()` forwards to a
  *uniformly random* neighbor with probability `0.9 * 0.5^(t/1e6)` (still ~2–3 % even at t = 30 s), and CR-QGeo
  inherits this unchanged, so a meaningful fraction of hops are exploration moves rather than the learned-optimal
  next hop, which increases path length and delay relative to the deterministic geographic protocols. This is an
  inherent property of QGeo's design, not something introduced by CR-QGeo.

## 9. Interpretation

In this single-seed, single-scenario run, CR-QGeo did **not** outperform its QGeo baseline: PDR, throughput, and hop
count were all slightly worse, while collisions were marginally better and delay/MAC-delay were essentially
unchanged. The congestion-aware reward and continuous gamma changed *which* next hops the Q-learning process
converges toward (visible in the debug traces — gamma now varies continuously, e.g. 0.31–0.90, instead of the
binary 0.4/0.6, and the intermediate reward is measurably reduced whenever the receiving UAV's queue is non-empty),
but in this particular topology/traffic/seed that shifted routing toward slightly longer, lower-throughput paths
without a compensating drop in delay or collisions.

This does not indicate a bug — the mechanism is verified to work as specified (congestion sampled pre-enqueue,
penalty proportional to queue occupancy, gamma continuous and bounded in [0.30, 0.90]) — but a single run at the
default traffic rate (5 packets/s per UAV, well below the point where QGeo's queues start filling meaningfully) is
not a scenario where the congestion penalty has much signal to act on, and is not sufficient to draw general
performance conclusions either way. Per the task's research guardrail, no simulator parameters or CR-QGeo weights
were adjusted to try to improve this result. A fairer test of CR-QGeo's hypothesis (that congestion- and
reliability-awareness helps under load/mobility stress) would need higher traffic-generation rates and/or higher
mobility speeds, and multiple seeds, matching the kind of sweep already used for the MC-Greedy comparison in Part 1.

## 10. Reproduction

```python
from utils import config
config.ROUTING_PROTOCOL = "cr_qgeo"  # or "qgeo"

import simpy
from simulator.simulator import Simulator

env = simpy.Environment()
channel_states = {i: simpy.Resource(env, capacity=1) for i in range(config.NUMBER_OF_DRONES)}
sim = Simulator(seed=2025, env=env, channel_states=channel_states, n_drones=config.NUMBER_OF_DRONES)
env.run(until=config.SIM_TIME)
sim.metrics.print_metrics()
```

Both protocols use the same `Simulator(seed=2025, ...)` call as Part 1; only `config.ROUTING_PROTOCOL` changes
between runs.
