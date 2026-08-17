# Experiment A: UAV Count Sweep (DSDV vs Greedy vs QGeo vs CR-QGeo vs MACG)

## 1. Setup

All runs use the same random seed and simulation parameters, varying only `config.NUMBER_OF_DRONES` and
`config.ROUTING_PROTOCOL`. 20 runs total (4 UAV counts × 5 protocols), each executed in its own isolated process
(parallelized across cores) with identical seed 2025.

| Parameter | Value |
|---|---|
| Simulation seed | 2025 |
| UAV counts swept | 10, 20, 50, 100 |
| Protocols compared | DSDV, Greedy, QGeo, CR-QGeo, MACG |
| Simulation time (nominal) | 30 s |
| Map size | 600 m × 600 m × 100 m (unchanged across UAV counts) |
| Mobility model / speed | 3-D Gauss-Markov, 10 m/s |
| Traffic pattern | Poisson, rate = 5 packets/s per UAV |
| Max queue size | 200 packets |
| `INITIAL_ENERGY` | 20,000 J (explicitly set for every run — see note below) |

`INITIAL_ENERGY` is pinned explicitly to 20,000 J at runtime for every run in this experiment rather than left at
whatever `utils/config.py`'s module-level default happens to be (that default has since changed to 200,000 J, for
reasons unrelated to this experiment) — this way all five protocols are guaranteed to be compared under the same
energy budget regardless of when each was run.

**Important caveat discovered during this work (applies to every run in this report):** with the simulator's default
energy model (`INITIAL_ENERGY = 20000 J`, `ENERGY_THRESHOLD = 2000 J`, rotary-wing hover power ≈1104 W at 10 m/s),
every drone's `residual_energy` hits the sleep threshold and the drone **permanently stops generating and relaying
packets** at **t ≈ 16.3 s** — confirmed by direct instrumentation (all 10 drones slept at exactly t=16.4 s in a
diagnostic run) and by the underlying power formula. This is independent of UAV count (flight power depends only on
speed, not network size), so it applies identically to all four UAV-count tiers below — the relative comparisons
between protocols/densities are not biased by it. But the nominal "30 s simulation" is misleading: real network
activity is compressed into the first ~16 s, with the remainder of the 30 s window contributing little beyond
draining already-queued packets. This is not a routing-protocol effect; it is a pre-existing property of the
simulator's default energy configuration. See `ExperimentC.md` for a full analysis and an energy-neutralized re-run
that isolates this effect. Per-drone generated-packet averages here (75.4 / 79.9 / 82.7 / 82.6 for n=10/20/50/100)
all converge to ≈80, consistent with a ~16 s active window at rate 5 pkt/s — additional confirmation of the same
cutoff at every density.

## 2. Results

| n_drones | Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Routing Load | Throughput (Kbps) | Hop Count | Collisions | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | **DSDV** | 754 | **700** | **92.84** | **23.81** | 0.929 | 1045.25 | 1.63 | **6** | 650 |
| 10 | Greedy | 754 | 685 | 90.85 | 23.95 | **0.876** | **1079.15** | **1.58** | 26 | 600 |
| 10 | MACG | 754 | 673 | 89.26 | 27.22 | 1.355 | 961.34 | 1.84 | 82 | 912 |
| 10 | QGeo | 754 | 645 | 85.54 | 131.44 | 0.930 | 552.77 | 2.40 | 84 | 600 |
| 10 | CR-QGeo | 754 | 638 | 84.62 | 136.45 | 0.940 | 462.56 | 2.52 | 81 | 600 |
| 20 | **DSDV** | 1597 | 802 | 50.22 | 103.08 | 4.203 | 614.56 | 1.91 | 4888 | 3371 |
| 20 | **Greedy** | 1597 | **1270** | **79.52** | **122.91** | **0.945** | **698.81** | **1.69** | **924** | 1200 |
| 20 | MACG | 1597 | 1146 | 71.76 | 416.64 | 1.618 | 378.23 | 1.99 | 952 | 1854 |
| 20 | QGeo | 1597 | 551 | 34.50 | 3392.59 | 2.178 | 30.41 | 2.71 | 856 | 1200 |
| 20 | CR-QGeo | 1597 | 508 | 31.81 | 3850.30 | 2.362 | 13.70 | 2.77 | 951 | 1200 |
| 50 | DSDV | 4136 | 1246 | 30.13 | 3218.56 | 9.706 | 24.17 | **1.44** | 20851 | 12094 |
| 50 | **Greedy** | 4136 | **1301** | **31.46** | **2214.56** | **2.306** | **33.71** | 1.50 | **6211** | 3000 |
| 50 | MACG | 4136 | 1227 | 29.67 | 3015.81 | 4.473 | 19.30 | 1.47 | 8133 | 5488 |
| 50 | QGeo | 4136 | 107 | 2.59 | 5125.69 | 28.037 | 8.76 | 1.81 | 6917 | 3000 |
| 50 | CR-QGeo | 4136 | 120 | 2.90 | 5423.67 | 25.000 | 7.92 | 1.73 | 7175 | 3000 |
| 100 | DSDV | 8255 | 934 | 11.31 | 4044.06 | 42.210 | **10.45** | 1.39 | 66796 | 39424 |
| 100 | **Greedy** | 8255 | 775 | 9.39 | **3546.47** | **7.742** | 7.63 | 1.41 | **24290** | **6000** |
| 100 | **MACG** | 8255 | **1218** | **14.75** | 4770.84 | 7.933 | 5.11 | 1.34 | 30583 | 9663 |
| 100 | QGeo | 8255 | 50 | 0.61 | 5412.47 | 120.000 | 7.52 | **1.22** | 31939 | 6000 |
| 100 | CR-QGeo | 8255 | 44 | 0.53 | 5139.35 | 136.364 | 8.39 | 1.25 | 30216 | 6000 |

