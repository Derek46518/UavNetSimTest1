# Experiment A: UAV Count Sweep (DSDV vs Greedy vs QGeo vs CR-QGeo)

## 1. Setup

All runs use the same random seed and simulation parameters, varying only `config.NUMBER_OF_DRONES` and
`config.ROUTING_PROTOCOL`. 16 runs total (4 UAV counts × 4 protocols), each executed in its own isolated process
(parallelized across cores) with identical seed 2025.

| Parameter | Value |
|---|---|
| Simulation seed | 2025 |
| UAV counts swept | 10, 20, 50, 100 |
| Protocols compared | DSDV, Greedy, QGeo, CR-QGeo |
| Simulation time (nominal) | 30 s |
| Map size | 600 m × 600 m × 100 m (unchanged across UAV counts) |
| Mobility model / speed | 3-D Gauss-Markov, 10 m/s |
| Traffic pattern | Poisson, rate = 5 packets/s per UAV |
| Max queue size | 200 packets |

**Important caveat discovered during this work (applies to every run in this report):** with the simulator's default
energy model (`INITIAL_ENERGY = 20000 J`, `ENERGY_THRESHOLD = 2000 J`, rotary-wing hover power ≈1104 W at 10 m/s),
every drone's `residual_energy` hits the sleep threshold and the drone **permanently stops generating and relaying
packets** at **t ≈ 16.3 s** — confirmed by direct instrumentation (all 10 drones slept at exactly t=16.4 s in a
diagnostic run) and by the underlying power formula. This is independent of UAV count (flight power depends only on
speed, not network size), so it applies identically to all four UAV-count tiers below — the relative comparisons
between protocols/densities are not biased by it. But the nominal "30 s simulation" is misleading: real network
activity is compressed into the first ~16 s, with the remainder of the 30 s window contributing little beyond
draining already-queued packets. This is not a routing-protocol effect; it is a pre-existing property of the
simulator's default energy configuration, unrelated to CR-QGeo. See `ExperimentC.md` for a full analysis and an
energy-neutralized re-run that isolates this effect. Per-drone generated-packet averages here (75.4 / 79.9 / 82.7 /
82.6 for n=10/20/50/100) all converge to ≈80, consistent with a ~16 s active window at rate 5 pkt/s — additional
confirmation of the same cutoff at every density.

## 2. Results

| n_drones | Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Routing Load | Throughput (Kbps) | Hop Count | Collisions | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | **DSDV** | 754 | **700** | **92.84** | **23.81** | 0.929 | 1045.25 | 1.63 | **6** | 650 |
| 10 | Greedy | 754 | 685 | 90.85 | 23.95 | **0.876** | **1079.15** | **1.58** | 26 | 600 |
| 10 | QGeo | 754 | 645 | 85.54 | 131.44 | 0.930 | 552.77 | 2.40 | 84 | 600 |
| 10 | CR-QGeo | 754 | 638 | 84.62 | 136.45 | 0.940 | 462.56 | 2.52 | 81 | 600 |
| 20 | **DSDV** | 1597 | 802 | 50.22 | 103.08 | 4.203 | 614.56 | 1.91 | 4888 | 3371 |
| 20 | **Greedy** | 1597 | **1270** | **79.52** | **122.91** | **0.945** | **698.81** | **1.69** | **924** | 1200 |
| 20 | QGeo | 1597 | 551 | 34.50 | 3392.59 | 2.178 | 30.41 | 2.71 | 856 | 1200 |
| 20 | CR-QGeo | 1597 | 508 | 31.81 | 3850.30 | 2.362 | 13.70 | 2.77 | 951 | 1200 |
| 50 | DSDV | 4136 | 1246 | 30.13 | 3218.56 | 9.706 | 24.17 | **1.44** | 20851 | 12094 |
| 50 | **Greedy** | 4136 | **1301** | **31.46** | **2214.56** | **2.306** | **33.71** | 1.50 | **6211** | 3000 |
| 50 | QGeo | 4136 | 107 | 2.59 | 5125.69 | 28.037 | 8.76 | 1.81 | 6917 | 3000 |
| 50 | CR-QGeo | 4136 | 120 | 2.90 | 5423.67 | 25.000 | 7.92 | 1.73 | 7175 | 3000 |
| 100 | **DSDV** | 8255 | **934** | **11.31** | 4044.06 | 42.210 | **10.45** | **1.39** | 66796 | 39424 |
| 100 | Greedy | 8255 | 775 | 9.39 | 3546.47 | **7.742** | 7.63 | 1.41 | 24290 | 6000 |
| 100 | QGeo | 8255 | 50 | 0.61 | 5412.47 | 120.000 | 7.52 | 1.22 | 31939 | 6000 |
| 100 | CR-QGeo | 8255 | 44 | 0.53 | **5139.35** | 136.364 | 8.39 | 1.25 | **30216** | 6000 |

