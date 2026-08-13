# Experiment Summary: DSDV vs Greedy vs QGeo vs CR-QGeo Across UAV Count, Speed, and Duration

This summarizes three config-sweep experiments run on top of the existing single-scenario comparison in
`PROTOCOL_COMPARISON_REPORT.md`. Full setup, tables, and per-experiment analysis are in `ExperimentA.md`,
`ExperimentB.md`, and `ExperimentC.md`. All runs use seed 2025 and, unless swept, the same defaults as
`PROTOCOL_COMPARISON_REPORT.md` (10 UAVs, 10 m/s, 600×600×100 m map, Poisson traffic at 5 pkt/s/UAV).

- **Experiment A** — sweep UAV count (10 / 20 / 50 / 100) at fixed 10 m/s, 30 s.
- **Experiment B** — sweep mobility speed (10 / 20 / 30 / 40 m/s) at fixed 10 UAVs, 30 s.
- **Experiment C** — one continuous 120 s run at fixed 10 UAVs / 10 m/s, metrics binned into four 30 s windows.

## 1. Energy configuration note

A UAV's flight power at 10 m/s under this simulator's rotary-wing power model is ≈1104 W. The simulator's default
energy budget (`INITIAL_ENERGY=20,000 J`, with a 2,000 J reserve before a drone is put to permanent sleep and stops
generating/relaying packets for the rest of the run) only covers about 16 seconds of continuous flight. Experiment
C requires 120 seconds of genuinely continuous operation to produce meaningful time-windowed data, so
`INITIAL_ENERGY` was raised to 200,000 J (≈179 s of flight time at 10 m/s) for that experiment, applied identically
across all four protocols. Experiment B's mobility-speed sweep reports two energy configurations (both documented
in `ExperimentB.md`): the default 20,000 J budget, whose active-flight duration varies non-monotonically with speed
because flight power is a non-monotonic function of speed under this power model; and a 5,000,000 J budget that
removes that duration effect to isolate the pure mobility effect. Experiment A does not need any energy adjustment,
since all four UAV-count tiers share the same fixed 30 s / 10 m/s energy budget.

## 2. Experiment A — UAV count (10/20/50/100 @ 10 m/s, 30s)

| n_drones | Best PDR | Best (lowest) collisions | Notable |
|---|---|---|---|
| 10 | DSDV (92.84%) | DSDV (6) | Baseline, low contention |
| 20 | Greedy (79.52%) | Greedy (924) | DSDV's PDR falls off a cliff (50.22%) |
| 50 | Greedy (31.46%) | Greedy (6211) | QGeo/CR-QGeo collapse to ~3% |
| 100 | DSDV (11.31%, barely) | Greedy (24290) | DSDV's own control flooding causes *more* collisions than anyone (66796) |

**Takeaway:** with a fixed map size, increasing UAV count is really increasing channel contention, and no protocol
holds up — but the *ranking* flips. DSDV wins at low density and becomes the worst-behaved protocol (via its own
control-packet flooding) at high density; Greedy, with minimal control overhead, is the most robust across the
sweep; QGeo and CR-QGeo — whose next-hop selection keeps a persistent random-exploration component and produces
longer paths — degrade the fastest and collapse hardest at high density. CR-QGeo tracks QGeo closely at every
density with no consistent advantage in this single-seed sweep.

## 3. Experiment B — mobility speed (10/20/30/40 m/s @ 10 UAVs, 30s, energy-neutralized)

| Speed | Best PDR | Notable |
|---|---|---|
| 10 m/s | DSDV (76.57%) | DSDV and Greedy essentially tied |
| 20 m/s | Greedy (67.17%) | DSDV drops sharply (42.29%) |
| 30 m/s | Greedy (56.67%) | DSDV keeps falling (42.09%) |
| 40 m/s | Greedy (54.04%) | DSDV worst of the four (34.55%) |

**Takeaway:** with the energy-neutralized configuration, PDR degrades monotonically with speed for every protocol,
as expected. Greedy overtakes DSDV as speed increases and is the most mobility-robust protocol overall — its
always-forward-to-current-nearest-neighbor design has no stale multi-hop state to protect, unlike DSDV's
periodically-refreshed tables. QGeo and CR-QGeo remain the two weakest protocols at every speed; no consistent
ordering between them emerges as a function of speed in this single-seed sweep.

## 4. Experiment C — sustained 120s operation (10 UAVs @ 10 m/s, INITIAL_ENERGY=200,000 J)

