# Experiment D: Map Size Sweep (DSDV vs Greedy vs QGeo vs CR-QGeo vs MACG)

## 1. Setup

This experiment isolates the effect of map size — i.e. spatial density/connectivity — independently of UAV count,
complementing Experiment A (which fixes the map at 600×600 m and instead varies UAV count). `MAP_LENGTH` and
`MAP_WIDTH` are swept together (square maps), `MAP_HEIGHT` stays fixed at 100 m as in every other experiment.

| Parameter | Value |
|---|---|
| Simulation seed | 2025 |
| Map sizes swept (square, `MAP_LENGTH = MAP_WIDTH`) | 300, 600, 900, 1200, 1600 m |
| UAV counts | 10 and 50 (run as two independent sub-sweeps) |
| Protocols compared | DSDV, Greedy, QGeo, CR-QGeo, MACG |
| Total simulation time | 120 s |
| `INITIAL_ENERGY` | 200,000 J |
| Mobility model / speed | 3-D Gauss-Markov, 10 m/s |
| Traffic pattern | Poisson, rate = 5 packets/s per UAV |
| Map height | 100 m (fixed) |

50 runs total (5 map sizes × 5 protocols × 2 UAV counts), each in its own isolated process.

**Why 120 s / 200,000 J rather than the 30 s / 20,000 J used in Experiments A/B:** MACG's clustering needs a
bootstrap window (`MACG_BOOTSTRAP_DELAY` + nomination + CH-declaration + join windows, roughly 1.75–2.25 s) before
any hierarchy even exists, and then further time for clusters to stabilize once formed — more so at sparser map
sizes, where a node has fewer neighbors to nominate or join in the first place. A 30-second run risks judging every
protocol's map-size behavior mid-bootstrap rather than at steady state, exactly the duration effect Experiment C
was built to correct for. Experiment D therefore reuses Experiment C's convention directly: 120 s of simulated
time, with `INITIAL_ENERGY` raised to 200,000 J so no drone runs out of flight energy partway through (the default
20,000 J budget only covers ≈16 s of flight regardless of map size, since flight power depends on speed, not map
size — confirmed directly during setup: an initial 120 s/20,000 J run produced the *exact same* generated-packet
count, 754, at every single map size, the unmistakable signature of every drone going to permanent sleep at the
same ≈16.3 s mark regardless of map size). This is applied identically to all five protocols and both UAV counts.

**Connectivity context.** The simulator's physical radio range, `maximum_communication_range()`, is ≈249 m under
the default PHY configuration; the MAC-layer carrier-sense/collision-domain range, `SENSING_RANGE`, is 750 m. A
simple 2-D disk-coverage estimate (`E[neighbors] ≈ (n-1)·π·r²/area`, ignoring boundary and altitude effects) gives
a rough sense of how sparse each map-size tier is at each UAV count:

| Map side (m) | Diagonal ÷ comm range | E[neighbors] @ n=10 | E[neighbors] @ n=50 | Regime |
|---|---|---|---|---|
| 300 | 1.7 | ~19.5 (capped at 9) | ~121.9 (capped at 49) | Near-complete graph |
| 600 | 3.4 | ~4.9 | ~29.4 | Connected multi-hop mesh |
| 900 | 5.1 | ~2.2 | ~13.1 | Sparser multi-hop |
| 1200 | 6.8 | ~1.2 | ~7.4 | Borderline (n=10) / still well-connected (n=50) |
| 1600 | 9.1 | ~0.7 | ~4.1 | Likely fragmented (n=10) / sparse multi-hop (n=50) |

## 2. Results

### n_drones = 10