Bold marks the best value per metric within each UAV-count tier.

## 3. Observations

- **Every protocol degrades sharply as UAV count increases**, which is expected: the map size (600×600×100 m) is
  held fixed, so higher UAV count means a denser, more contention-heavy shared channel, not a larger deployment area.
  PDR for all four protocols drops by roughly an order of magnitude between 10 and 50 UAVs, and by two orders of
  magnitude between 10 and 100 UAVs.
- **DSDV's advantage inverts with density.** At n=10, DSDV has the best PDR, delay, and fewest collisions by a wide
  margin. But DSDV's proactive table-driven design means its control-packet volume scales with network size
  (650 → 3371 → 12094 → 39424 control packets as n grows), and at n=100 this makes DSDV generate **more collisions
  than any other protocol** (66796, vs 24290 for Greedy and ~30-32k for QGeo/CR-QGeo) — its own control-plane
  overhead becomes the dominant source of channel contention. Greedy, which only floods lightweight Hello
  broadcasts, scales far better on routing load and collisions at high density (best routing load and best PDR at
  n=20/50, competitive at n=100 despite losing the "best PDR" crown to DSDV there by a small absolute margin — 11.31%
  vs 9.39%, both effectively network collapse).
- **QGeo and CR-QGeo collapse hardest at high density.** At n=50 and n=100 both Q-learning protocols deliver under
  3% and under 1% of traffic respectively — far worse than DSDV/Greedy. Two compounding causes are visible in the
  data: (1) their **hop counts are higher** at low/medium density (2.4-2.8 vs 1.4-1.9 for DSDV/Greedy) because
  QGeo/CR-QGeo's `best_neighbor()` retains a non-trivial random-exploration probability throughout the run, so a
  fraction of hops are exploration moves rather than shortest-progress moves; more hops means more chances to hit
  a collision or a saturated queue. (2) Their **routing load explodes at high n** (up to 120-136 control-packets-
  per-delivered-packet at n=100) purely because the denominator (delivered packets) collapses toward zero while
  Hello-packet volume stays constant — this is a symptom of collapse, not a cause.
- **CR-QGeo tracks QGeo closely at every density**, consistently slightly behind it on PDR and throughput (e.g.,
  31.81% vs 34.50% at n=20; 0.53% vs 0.61% at n=100), consistent with the single-seed Part-2 finding in
  `PROTOCOL_COMPARISON_REPORT.md`. The congestion-aware reward does not show a rescue effect at high density in this
  single-seed run — if anything, both Q-learning protocols degrade in lockstep, suggesting the dominant failure mode
  at high density (channel saturation / collision storms) overwhelms whatever benefit the congestion penalty or
  continuous gamma provides. CR-QGeo does have marginally fewer collisions than QGeo at n=100 (30216 vs 31939), a
  small and single-seed-fragile difference, not a clear win.

## 4. Interpretation

This sweep shows all four protocols were tuned/evaluated (in the existing `PROTOCOL_COMPARISON_REPORT.md`) at a UAV
count (10) where the shared 600×600×100 m channel is lightly loaded; none of the four protocols — including the two
proactive/greedy ones — hold up as density increases with a fixed map size. The clearest structural finding is that
**DSDV's control overhead becomes counter-productive above roughly 20-50 UAVs** in this fixed-area setup, while
**Greedy's minimal control overhead makes it the most robust of the four as density grows**. QGeo and CR-QGeo, whose
next-hop selection retains persistent random exploration and produces longer paths, are the most fragile under
density-driven contention. This is a single-seed, single-scenario sweep — general conclusions would need multiple
seeds and/or scaling the map area with UAV count to separate "more contention on a fixed channel" from "genuinely
larger network."

## 5. Reproduction

```python
from utils import config
config.NUMBER_OF_DRONES = 20          # 10 / 20 / 50 / 100
config.ROUTING_PROTOCOL = "cr_qgeo"   # "dsdv" / "greedy" / "qgeo" / "cr_qgeo"

import simpy
from simulator.simulator import Simulator

env = simpy.Environment()
channel_states = {i: simpy.Resource(env, capacity=1) for i in range(config.NUMBER_OF_DRONES)}
sim = Simulator(seed=2025, env=env, channel_states=channel_states, n_drones=config.NUMBER_OF_DRONES)
env.run(until=config.SIM_TIME)
sim.metrics.print_metrics()
```

All 16 runs use the same seed (2025); only `config.NUMBER_OF_DRONES` and `config.ROUTING_PROTOCOL` change.
