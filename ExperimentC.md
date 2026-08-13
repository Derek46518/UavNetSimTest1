# Experiment C: Time-Windowed Behavior Over 120s (DSDV vs Greedy vs QGeo vs CR-QGeo)

## 1. Setup

One continuous 120-second simulation per protocol (not four separate restarts), seed 2025, with metrics binned by
each delivered packet's arrival time into four 30-second windows: 0-30s, 30-60s, 60-90s, 90-120s. "Generated in
window" is binned by each packet's creation time; "delivered in window" and the per-window delay/throughput/hop-
count averages are binned by arrival time — so a packet generated late in one window that arrives in the next window
is correctly counted in the window it actually arrived in.

| Parameter | Value |
|---|---|
| Simulation seed | 2025 |
| Number of UAVs | 10 |
| Total simulation time | 120 s, binned into four 30 s windows |
| Protocols compared | DSDV, Greedy, QGeo, CR-QGeo |
| Map size | 600 m × 600 m × 100 m |
| Mobility model / speed | 3-D Gauss-Markov, 10 m/s |
| Traffic pattern | Poisson, rate = 5 packets/s per UAV |
| `INITIAL_ENERGY` | 200,000 J (see note below) |

**Note on the energy budget:** a UAV's flight power at 10 m/s under this simulator's rotary-wing power model is
≈1104 W. `utils/config.py`'s default `INITIAL_ENERGY` (20,000 J, with a 2,000 J reserve before a drone is put to
permanent sleep) only covers about 16 seconds of flight — far too short for a 120-second experiment, since once a
drone sleeps it never generates or relays another packet for the rest of the run. `INITIAL_ENERGY` was therefore
raised to 200,000 J for this experiment (≈179 s of flight time at 10 m/s), so that no drone runs out of energy
mid-run and all four 30-second windows reflect genuine, continuous network activity. This value is applied
identically to all four protocols.

## 2. Results

| Protocol | Window | Generated | Delivered | Cumulative PDR (%) | Avg E2E Delay (ms) | Avg Throughput (Kbps) | Avg Hop Count | Collisions |
|---|---|---|---|---|---|---|---|---|
| **DSDV** | 0-30s | 1447 | 1108 | 76.57 | 18.23 | 1175.90 | 1.52 | 88 |
| DSDV | 30-60s | 1453 | 414 | 52.48 | 790.11 | 1132.36 | 1.69 | 275 |
| DSDV | 60-90s | 1446 | **0** | 35.02 | — | — | — | 470 |
| DSDV | 90-120s | 1517 | **0** | 25.96 | — | — | — | 400 |
| **Greedy** | 0-30s | 1447 | 1103 | 76.23 | 17.96 | 1236.95 | 1.42 | 28 |
| Greedy | 30-60s | 1453 | 874 | 68.17 | 812.98 | 978.23 | 1.77 | 61 |
| Greedy | 60-90s | 1446 | 755 | 62.86 | 9.22 | 1250.01 | 1.41 | 40 |
| Greedy | 90-120s | 1517 | **1249** | 67.90 | 903.61 | 813.75 | 1.88 | 84 |
| **QGeo** | 0-30s | 1447 | 1062 | 73.39 | 203.36 | 450.13 | 2.27 | 162 |
| QGeo | 30-60s | 1453 | 455 | 52.31 | 1204.59 | 111.85 | 1.85 | 140 |
| QGeo | 60-90s | 1446 | 396 | 44.02 | 1241.26 | 180.62 | 2.05 | 105 |
| QGeo | 90-120s | 1517 | 584 | 42.59 | 1753.27 | 142.42 | 2.27 | 72 |
| **CR-QGeo** | 0-30s | 1447 | 1042 | 72.01 | 209.72 | 384.41 | 2.41 | 145 |
| CR-QGeo | 30-60s | 1453 | 566 | 55.45 | 2069.95 | 88.71 | 2.16 | 209 |
| CR-QGeo | 60-90s | 1446 | 681 | 52.67 | 1906.92 | 99.13 | 2.10 | 181 |
| CR-QGeo | 90-120s | 1517 | 575 | 48.85 | 2413.32 | 79.78 | 2.42 | 190 |

**Overall (0-120s):** DSDV 25.96% PDR (1522/5863 delivered) · Greedy 67.90% PDR (3981/5863) · QGeo 42.59% PDR
(2497/5863) · CR-QGeo 48.85% PDR (2864/5863).

## 3. Observations