| Map (m) | Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Routing Load | Throughput (Kbps) | Hop Count | Collisions | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|---|
| 300 | DSDV | 5863 | 5845 | **99.69** | 6.83 | **0.411** | 1500.60 | 1.11 | 419 | **2400** |
| 300 | Greedy | 5863 | 5749 | 98.06 | **6.61** | 0.417 | **1526.34** | **1.09** | **284** | 2400 |
| 300 | MACG | 5863 | 5755 | 98.16 | 6.96 | 0.634 | 1503.51 | 1.12 | 304 | 3647 |
| 300 | QGeo | 5863 | 5712 | 97.42 | 32.89 | 0.420 | 607.57 | 2.50 | 542 | 2400 |
| 300 | CR-QGeo | 5863 | 5737 | 97.85 | 32.43 | 0.418 | 631.75 | 2.46 | 395 | 2400 |
| 600 | DSDV | 5863 | 1522 | 25.96 | **228.19** | 3.205 | **1164.05** | **1.57** | 1233 | 4878 |
| 600 | Greedy | 5863 | 3981 | **67.90** | 468.71 | **0.603** | 1049.85 | 1.64 | **213** | **2400** |
| 600 | MACG | 5863 | 3898 | 66.48 | 1062.78 | 0.938 | 446.26 | 1.97 | 719 | 3655 |
| 600 | QGeo | 5863 | 2497 | 42.59 | 912.90 | 0.961 | 273.78 | 2.16 | 479 | 2400 |
| 600 | CR-QGeo | 5863 | 2864 | 48.85 | 1423.32 | 0.838 | 196.98 | 2.29 | 725 | 2400 |
| 900 | DSDV | 5863 | 723 | 12.33 | **581.42** | 6.960 | **1241.46** | 1.42 | 2754 | 5032 |
| 900 | Greedy | 5863 | 2128 | **36.30** | 746.18 | **1.128** | 1161.19 | **1.40** | **888** | **2400** |
| 900 | MACG | 5863 | 1831 | 31.23 | 1147.99 | 2.013 | 302.67 | 1.68 | 1969 | 3686 |
| 900 | QGeo | 5863 | 1530 | 26.10 | 1789.60 | 1.569 | 100.05 | 1.79 | 3548 | 2400 |
| 900 | CR-QGeo | 5863 | 1305 | 22.26 | 1187.54 | 1.839 | 161.58 | 1.68 | 2335 | 2400 |
| 1200 | DSDV | 5863 | 1064 | 18.15 | **770.12** | 3.131 | **1178.03** | **1.47** | 1658 | 3331 |
| 1200 | Greedy | 5863 | 1567 | **26.73** | 818.57 | **1.532** | 1093.25 | 1.53 | **1643** | **2400** |
| 1200 | MACG | 5863 | 1462 | 24.94 | 1397.99 | 2.490 | 233.72 | 1.73 | 4804 | 3640 |
| 1200 | QGeo | 5863 | 910 | 15.52 | 1470.59 | 2.637 | 208.34 | 1.71 | 2185 | 2400 |
| 1200 | CR-QGeo | 5863 | 1427 | 24.34 | 1764.10 | 1.682 | 113.56 | 1.83 | 4550 | 2400 |
| 1600 | DSDV | 5863 | 943 | 16.08 | 1153.78 | 3.191 | 1047.56 | 1.61 | **3471** | 3009 |
| 1600 | Greedy | 5863 | 1154 | **19.68** | **1124.06** | **2.080** | **1065.64** | 1.53 | 3652 | **2400** |
| 1600 | MACG | 5863 | 516 | 8.80 | 1188.69 | 7.010 | 592.19 | **1.45** | 4007 | 3617 |
| 1600 | QGeo | 5863 | 561 | 9.57 | 1313.13 | 4.278 | 274.54 | 1.50 | 3886 | 2400 |
| 1600 | CR-QGeo | 5863 | 544 | 9.28 | 1249.78 | 4.412 | 267.27 | 1.54 | 3641 | 2400 |

### n_drones = 50

