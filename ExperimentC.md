# Experiment C: Time-Windowed Behavior Over 120s (DSDV vs Greedy vs QGeo vs CR-QGeo vs MACG)

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
| Protocols compared | DSDV, Greedy, QGeo, CR-QGeo, MACG |
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
identically to all five protocols.

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
| **MACG** | 0-30s | 1447 | 1079 | 74.57 | 47.81 | 879.52 | 1.59 | 94 |
| MACG | 30-60s | 1453 | 776 | 63.97 | 1588.61 | 192.20 | 2.14 | 201 |
| MACG | 60-90s | 1446 | 781 | 60.65 | 1613.42 | 183.63 | 1.72 | 294 |
| MACG | 90-120s | 1517 | **1262** | 66.48 | 1266.48 | 394.57 | 2.35 | 130 |
| **QGeo** | 0-30s | 1447 | 1062 | 73.39 | 203.36 | 450.13 | 2.27 | 162 |
| QGeo | 30-60s | 1453 | 455 | 52.31 | 1204.59 | 111.85 | 1.85 | 140 |
| QGeo | 60-90s | 1446 | 396 | 44.02 | 1241.26 | 180.62 | 2.05 | 105 |
| QGeo | 90-120s | 1517 | 584 | 42.59 | 1753.27 | 142.42 | 2.27 | 72 |
| **CR-QGeo** | 0-30s | 1447 | 1042 | 72.01 | 209.72 | 384.41 | 2.41 | 145 |
| CR-QGeo | 30-60s | 1453 | 566 | 55.45 | 2069.95 | 88.71 | 2.16 | 209 |
| CR-QGeo | 60-90s | 1446 | 681 | 52.67 | 1906.92 | 99.13 | 2.10 | 181 |
| CR-QGeo | 90-120s | 1517 | 575 | 48.85 | 2413.32 | 79.78 | 2.42 | 190 |

**Overall (0-120s):** DSDV 25.96% PDR (1522/5863 delivered) · **Greedy 67.90% PDR (3981/5863)** · MACG 66.48% PDR
(3898/5863) · CR-QGeo 48.85% PDR (2864/5863) · QGeo 42.59% PDR (2497/5863).

## 3. Observations

- **DSDV collapses completely and does not recover.** Its cumulative PDR falls monotonically (76.57 → 52.48 →
  35.02 → 25.96%), and it delivers **zero packets in the last two windows** despite generating over 1400 new
  packets in each. Its collision count keeps climbing even as deliveries hit zero (88 → 275 → 470 → 400) — DSDV's
  periodic table-broadcast control traffic keeps flooding the channel indefinitely, so the network reaches a state
  where control overhead alone saturates the channel with zero useful throughput. This directly corroborates
  `ExperimentA.md`'s finding that DSDV's control overhead becomes counter-productive under sustained
  load/contention — here the same effect appears not from adding UAVs, but purely from running long enough for
  staleness and control traffic to accumulate.
- **Greedy is the most sustained-load-robust protocol**, ending at 67.90% cumulative PDR — more than double
  QGeo/CR-QGeo and 2.6× DSDV. It **recovers in the final window** (1249 delivered in 90-120s, its best window by
  far), which — combined with its collision counts staying low and roughly flat throughout (28/61/40/84) —
  suggests Greedy's per-hop, always-current-neighbor-table forwarding does not accumulate the kind of
  stale/compounding state that hurts DSDV, QGeo, and CR-QGeo over time.
- **MACG finishes a close second**, ending at 66.48% cumulative PDR — just 1.4 points behind Greedy and far ahead
  of CR-QGeo (48.85%), QGeo (42.59%), and DSDV (25.96%). It shows the same "dip then recover in the final window"
  shape as Greedy rather than DSDV's terminal collapse: cumulative PDR dips from 74.57% (0-30s) to 60.65% (60-90s)
  and then **recovers to 66.48%** in the final window — 1262 packets delivered in 90-120s alone, MACG's best
  window by a wide margin and, in raw count, even slightly higher than Greedy's own best window (1249). The
  mid-run dip coincides with a real delay spike (47.81 ms in 0-30s up to 1588-1613 ms in 30-90s, dropping back to
  1266 ms in 90-120s), consistent with active cluster churn (CHs, members, and gateways still re-forming/
  re-associating under mobility during this window — see the `re_associations`/`member_removals`/`gateway_changes`
  diagnostics in `routing/macg/macg_cluster_manager.py`) that stabilizes by the final window. Its collisions stay
  bounded throughout (94/201/294/130) rather than growing without limit like DSDV's, and its hop count is
  noticeably less stable across windows than Greedy's (1.59 → 2.14 → 1.72 → 2.35 vs Greedy's tighter
  1.42 → 1.77 → 1.41 → 1.88), reflecting the extra CH/gateway detour hops hierarchical routing sometimes takes.
- **QGeo degrades steadily and roughly levels off** (73.39 → 52.31 → 44.02 → 42.59% cumulative), settling into a
  moderate but stable operating point rather than collapsing (DSDV) or staying strong (Greedy/MACG).
