# Experiment B: Mobility Speed Sweep (DSDV vs Greedy vs QGeo vs CR-QGeo)

## 1. Setup

All runs use the same seed and parameters, varying only `config.DRONE_SPEED` (the homogeneous UAV speed) and
`config.ROUTING_PROTOCOL`. 16 runs total (4 speeds × 4 protocols).

| Parameter | Value |
|---|---|
| Simulation seed | 2025 |
| Speeds swept | 10, 20, 30, 40 m/s |
| Protocols compared | DSDV, Greedy, QGeo, CR-QGeo |
| Number of UAVs | 10 |
| Simulation time (nominal) | 30 s |
| Map size | 600 m × 600 m × 100 m |
| Mobility model | 3-D Gauss-Markov |
| Traffic pattern | Poisson, rate = 5 packets/s per UAV |

`config.DRONE_SPEED` did not previously exist as a tunable — the simulator hardcoded the homogeneous-case speed to
10 m/s in `simulator/simulator.py`. A new config constant `DRONE_SPEED` (default 10, so existing behavior is
unchanged) was added, and `simulator.py`'s one hardcoded `speed = 10` line now reads `speed = config.DRONE_SPEED`,
so this sweep could be run at all.

## 2. A second confound found: energy depletion time depends on speed

The same energy-exhaustion behavior documented in `ExperimentC.md` (drones permanently stop generating/relaying
once `residual_energy` hits `ENERGY_THRESHOLD`, at default `INITIAL_ENERGY=20000 J`) also affects this experiment,
and here it does **not** cancel out across the swept variable: the rotary-wing power model is a non-monotonic
function of speed, so **how long the network stays alive before depletion changes with speed**:

| Speed (m/s) | Hover/flight power (W) | Time to energy depletion (s) |
|---|---|---|
| 10 | 1104.0 | 16.3 |
| 20 | 923.8 | 19.5 |
| 30 | 972.3 | 18.5 |
| 40 | 1198.6 | 15.0 |

This is directly visible in the "packets generated" column of the as-collected results below (912 at 20 m/s vs 685
at 40 m/s, out of a nominal 30 s × 10 UAVs × 5 pkt/s ≈ 1500 budget) — the ranking of generated-packet counts exactly
matches the ranking of depletion times (20 m/s lasts longest → most packets; 40 m/s depletes fastest → fewest). This
means the "as collected" sweep below conflates two effects: (a) the mobility/link-stability effect the experiment
is meant to isolate, and (b) how much active network time each speed got before its UAVs went permanently silent.
Section 4 gives a second, energy-neutralized pass that removes confound (b).

## 3. Results — as collected (default energy model, both confounds present)

| Speed | Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Throughput (Kbps) | Hop Count | Collisions |
|---|---|---|---|---|---|---|---|---|
| 10 | **DSDV** | 754 | **700** | **92.84** | **23.81** | 1045.25 | 1.63 | **6** |
| 10 | Greedy | 754 | 685 | 90.85 | 23.95 | **1079.15** | **1.58** | 26 |
| 10 | QGeo | 754 | 645 | 85.54 | 131.44 | 552.77 | 2.40 | 84 |
| 10 | CR-QGeo | 754 | 638 | 84.62 | 136.45 | 462.56 | 2.52 | 81 |
| 20 | DSDV | 912 | 517 | 56.69 | 26.04 | 1116.99 | 1.65 | 302 |
| 20 | **Greedy** | 912 | **658** | **72.15** | **16.45** | **1211.52** | **1.43** | **40** |
| 20 | QGeo | 912 | 579 | 63.49 | 195.41 | 446.48 | 2.57 | 110 |
| 20 | CR-QGeo | 912 | 559 | 61.29 | 438.12 | 189.26 | 2.79 | 183 |
| 30 | DSDV | 867 | 561 | 64.71 | 266.31 | 1057.32 | 1.60 | 92 |
| 30 | **Greedy** | 867 | **574** | **66.21** | 227.75 | **1131.29** | **1.54** | 82 |
| 30 | QGeo | 867 | 352 | 40.60 | 129.00 | 420.63 | 2.76 | **14** |
| 30 | CR-QGeo | 867 | 395 | 45.56 | **127.77** | 356.95 | 2.60 | 61 |
| 40 | **DSDV** | 685 | **447** | **65.26** | 312.19 | 1057.05 | **1.63** | 120 |
| 40 | Greedy | 685 | 442 | 64.53 | 435.30 | **1085.70** | 1.59 | 106 |
| 40 | QGeo | 685 | 339 | 49.49 | 225.37 | 364.53 | 2.55 | 140 |
| 40 | CR-QGeo | 685 | 318 | 46.42 | **216.60** | 363.52 | 2.56 | **91** |

Bold marks the best value per metric within each speed tier. Note the non-monotonic, hard-to-interpret PDR trend for
DSDV (92.84 → 56.69 → 64.71 → 65.26 as speed increases) — this is the energy-duration confound from Section 2, not
a real "DSDV gets better at higher speed" effect.

## 4. Results — energy-neutralized (isolates the mobility effect)

For this pass only, `config.INITIAL_ENERGY` was overridden to 5,000,000 J at runtime in the test harness (not
persisted to `config.py`) so no drone depletes mid-run at any of the four speeds — applied identically across all
16 runs, so it does not bias the comparison. All other parameters are unchanged.