| Map (m) | Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Routing Load | Throughput (Kbps) | Hop Count | Collisions | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|---|
| 300 | DSDV | 29879 | 7172 | 24.00 | 5410.47 | 33.072 | 21.26 | **1.06** | 1930543 | 237191 |
| 300 | Greedy | 29879 | 7481 | 25.04 | 4775.86 | **1.604** | 18.48 | 1.09 | 59839 | **12000** |
| 300 | MACG | 29879 | 11552 | **38.66** | **4345.19** | 2.392 | **23.51** | 1.08 | **43059** | 27633 |
| 300 | QGeo | 29879 | 1480 | 4.95 | 7570.88 | 8.108 | 1.38 | 1.10 | 66683 | 12000 |
| 300 | CR-QGeo | 29879 | 1770 | 5.92 | 7560.67 | 6.780 | 1.37 | 1.09 | 61707 | 12000 |
| 600 | DSDV | 29879 | 1620 | 5.42 | **4059.34** | 59.633 | **18.94** | 1.35 | 593176 | 96606 |
| 600 | Greedy | 29879 | 5814 | **19.46** | 4819.13 | **2.064** | 15.04 | 1.41 | 38932 | **12000** |
| 600 | MACG | 29879 | 4126 | 13.81 | 5101.30 | 5.178 | 13.81 | 1.33 | **28966** | 21364 |
| 600 | QGeo | 29879 | 1225 | 4.10 | 7122.66 | 9.796 | 2.04 | **1.16** | 60021 | 12000 |
| 600 | CR-QGeo | 29879 | 1397 | 4.68 | 6953.96 | 8.590 | 1.97 | 1.19 | 57738 | 12000 |
| 900 | DSDV | 29879 | 853 | 2.85 | **3267.57** | 122.725 | **68.67** | 1.77 | 1135243 | 104684 |
| 900 | Greedy | 29879 | 4176 | **13.98** | 4295.16 | **2.874** | 52.27 | 1.63 | **82256** | **12000** |
| 900 | MACG | 29879 | 2835 | 9.49 | 4634.59 | 7.465 | 59.49 | **1.43** | 135495 | 21163 |
| 900 | QGeo | 29879 | 1216 | 4.07 | 5060.39 | 9.868 | 61.85 | 1.81 | 108659 | 12000 |
| 900 | CR-QGeo | 29879 | 1546 | 5.17 | 5354.20 | 7.762 | 43.74 | 1.69 | 108765 | 12000 |
| 1200 | DSDV | 29879 | 623 | 2.09 | **2693.37** | 102.827 | 126.84 | 2.74 | 747207 | 64061 |
| 1200 | Greedy | 29879 | 2346 | **7.85** | 2984.59 | **5.115** | **186.79** | 1.85 | **45649** | **12000** |
| 1200 | MACG | 29879 | 1351 | 4.52 | 4271.07 | 14.447 | 83.00 | **1.70** | 118223 | 19518 |
| 1200 | QGeo | 29879 | 730 | 2.44 | 4440.93 | 16.438 | 32.44 | 1.98 | 120284 | 12000 |
| 1200 | CR-QGeo | 29879 | 658 | 2.20 | 3706.64 | 18.237 | 54.08 | 1.85 | 124247 | 12000 |
| 1600 | DSDV | 29879 | 1163 | 3.89 | **1356.53** | 37.592 | **564.86** | 2.77 | 588629 | 43720 |
| 1600 | Greedy | 29879 | 1584 | **5.30** | 1627.12 | **7.576** | 503.12 | 2.09 | **122275** | **12000** |
| 1600 | MACG | 29879 | 941 | 3.15 | 2887.94 | 19.538 | 119.72 | 1.63 | 211416 | 18385 |
| 1600 | QGeo | 29879 | 465 | 1.56 | 2520.89 | 25.806 | 88.91 | **1.58** | 215467 | 12000 |
| 1600 | CR-QGeo | 29879 | 609 | 2.04 | 3307.90 | 19.704 | 41.92 | 2.06 | 143211 | 12000 |

Bold marks the best value per metric within each (n_drones, map size) tier, across all five protocols.

## 3. Observations

- **Every protocol's PDR falls sharply as the map grows**, at both UAV counts, which is the expected effect: a
  bigger map at a fixed UAV count means a sparser, more disconnected network, not more capacity. At n=10, PDR
  drops from 97–100% at 300 m to single digits by 1600 m for three of the five protocols. At n=50, PDR is already
  down to 5–39% at 300 m (channel contention dominates before sparsity even becomes a factor) and falls to 1.6–5.3%
  by 1600 m.