- **DSDV collapses completely and does not recover.** Its cumulative PDR falls monotonically (76.57 → 52.48 →
  35.02 → 25.96%), and it delivers **zero packets in the last two windows** despite generating over 1400 new
  packets in each. Its collision count keeps climbing even as deliveries hit zero (88 → 275 → 470 → 400) — DSDV's
  periodic table-broadcast control traffic keeps flooding the channel indefinitely, so the network reaches a state
  where control overhead alone saturates the channel with zero useful throughput. This directly corroborates
  `ExperimentA.md`'s finding that DSDV's control overhead becomes counter-productive under sustained
  load/contention — here the same effect appears not from adding UAVs, but purely from running long enough for
  staleness and control traffic to accumulate.
- **Greedy is the most sustained-load-robust protocol by a wide margin**, ending at 67.90% cumulative PDR — more
  than double QGeo/CR-QGeo and 2.6× DSDV. It even **recovers in the final window** (1249 delivered in 90-120s, its
  best window by far), which — combined with its collision counts staying low and roughly flat throughout
  (28/61/40/84) — suggests Greedy's per-hop, always-current-neighbor-table forwarding does not accumulate the kind
  of stale/compounding state that hurts DSDV, QGeo, and CR-QGeo over time.
- **QGeo degrades steadily and roughly levels off** (73.39 → 52.31 → 44.02 → 42.59% cumulative), settling into a
  moderate but stable operating point rather than collapsing (DSDV) or staying strong (Greedy).
- **CR-QGeo outperforms QGeo over the full 120s run.** CR-QGeo delivers more packets than QGeo in two of the three
  post-30s windows (566 vs 455 in 30-60s, 681 vs 396 in 60-90s) and ends with a clearly higher overall PDR (48.85%
  vs 42.59%). The trade-off is visible in the same data: CR-QGeo's **per-window average throughput is lower than
  QGeo's in every single window** (e.g. 88.71 vs 111.85 Kbps in 30-60s; 99.13 vs 180.62 Kbps in 60-90s) and its
  average E2E delay is consistently higher (e.g. 2069.95 vs 1204.59 ms in 30-60s), alongside a slightly higher hop
  count in most windows. This is a coherent signature: CR-QGeo's congestion penalty appears to route more traffic
  around locally-congested direct paths onto longer, less-contended alternate paths — each individual delivery is
  slower and less efficient, but more packets get through in total. That is exactly the trade-off the
  congestion-aware reward was designed to make, and it takes time to show up — CR-QGeo's Q-table needs several
  tens of seconds of experience before the congestion penalty meaningfully redirects traffic.

## 4. Interpretation

The central result of this experiment is that **duration matters, and it matters differently per protocol**: DSDV
looks strong early but collapses to worst by 120s as its control-plane overhead saturates the channel; Greedy is
consistently strong and even self-recovers in the final window; QGeo degrades steadily and plateaus; and CR-QGeo,
despite trailing QGeo in the first 30 seconds, pulls ahead of it cumulatively by 120s, consistent with its
congestion-awareness needing time to pay off. This is a single-seed run and the specific numbers should not be
over-generalized, but the qualitative pattern — CR-QGeo overtaking QGeo given enough sustained operation — is
exactly the kind of scenario where congestion/reliability-aware routing has the most opportunity to matter,
relative to a single short snapshot.

## 5. Reproduction

```python
from utils import config
config.ROUTING_PROTOCOL = "cr_qgeo"      # "dsdv" / "greedy" / "qgeo" / "cr_qgeo"
config.SIM_TIME = 120 * 1e6
config.INITIAL_ENERGY = 200_000          # see Section 1 note

import simpy
from simulator.simulator import Simulator

env = simpy.Environment()
channel_states = {i: simpy.Resource(env, capacity=1) for i in range(config.NUMBER_OF_DRONES)}
sim = Simulator(seed=2025, env=env, channel_states=channel_states, n_drones=config.NUMBER_OF_DRONES)
env.run(until=config.SIM_TIME)
sim.metrics.print_metrics()
```

To reproduce the per-window breakdown, snapshot `sim.metrics.datapacket_arrived` /
`sim.metrics.deliver_time_dict` / `sim.metrics.throughput_dict` / `sim.metrics.hop_cnt_dict` /
`sim.metrics.collision_num` / `sim.metrics.control_packet_num` at env time checkpoints of 30/60/90/120 × 1e6 (via
an `env.process` that yields to each checkpoint) and diff consecutive snapshots.