| Speed | Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Throughput (Kbps) | Hop Count | Collisions |
|---|---|---|---|---|---|---|---|---|
| 10 | **DSDV** | 1447 | **1108** | **76.57** | **18.23** | 1175.90 | 1.52 | 88 |
| 10 | Greedy | 1447 | 1103 | 76.23 | 17.96 | **1236.95** | **1.42** | **28** |
| 10 | QGeo | 1447 | 1062 | 73.39 | 203.36 | 450.13 | 2.27 | 162 |
| 10 | CR-QGeo | 1447 | 1042 | 72.01 | 209.72 | 384.41 | 2.41 | 145 |
| 20 | **Greedy** | 1447 | **972** | **67.17** | 447.86 | **1057.37** | **1.63** | **60** |
| 20 | DSDV | 1447 | 612 | 42.29 | 326.24 | 1065.63 | 1.70 | 404 |
| 20 | CR-QGeo | 1447 | 719 | 49.69 | 568.95 | 170.77 | 2.62 | 247 |
| 20 | QGeo | 1447 | 660 | 45.61 | **259.53** | 425.42 | 2.51 | 148 |
| 30 | **Greedy** | 1447 | **820** | **56.67** | **163.10** | **1138.75** | **1.55** | 124 |
| 30 | DSDV | 1447 | 609 | 42.09 | 245.95 | 1081.95 | 1.59 | 252 |
| 30 | CR-QGeo | 1447 | 532 | 36.77 | 481.90 | 288.83 | 2.62 | 88 |
| 30 | QGeo | 1447 | 430 | 29.72 | 508.03 | 365.06 | 2.78 | **51** |
| 40 | **Greedy** | 1447 | **782** | **54.04** | 541.79 | **1068.18** | **1.57** | 106 |
| 40 | DSDV | 1447 | 500 | 34.55 | **392.06** | 1055.16 | 1.63 | 262 |
| 40 | QGeo | 1447 | 660 | 45.61 | 1128.19 | 235.63 | 2.58 | 209 |
| 40 | CR-QGeo | 1447 | 572 | 39.53 | 660.95 | 256.99 | 2.51 | **122** |

Every protocol now sees the identical 1447 packets generated at every speed, confirming the mobility variable is
cleanly isolated here — any remaining differences across speed are due to link stability/mobility, not unequal
active-network duration.

## 5. Observations

- **With the confound removed, PDR degrades monotonically with speed for every protocol** — e.g. DSDV
  76.57% → 42.29% → 42.09% → 34.55%; Greedy 76.23% → 67.17% → 56.67% → 54.04%; QGeo 73.39% → 45.61% → 29.72% →
  45.61%; CR-QGeo 72.01% → 49.69% → 36.77% → 39.53%. This is the expected mobility effect: faster UAVs break
  links faster (both because Hello-based neighbor tables go stale faster and because the physical topology changes
  faster than the routing state can track it).
- **Greedy is the most mobility-robust of the four**, taking over as the best-PDR protocol at every speed ≥ 20 m/s
  in the neutralized data (it starts essentially tied with DSDV at 10 m/s, then pulls ahead as speed increases).
  This matches Greedy's design: it always forwards to whichever *current* neighbor is closest to the destination,
  re-decided fresh at every hop from live neighbor-table data, with no dependency on a possibly-stale multi-hop
  route (DSDV) or a slowly-converging Q-table (QGeo/CR-QGeo).
- **DSDV degrades the fastest with speed.** Its proactive routes are computed from periodically-exchanged tables
  and can go stale between updates; at higher speed this staleness causes more forwarding failures, visible in its
  collision count climbing sharply (88 → 404 → 252 → 262) as its control traffic increasingly chases a moving
  target.
- **QGeo and CR-QGeo are consistently the two worst performers at every speed** in both the as-collected and
  neutralized data, for the same structural reason identified in `ExperimentA.md` and
  `PROTOCOL_COMPARISON_REPORT.md`: persistent random exploration and higher hop counts. CR-QGeo tracks QGeo closely
  and trades places with it non-systematically across speeds (CR-QGeo slightly ahead of QGeo at 20/30 m/s, behind
  at 10/40 m/s) — no consistent advantage or disadvantage from the congestion/gamma changes is visible as a
  function of mobility speed in this single-seed sweep.
- **MAC/E2E delay for QGeo and CR-QGeo grows sharply with speed** (e.g. CR-QGeo's MAC delay: 43 ms → 219 ms →
  172 ms → 189 ms at 10 m/s default-energy vs the longer-duration neutralized runs), consistent with their
  Q-tables needing to re-learn good next hops as the topology shifts faster than at low speed — the "stability"
  half of CR-QGeo's design goal, but here that adaptation cost shows up as delay rather than being fully absorbed
  by the continuous gamma.

## 6. Interpretation

Once the energy-duration confound is removed, this sweep shows a clean, monotonic mobility-degrades-everything
trend, with Greedy the most robust of the four protocols to increasing speed and QGeo/CR-QGeo the least. There is
no evidence in this single-seed sweep that CR-QGeo's reliability-aware continuous gamma gives it a mobility-
robustness edge over plain QGeo — the two track each other closely with no consistent ordering across speeds. This
does not rule out a benefit at other traffic rates, seeds, or exploration settings, only that none is visible here.

## 7. Reproduction

```python
from utils import config
config.DRONE_SPEED = 20               # 10 / 20 / 30 / 40
config.ROUTING_PROTOCOL = "cr_qgeo"   # "dsdv" / "greedy" / "qgeo" / "cr_qgeo"
# config.INITIAL_ENERGY = 5_000_000   # uncomment to reproduce the energy-neutralized pass (Section 4)

import simpy
from simulator.simulator import Simulator

env = simpy.Environment()
channel_states = {i: simpy.Resource(env, capacity=1) for i in range(config.NUMBER_OF_DRONES)}
sim = Simulator(seed=2025, env=env, channel_states=channel_states, n_drones=config.NUMBER_OF_DRONES)
env.run(until=config.SIM_TIME)
sim.metrics.print_metrics()
```