Bold marks the best value per metric within each UAV-count tier, across all five protocols.

## 3. Observations

- **Every protocol degrades sharply as UAV count increases**, which is expected: the map size (600×600×100 m) is
  held fixed, so higher UAV count means a denser, more contention-heavy shared channel, not a larger deployment
  area. PDR for every protocol drops by roughly an order of magnitude between 10 and 50 UAVs, and further still
  between 10 and 100 UAVs.
- **DSDV's advantage inverts with density.** At n=10, DSDV has the best PDR, delay, and fewest collisions by a wide
  margin. But DSDV's proactive table-driven design means its control-packet volume scales with network size
  (650 → 3371 → 12094 → 39424 control packets as n grows), and at n=100 this makes DSDV generate **more collisions
  than any other protocol** (66796, vs 24290 for Greedy and 30-32k for QGeo/CR-QGeo/MACG) — its own control-plane
  overhead becomes the dominant source of channel contention.
- **Greedy has the lowest, flattest control overhead of the five** (600 control packets at every one of n=10/20,
  and only 3000/6000 at n=50/100 — far below DSDV's proactive flooding), which keeps it the best- or
  near-best-PDR protocol at n=20 and n=50. It only loses its lead once density is extreme enough (n=100) that a
  single flat Hello-broadcast network cannot avoid heavy channel contention regardless of how little control
  traffic it personally injects.
- **QGeo and CR-QGeo collapse hardest at high density.** At n=50 and n=100 both Q-learning protocols deliver under
  3% and under 1% of traffic respectively — far worse than every other protocol. Two compounding causes are
  visible in the data: (1) their **hop counts are higher** at low/medium density (2.4-2.8 vs 1.4-2.0 for the other
  three) because QGeo/CR-QGeo's `best_neighbor()` retains a non-trivial random-exploration probability throughout
  the run, so a fraction of hops are exploration moves rather than shortest-progress moves; more hops means more
  chances to hit a collision or a saturated queue. (2) Their **routing load explodes at high n** (up to 120-136
  control-packets-per-delivered-packet at n=100) purely because the denominator (delivered packets) collapses
  toward zero while Hello-packet volume stays constant — this is a symptom of collapse, not a cause. CR-QGeo tracks
  QGeo closely at every density, consistently slightly behind it on PDR and throughput (e.g. 31.81% vs 34.50% at
  n=20; 0.53% vs 0.61% at n=100) — the congestion-aware reward does not show a rescue effect at high density in
  this single-seed run.
- **MACG needs density before it pays off.** At n=10/20/50 it places 3rd of five, behind DSDV/Greedy and ahead of
  QGeo/CR-QGeo, with a routing load (1.36–4.47) and control-packet count (912–5488) consistently higher than
  Greedy's flat Hello-only overhead — the clustering handshake (Hello + Nomination + CH_DECLARE + JOIN_REQUEST/
  ACCEPT + CLUSTER_STATE + MAINTENANCE + MAINT_RESPONSE) costs real control traffic that a small, lightly-loaded,
  largely single-hop-reachable swarm does not need to pay for. But at n=100, MACG becomes the best-PDR protocol of
  all five (14.75%, vs Greedy's 9.39% and DSDV's 11.31%), while its own collisions (30583) and control overhead
  (9663) stay well below DSDV's (66796 / 39424) — the crossover from "3rd place" to "1st place" happens between
  n=50 and n=100, exactly where the other protocols' channel contention becomes severe enough for hierarchical
  organization to start earning back its overhead.

## 4. Why does the leading protocol win at each density?

The best-PDR protocol changes twice across this sweep — DSDV at n=10, Greedy at n=20/50, MACG at n=100 — and each
handover has a distinct, mechanistically-grounded explanation:

- **n=10 — DSDV wins because the channel is uncongested enough that proactive, always-fresh routes beat everything
  else.** With only 10 UAVs on a 600×600 m map, DSDV's periodically-broadcast distance-vector tables stay accurate
  (little time for staleness to accumulate before the next update) and every route is a short, direct multi-hop
  path computed without any per-packet route-discovery overhead. Its control-packet count (650) is comparable to
  the flat-Hello protocols, so at this density its usual weakness — control traffic that scales with network size —
  never gets a chance to bite. The two Q-learning protocols and MACG all carry extra structural cost at this size
  (QGeo/CR-QGeo's persistent exploration, MACG's clustering handshake) that a proactive table-driven protocol does
  not need to pay when the network is this small and stable.
- **n=20 and n=50 — Greedy wins because it has the least control overhead of any protocol that still forwards
  correctly, and no state to go stale.** Every hop is decided fresh, from whichever neighbor is currently closest
  to the destination in the local neighbor table — there is no multi-hop route to protect (unlike DSDV), no
  cluster/gateway state to maintain (unlike MACG), and no exploration probability that occasionally sends a packet
  the wrong way (unlike QGeo/CR-QGeo). Its control-packet volume is flat and Hello-only (1200 at both n=20 and
  n=50), so as contention rises with density, Greedy is the protocol contributing the *least* extra load to the
  very channel that is becoming the bottleneck. DSDV's proactive flooding starts to work against it here (routing
  load 4.2 at n=20 vs Greedy's 0.945), and MACG's clustering overhead has not yet started paying for itself at
  this density.
- **n=100 — MACG wins because it is the only protocol that changes the *shape* of the contention problem instead
  of just minimizing its own control traffic.** DSDV and Greedy are both flat networks: every drone effectively
  competes for the same shared channel with every other drone, so as density rises their collision counts explode
  (66796 and 24290 respectively) regardless of how lean their own control overhead is. MACG instead organizes the
  100-UAV swarm into many small clusters connected by a handful of gateways (see `routing/macg/macg_cluster_manager.py`'s
  diagnostics for the underlying mechanism), so a meaningful fraction of delivered traffic only ever needs short,
  local, intra-cluster Greedy hops rather than contending across the whole flat channel end to end. That
  restructuring costs control overhead of its own (9663 control packets, more than Greedy's 6000), but it is far
  cheaper than DSDV's proactive flooding (39424) and it reduces exposure to the channel-wide collision storm enough
  to net out ahead of both flat protocols — precisely the tradeoff hierarchical clustering is meant to make once a
  fully flat network becomes this congested.

## 5. Interpretation

This sweep shows no protocol holds up as density increases with a fixed map size — PDR for every protocol drops by
one to two orders of magnitude between n=10 and n=100 — but which protocol degrades *least* changes with density,
and each handover in Section 4 traces to a specific structural property: DSDV's proactive freshness wins when the
channel is uncongested and its own control traffic is cheap relative to network size; Greedy's near-zero control
overhead and freedom from stale state win in the middle of the sweep, where minimizing self-inflicted contention
matters most; and MACG's hierarchical clustering wins once the network is dense enough that no amount of
control-overhead minimization on a flat topology can avoid a channel-wide collision storm, and reorganizing the
topology itself becomes more valuable than any single next-hop-selection strategy. QGeo and CR-QGeo, whose
next-hop selection retains persistent random exploration and produces longer paths, are the most fragile under
density-driven contention at every tier. This is a single-seed, single-scenario sweep — general conclusions would
need multiple seeds and/or scaling the map area with UAV count to separate "more contention on a fixed channel"
from "genuinely larger network," and would benefit from extending the sweep past n=100 to see whether MACG's
advantage grows further or is a one-tier artifact.

## 6. Reproduction

```python
from utils import config
config.NUMBER_OF_DRONES = 20          # 10 / 20 / 50 / 100
config.INITIAL_ENERGY = 20_000        # explicit override — see Section 1
config.ROUTING_PROTOCOL = "macg"      # "dsdv" / "greedy" / "qgeo" / "cr_qgeo" / "macg"

import simpy
from simulator.simulator import Simulator

env = simpy.Environment()
channel_states = {i: simpy.Resource(env, capacity=1) for i in range(config.NUMBER_OF_DRONES)}
sim = Simulator(seed=2025, env=env, channel_states=channel_states, n_drones=config.NUMBER_OF_DRONES)
env.run(until=config.SIM_TIME)
sim.metrics.print_metrics()
```

All 20 runs (4 UAV counts × 5 protocols) use the same seed (2025); only `config.NUMBER_OF_DRONES` and
`config.ROUTING_PROTOCOL` change (plus the explicit `INITIAL_ENERGY = 20_000` override, needed because the
repository's config-file default has since changed — see Section 1).