- **CR-QGeo outperforms QGeo over the full 120s run.** CR-QGeo delivers more packets than QGeo in two of the three
  post-30s windows (566 vs 455 in 30-60s, 681 vs 396 in 60-90s) and ends with a clearly higher overall PDR (48.85%
  vs 42.59%). The trade-off is visible in the same data: CR-QGeo's **per-window average throughput is lower than
  QGeo's in every single window** (e.g. 88.71 vs 111.85 Kbps in 30-60s; 99.13 vs 180.62 Kbps in 60-90s) and its
  average E2E delay is consistently higher (e.g. 2069.95 vs 1204.59 ms in 30-60s), alongside a slightly higher hop
  count in most windows. This is a coherent signature: CR-QGeo's congestion penalty appears to route more traffic
  around locally-congested direct paths onto longer, less-contended alternate paths — each individual delivery is
  slower and less efficient, but more packets get through in total.

## 4. Why does the leading protocol win over a sustained run?

Greedy ends the 120-second run with the highest cumulative PDR (67.90%), and MACG — the protocol that comes
closest to matching it (66.48%) — shares the specific mechanism that separates both of them from the rest of the
field: **neither one depends on state that keeps degrading the longer the simulation runs.**

- **DSDV loses because its control-plane overhead compounds over time, not just over UAV count.** Every periodic
  table broadcast adds to a channel that never gets a chance to drain, and once contention crosses a threshold
  DSDV's own control traffic becomes the dominant thing occupying the channel — visible directly in its collision
  count climbing (88 → 275 → 470 → 400) precisely as its deliveries fall to zero. There is no mechanism in DSDV
  that reduces this overhead as conditions worsen; it broadcasts on a fixed schedule regardless of whether doing so
  is still productive, so a long enough run drives it to complete collapse.
- **QGeo and CR-QGeo lose because their Q-tables need continuous re-learning under mobility**, and every hop still
  carries a persistent exploration probability that produces avoidably long paths — a cost that a longer run does
  not amortize away the way it might if the exploration rate decayed over time.
- **Greedy wins because its forwarding decision carries no memory at all.** Every hop is decided fresh from the
  current neighbor table, so nothing accumulated in window 1 can go stale and hurt window 4 — the same property
  that makes it the most mobility-robust protocol in `ExperimentB.md`. Its low, flat control overhead (Hello
  broadcasts only) also means it never approaches the kind of self-inflicted channel saturation that sinks DSDV.
- **MACG wins almost as decisively, and for a related but distinct reason: its hierarchical forwarding is also
  recomputed fresh from local cluster-manager state at every hop**, never dependent on a slowly-propagating global
  table the way DSDV is. The one piece of state MACG does carry — cluster/CH/gateway membership — is exactly what
  produces the mid-run dip (windows 2-3), while that state is still forming and being re-negotiated as UAVs move;
  but once it stabilizes, MACG's final-window recovery (1262 delivered, its best window of the run, edging out even
  Greedy's own best window) shows that stabilized cluster state does not compound into worse performance the way
  DSDV's stale tables do — it simply took longer than a single 30-second snapshot for that state to settle. This is
  also why MACG's showing here (2nd of five, 1.4 points behind Greedy) is markedly stronger than its position in
  the single-30s snapshots in `ExperimentA.md`/`ExperimentB.md` (typically 3rd of five at this UAV count): a sweep
  that ends the moment a protocol's setup cost has been paid, before that cost has had time to earn a return,
  understates exactly the protocols — MACG here, CR-QGeo in its own way — whose design trades a slower start for
  better sustained behavior.

## 5. Interpretation

The central result of this experiment is that **duration matters, and it matters differently per protocol**: DSDV
looks strong early but collapses to worst by 120s as its control-plane overhead saturates the channel; Greedy is
consistently strong and even self-recovers in the final window; MACG follows Greedy's same dip-then-recover pattern
and finishes a close second overall, a much stronger relative showing than its 30-second snapshots in
`ExperimentA.md`/`ExperimentB.md` would suggest; QGeo degrades steadily and plateaus; and CR-QGeo, despite trailing
QGeo in the first 30 seconds, pulls ahead of it cumulatively by 120s, consistent with its congestion-awareness
needing time to pay off. This is a single-seed run and the specific numbers should not be over-generalized, but the
qualitative pattern — CR-QGeo overtaking QGeo, and MACG closing most of the gap to Greedy, given enough sustained
operation — is exactly the kind of scenario where congestion/reliability-aware and clustering-aware routing have
the most opportunity to matter, relative to a single short snapshot.

## 6. Reproduction

```python
from utils import config
config.ROUTING_PROTOCOL = "macg"         # "dsdv" / "greedy" / "qgeo" / "cr_qgeo" / "macg"
config.SIM_TIME = 120 * 1e6
config.INITIAL_ENERGY = 200_000          # see Section 1 note (this happens to already be today's config default)

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