| Protocol | Overall 120s PDR | Trajectory |
|---|---|---|
| DSDV | 25.96% | Collapses: 76.6% → 52.5% → 35.0% → 26.0% cumulative; **zero** deliveries in the last two windows despite continuing to generate control traffic that saturates the channel |
| **Greedy** | **67.90%** | Most robust: dips mid-run then **recovers** in the final window (its single best window of the whole run) |
| QGeo | 42.59% | Degrades steadily, then plateaus (73.4% → 52.3% → 44.0% → 42.6%) |
| CR-QGeo | 48.85% | Starts behind QGeo (72.0% vs 73.4% in 0-30s) but **overtakes it** by 120s (48.85% vs 42.59% overall) |

**Takeaway:** duration changes the ranking entirely from what a 30-second snapshot shows. DSDV looks best at 30s
and is worst by 120s. Greedy is the standout for sustained operation. Most notably for this task's purpose:
**CR-QGeo overtakes QGeo when given enough time to operate** — it delivers more packets in 2 of the 3 post-30s
windows, at the cost of consistently lower per-packet throughput and higher per-packet delay (its congestion
penalty appears to route traffic onto longer, less-congested paths — more packets get through overall, each one
somewhat slower). This is the opposite ranking from the single 30-second comparison in
`PROTOCOL_COMPARISON_REPORT.md` Part 2 and from Experiment A's n=10 tier, where CR-QGeo trailed QGeo slightly.

## 5. Overall conclusions

1. **No single protocol wins everywhere.** DSDV excels only in the light-load, short-duration regime and fails
   badly under density and sustained duration (control-overhead flooding). Greedy is the most consistently robust
   protocol across density, speed, and duration in this single-seed testing. QGeo and CR-QGeo are the weakest
   protocols under density and speed stress, but CR-QGeo is the only one of the four whose relative ranking
   *improves* with longer operation.
2. **CR-QGeo vs. QGeo specifically:** across a 30-second snapshot (`PROTOCOL_COMPARISON_REPORT.md` Part 2, and
   Experiment A's n=10 tier), CR-QGeo trails QGeo slightly. Across UAV-count and speed sweeps at 30s, the two track
   each other closely with no consistent winner. But over a genuinely sustained 120-second run, CR-QGeo delivers
   ~15% more traffic overall than QGeo (48.85% vs 42.59% PDR), trading lower per-packet throughput/higher
   per-packet delay for a higher aggregate delivery ratio — consistent with the congestion-aware reward mechanism
   needing time to accumulate enough Q-table experience to redirect traffic away from congested paths. This is a
   single-seed result and should not be treated as conclusive, but it is evidence that CR-QGeo's core hypothesis
   (congestion/reliability-awareness pays off under sustained load) holds in at least one scenario.

## 6. Caveats

- All results are **single-seed (2025)**; no statistical confidence claims are made. Multiple seeds would be needed
  to confirm any of the rankings above are not run-specific noise, especially the closer margins (e.g. CR-QGeo vs
  QGeo in Experiment A/B).
- Experiment A holds map size fixed while increasing UAV count, so "UAV count" here really means "channel density
  on a fixed-size channel," not "larger deployment area." A map-size-scaled variant would isolate pure network-size
  effects from contention effects.
- No simulator parameter or CR-QGeo weight was tuned in response to seeing routing-protocol results, per the
  research guardrail from the original CR-QGeo task. `INITIAL_ENERGY` is the one exception, and it was raised for a
  different reason: so drones do not exhaust their flight energy mid-run and prematurely stop participating,
  which would otherwise confound Experiment B's speed sweep and make Experiment C's later time windows empty. It is
  applied identically across every protocol compared in each experiment, so it does not bias the comparison between
  protocols — full details in `ExperimentB.md` §4 and `ExperimentC.md` §1.

## 7. Files produced

- `ExperimentA.md` — UAV count sweep, full tables and analysis
- `ExperimentB.md` — mobility speed sweep, as-collected + energy-neutralized tables and analysis
- `ExperimentC.md` — 120s time-windowed run, full tables and analysis
- `Experiment.md` — this summary

## 8. Code changes made to support these experiments

- `utils/config.py`: added `DRONE_SPEED = 10` (new tunable; previously the homogeneous-case speed was hardcoded).
- `simulator/simulator.py`: the one hardcoded `speed = 10` line in the homogeneous-case branch now reads
  `speed = config.DRONE_SPEED`. No other change to this file.
- `utils/config.py`: `INITIAL_ENERGY` set to `200 * 1e3` (200,000 J), up from the out-of-the-box default of
  `20 * 1e3` (20,000 J), so drones have enough flight energy to remain active for the full duration of these
  experiments (see Section 1). Applied identically across all protocols compared.
- No changes to `routing/`, `energy/`, `mobility/`, `mac/`, `phy/`, or any other guarded module — only the
  `config.py` constants they read from were touched.