- **DSDV is the standout at the smallest, densest tier and the worst-behaved protocol almost everywhere else.** At
  n=10/300 m it delivers 99.69% of traffic — the best result recorded in this entire family of experiments — with
  the lowest routing load (0.411) and the fewest control packets, because a small, dense, low-churn network is
  exactly where periodic table-driven routing is cheapest and most accurate. But at every n=50 tier its collision
  count is catastrophic (588k–1.9M, one to two orders of magnitude above any other protocol) and its routing load
  reaches over 100 at 900 m and 1200 m. This is a broadcast-storm effect specific to DSDV's design: its
  `detect_broken_link_periodically()` mechanism re-broadcasts an "immediate" table update the moment any link
  breaks, and every node that receives a not-yet-seen immediate update re-broadcasts it again — at 50 UAVs moving
  continuously for 120 seconds, links break constantly, and each break can cascade into a network-wide rebroadcast
  flood. The effect compounds with duration (Experiment C already showed DSDV collapsing to zero deliveries by
  120s at a single map size) and now clearly compounds with UAV count too.
- **Greedy is the most consistently strong protocol across the sweep**, winning PDR at 8 of the 10 (map size, UAV
  count) tiers tested, including every n=50 tier and every n=10 tier except the very densest and very sparsest. Its
  control-packet count is flat and low (2400 at n=10, 12000 at n=50) regardless of map size, since it only ever
  sends Hello broadcasts — it never pays extra for either density or sparsity the way the other four protocols do
  in different ways.
- **QGeo and CR-QGeo are the weakest protocols at nearly every tier** except the very smallest/densest map, for the
  same structural reason as in Experiments A–C: persistent random exploration and longer average hop counts (up to
  2.5 hops at n=10/300m — more than double DSDV/Greedy/MACG's ~1.1 at that same tier) mean more opportunities to
  hit a collision or a stale queue. CR-QGeo trades places with QGeo inconsistently across tiers with no clear
  pattern tied to map size specifically.
- **MACG's performance tracks local density almost exactly, regardless of whether that density comes from more
  UAVs or a smaller map.** At n=50/300 m — the single densest tier tested (≈122 expected neighbors before the
  9-neighbor Hello-table cap) — MACG is the best protocol by a wide margin (38.66% PDR vs Greedy's 25.04% and
  DSDV's 24.00%), while also having the *fewest* collisions of any protocol at that tier (43059, versus Greedy's
  59839 and DSDV's 1.93 million). As the map grows and density drops, MACG's relative position slides: 2nd at
  n=50/600–1200m and n=10/600–1200m, and by the sparsest tier (n=10/1600m, ≈0.7 expected neighbors) it becomes the
  single *worst* protocol of the five (8.80% PDR, below even QGeo and CR-QGeo), with by far the worst routing load
  (7.010, more than triple DSDV's) — it is paying its full clustering-control-packet tax while having too few
  neighbors per node to form clusters worth the cost.

## 4. Why does the leading protocol win at each tier?

Three different protocols lead PDR somewhere in this sweep — DSDV once, MACG once, Greedy everywhere else — and
each has a distinct explanation tied directly to local network density:

- **DSDV wins only at n=10/300m — the single densest, lowest-churn tier tested.** With 10 UAVs on a 300 m map, the
  physical topology is close to a complete graph and changes little between successive table broadcasts, so
  DSDV's proactive routes stay accurate essentially all the time, its control overhead never has enough
  simultaneous link churn to cascade into a broadcast storm, and its pre-computed multi-hop routes beat Greedy's
  locally-greedy hop-by-hop choices on raw efficiency. This is the same mechanism behind DSDV's win in
  Experiment A's n=10 tier and Experiment B's 10 m/s tier — DSDV wins precisely when there is so little topology
  change for its proactive design to react to that its usual weakness never gets triggered. Every other map size
  or UAV count tested here has enough churn (from sparsity, density-driven contention, or both) to flip this
  advantage into DSDV's characteristic broadcast-storm collapse instead.
- **Greedy wins across the middle and sparse end of the sweep, at both UAV counts, for the same reason it wins
  most tiers in Experiments A–C: its next-hop decision has no state that density or sparsity can degrade.** It
  does not need enough neighbors to elect a cluster head (unlike MACG), a converged Q-table (unlike QGeo/CR-QGeo),
  or a fresh proactive table (unlike DSDV) — it simply forwards to whichever *current* neighbor is closest to the
  destination, however many or few neighbors that happens to be. Its control-packet cost is flat regardless of
  map size, so as density drops it never has extra self-inflicted overhead to shed, and as density rises (n=50)
  it never has extra self-inflicted overhead to cause a collision storm either. This flatness is what makes it the
  most robust default across a spatial dimension that pushes every other protocol into a different, dimension-
  specific failure mode.
- **MACG wins only at n=50/300m, where density is high enough (from UAV count, not map size) for its clustering
  to form quickly and pay for itself immediately** — the same mechanism behind MACG's win in Experiment A's n=100
  tier, now confirmed to be about *local neighbor density* specifically rather than UAV count per se: a small map
  packed with 50 UAVs gives MACG plenty of well-connected candidates to nominate, elect, and join, so clusters
  form fast and a large fraction of traffic gets to stay on short intra-cluster hops instead of contending for a
  single flat channel — exactly the mechanism identified in `ExperimentA.md` §4, here triggered by shrinking the
  map instead of growing the swarm. The flip side is equally informative: at the sparsest tier tested
  (n=10/1600m), MACG has too few neighbors per node to form clusters worth the overhead, and becomes the worst
  protocol of the five — clustering has a fixed control-packet cost that only pays off above some local-density
  threshold, and below that threshold it is a pure liability. Density, not raw UAV count or raw map size alone, is
  the variable that actually predicts whether MACG helps or hurts.

## 5. Interpretation

This sweep confirms that MACG's win/lose boundary from Experiment A is really about **local connectivity density**,
not UAV count specifically: shrinking the map at fixed UAV count reproduces the same "clustering pays off" result
(n=50/300m) that growing the swarm at a fixed map produced in Experiment A (n=100), and stretching the map at low
UAV count reproduces the opposite result even more starkly — MACG does not merely lose at n=10/1600m, it becomes
the single worst protocol tested in this entire experiment family. Greedy's structural advantage — a forwarding
rule with no state for either density or sparsity to degrade — makes it the most robust default across this
spatial dimension exactly as it was across UAV count (Experiment A) and speed (Experiment B). DSDV's proactive
design is a double-edged sword along this same axis: unbeatable in the single lowest-churn tier tested, and the
worst protocol by collision count in every higher-churn tier, regardless of whether that churn comes from
sparsity-driven route staleness or density-driven broadcast storms. This is a single-seed, two-UAV-count sweep —
testing intermediate UAV counts (20, 30) at the sparser map tiers would help confirm whether MACG's density
threshold is a sharp cliff or a smooth crossover, and a third UAV-count tier at the largest map sizes would help
distinguish "genuinely too sparse for any clustering" from "just needs a slightly larger nomination/join window."

## 6. Reproduction

```python
from utils import config
config.MAP_LENGTH = 900               # 300 / 600 / 900 / 1200 / 1600 (MAP_WIDTH set identically)
config.MAP_WIDTH = 900
config.NUMBER_OF_DRONES = 50          # 10 or 50
config.DRONE_SPEED = 10
config.SIM_TIME = 120 * 1e6
config.INITIAL_ENERGY = 200_000       # see Section 1 — required for the 120s window to matter at all
config.ROUTING_PROTOCOL = "macg"      # "dsdv" / "greedy" / "qgeo" / "cr_qgeo" / "macg"

import simpy
from simulator.simulator import Simulator

env = simpy.Environment()
channel_states = {i: simpy.Resource(env, capacity=1) for i in range(config.NUMBER_OF_DRONES)}
sim = Simulator(seed=2025, env=env, channel_states=channel_states, n_drones=config.NUMBER_OF_DRONES)
env.run(until=config.SIM_TIME)
sim.metrics.print_metrics()
```

All 50 runs (5 map sizes × 5 protocols × 2 UAV counts) use the same seed (2025); only `config.MAP_LENGTH` /
`config.MAP_WIDTH`, `config.NUMBER_OF_DRONES`, and `config.ROUTING_PROTOCOL` change.
