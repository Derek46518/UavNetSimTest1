# Experiment Summary: DSDV vs Greedy vs QGeo vs CR-QGeo vs MACG Across UAV Count, Speed, Duration, and Map Size

This summarizes four config-sweep experiments comparing five routing protocols — DSDV, Greedy, QGeo, CR-QGeo, and
MACG (Mobility-Aware Clustered Greedy) — run on top of the existing single-scenario comparison in
`PROTOCOL_COMPARISON_REPORT.md`. Full setup, tables, and per-experiment analysis are in `ExperimentA.md`,
`ExperimentB.md`, `ExperimentC.md`, and `ExperimentD.md`. All runs use seed 2025 and, unless swept, the same
defaults as `PROTOCOL_COMPARISON_REPORT.md` (10 UAVs, 10 m/s, 600×600×100 m map, Poisson traffic at 5 pkt/s/UAV).

- **Experiment A** — sweep UAV count (10 / 20 / 50 / 100) at fixed 10 m/s, 30 s, fixed 600×600 m map.
- **Experiment B** — sweep mobility speed (10 / 20 / 30 / 40 m/s) at fixed 10 UAVs, 30 s, fixed 600×600 m map.
- **Experiment C** — one continuous 120 s run at fixed 10 UAVs / 10 m/s / 600×600 m, metrics binned into four
  30 s windows.
- **Experiment D** — sweep map size (300 / 600 / 900 / 1200 / 1600 m, square) at fixed 10 m/s, 120 s, at both
  10 and 50 UAVs.

## 1. Energy configuration note

A UAV's flight power at 10 m/s under this simulator's rotary-wing power model is ≈1104 W. The simulator's default
energy budget (`INITIAL_ENERGY=20,000 J`, with a 2,000 J reserve before a drone is put to permanent sleep and stops
generating/relaying packets for the rest of the run) only covers about 16 seconds of continuous flight — a limit
that is independent of map size, since flight power depends only on speed. Experiments C and D both require
genuinely continuous operation over 120 seconds to produce meaningful data, so `INITIAL_ENERGY` was raised to
200,000 J (≈179 s of flight time at 10 m/s) for both, applied identically across all five protocols; a first pass
at Experiment D run at the default 20,000 J confirmed the need for this directly — every map size produced the
exact same 754-packet generated count, the signature of every drone sleeping at the same ≈16.3 s mark regardless
of map size, which would have made the swept variable meaningless. Experiment B's mobility-speed sweep reports two
energy configurations (both documented in `ExperimentB.md`): the default 20,000 J budget, whose active-flight
duration varies non-monotonically with speed because flight power is a non-monotonic function of speed under this
power model; and a 5,000,000 J budget that removes that duration effect to isolate the pure mobility effect.
Experiment A does not need any energy adjustment, since all four UAV-count tiers share the same fixed 30 s / 10 m/s
energy budget, and it is pinned explicitly to 20,000 J for every protocol regardless of `utils/config.py`'s
present-day default (which has since changed to 200,000 J for unrelated reasons) so all five protocols are compared
under an identical, explicitly-controlled energy budget in every experiment — full detail in `ExperimentA.md` §1,
`ExperimentB.md` §1, and `ExperimentD.md` §1.

## 2. Experiment A — UAV count (10/20/50/100 @ 10 m/s, 30s)

| n_drones | Best PDR | Best (lowest) collisions | Notable |
|---|---|---|---|
| 10 | DSDV (92.84%) | DSDV (6) | Baseline, low contention; every other protocol trails DSDV/Greedy here |
| 20 | Greedy (79.52%) | Greedy (924) | DSDV's PDR falls off a cliff (50.22%) as its control traffic scales with n |
| 50 | Greedy (31.46%) | Greedy (6211) | QGeo/CR-QGeo collapse to ~3%; DSDV and MACG both close behind Greedy |
| 100 | MACG (14.75%) | Greedy (24290) | MACG overtakes both DSDV (11.31%) and Greedy (9.39%) as density crosses the point where hierarchical clustering starts to pay for itself |

**Takeaway:** with a fixed map size, increasing UAV count is really increasing channel contention, and no protocol
holds up for long — but the *ranking* changes twice across the sweep. DSDV wins at low density (its proactive
tables stay fresh and its control overhead is still cheap) and becomes one of the worst-behaved protocols (via its
own control-packet flooding) at high density. Greedy, with minimal and flat control overhead, takes over in the
middle of the sweep. QGeo and CR-QGeo — whose next-hop selection keeps a persistent random-exploration component
and produces longer paths — degrade the fastest and collapse hardest at every density; CR-QGeo tracks QGeo closely
with no consistent advantage in this single-seed sweep. MACG is uncompetitive at n=10/20 (its clustering handshake
overhead has no payoff on a small, lightly-loaded swarm) but becomes the single best-PDR protocol at n=100,
overtaking Greedy and DSDV exactly where the flat protocols' channel contention becomes severe enough for
hierarchical organization to start paying for itself — see `ExperimentA.md` §4 for the mechanism behind each
handover.

## 3. Experiment B — mobility speed (10/20/30/40 m/s @ 10 UAVs, 30s, energy-neutralized)

| Speed | Best PDR | Notable |
|---|---|---|
| 10 m/s | DSDV (76.57%) | DSDV and Greedy essentially tied; MACG close behind in 3rd (75.88%) |
| 20 m/s | Greedy (67.17%) | DSDV drops sharply (42.29%); MACG is last of five here (41.05%) |
| 30 m/s | Greedy (56.67%) | DSDV keeps falling (42.09%); MACG 2nd (49.83%), ahead of DSDV/QGeo/CR-QGeo |
| 40 m/s | Greedy (54.04%) | DSDV worst of the four original protocols (34.55%); MACG 2nd (50.17%) with the lowest delay of all five |

**Takeaway:** with the energy-neutralized configuration, PDR degrades monotonically with speed for DSDV, Greedy,
QGeo, and CR-QGeo, as expected. Greedy overtakes DSDV as speed increases and is the most mobility-robust protocol
on raw PDR — its always-forward-to-current-nearest-neighbor design has no stale multi-hop state to protect, unlike
DSDV's periodically-refreshed tables. QGeo and CR-QGeo remain the two weakest protocols at every speed; no
consistent ordering between them emerges as a function of speed in this single-seed sweep. MACG does not fit the
monotonic-degradation pattern: it is worst-of-five at 20 m/s but climbs to 2nd-of-five (ahead of DSDV, QGeo, and
CR-QGeo) at 30 and 40 m/s, and has the lowest average delay of all five protocols at those two higher speeds in
both the as-collected and energy-neutralized passes — see `ExperimentB.md` §6.

## 4. Experiment C — sustained 120s operation (10 UAVs @ 10 m/s, INITIAL_ENERGY=200,000 J)

| Protocol | Overall 120s PDR | Trajectory |
|---|---|---|
| DSDV | 25.96% | Collapses: 76.6% → 52.5% → 35.0% → 26.0% cumulative; **zero** deliveries in the last two windows despite continuing to generate control traffic that saturates the channel |
| **Greedy** | **67.90%** | Most robust: dips mid-run then **recovers** in the final window (its single best window of the whole run) |
| MACG | 66.48% | Close 2nd: dips mid-run (74.6% → 61.4% → 60.7%) then **recovers** to 66.5% in the final window (1262 delivered — even more than Greedy's own best window) |
| CR-QGeo | 48.85% | Starts behind QGeo (72.0% vs 73.4% in 0-30s) but **overtakes it** by 120s (48.85% vs 42.59% overall) |
| QGeo | 42.59% | Degrades steadily, then plateaus (73.4% → 52.3% → 44.0% → 42.6%) |

**Takeaway:** duration changes the ranking substantially from what a 30-second snapshot shows. DSDV looks best at
30s and is worst by 120s. Greedy is the standout for sustained operation, with MACG a close second — a much
stronger relative position than MACG holds in the single-30s Experiment A/B snapshots — mirroring Greedy's
dip-then-recover shape almost exactly rather than DSDV's terminal collapse. CR-QGeo overtakes QGeo when given
enough time to operate — it delivers more packets in 2 of the 3 post-30s windows, at the cost of consistently
lower per-packet throughput and higher per-packet delay (its congestion penalty appears to route traffic onto
longer, less-congested paths — more packets get through overall, each one somewhat slower). This is the opposite
ranking from the single 30-second comparison in `PROTOCOL_COMPARISON_REPORT.md` Part 2 and from Experiment A's
n=10 tier, where CR-QGeo trailed QGeo slightly.

## 5. Experiment D — map size (300/600/900/1200/1600 m @ 10 m/s, 120s, at n=10 and n=50)

| Tier | Best PDR | Notable |
|---|---|---|
| n=10, 300 m (densest) | DSDV (99.69%) | Near-complete graph, minimal churn — DSDV's best result across all four experiments |
| n=10, 600–1600 m | Greedy (67.90% → 19.68%) | MACG 2nd at 600–1200m; MACG becomes the single *worst* protocol at 1600m (8.80%) |
| n=50, 300 m (densest) | **MACG (38.66%)** | MACG's best result across all four experiments; DSDV's collisions hit 1.93 million at this tier |
| n=50, 600–1600 m | Greedy (19.46% → 5.30%) | MACG 2nd at every tier; DSDV's collisions stay catastrophic (588k–1.14M) throughout |

**Takeaway:** map size is really a second knob on the same variable Experiment A swept with UAV count — local
connectivity density — and MACG's win/lose boundary tracks that shared variable, not UAV count or map size
individually. MACG wins at the single densest tier reachable at each UAV count (n=50/300m rather than n=10/300m,
where DSDV's low-churn advantage still dominates), places 2nd across the connected-to-sparse middle of the sweep at
both UAV counts, and becomes the *worst* protocol of the five at the sparsest tier tested (n=10/1600m) — clustering
overhead with no local density to justify it. DSDV's opposite failure mode compounds with both density *and*
duration: its control-packet broadcast storm produces 588k–1.93M collisions at every n=50 tier over this
experiment's 120s window, far beyond anything seen in the 30s Experiment A sweep at the same UAV counts. Greedy
remains the most consistent protocol, winning 8 of the 10 (map size × UAV count) tiers tested — see
`ExperimentD.md` §4 for the mechanism behind each handover.

## 6. Why do the leading protocols win? A cross-experiment view

Each experiment file has its own detailed "why does the leader win" section (`ExperimentA.md` §4, `ExperimentB.md`
§6, `ExperimentC.md` §4, `ExperimentD.md` §4); the same handful of structural properties explain almost every
handover across all four:

- **Proactive, table-based routing (DSDV) wins only when the network is small, static enough, and short-lived
  enough that its tables stay fresh.** It has the shortest, most direct routes of any protocol when its control
  traffic can keep up with topology change — true at n=10 in Experiment A, at 10 m/s in Experiment B, and at the
  single densest/lowest-churn tier in Experiment D (n=10/300m, its best result in the entire study, 99.69% PDR) —
  but that same proactive control traffic scales with network size, duration, *and* sparsity-driven route
  staleness, so it becomes the single worst protocol whenever any of those push its update rate past what the
  channel can absorb (Experiment A n≥20, Experiment B speed≥20 m/s, Experiment C's final two windows, and every
  Experiment D tier except its one win — where, at n=50, its control-packet broadcast storm reaches 588k–1.93M
  collisions regardless of map size).
- **Stateless, per-hop routing (Greedy) wins across the widest range of conditions** because there is nothing in
  its next-hop decision that can go stale — no multi-hop route to protect, no Q-table to re-learn, no cluster
  membership to re-negotiate. That is why it holds the best or near-best PDR through most of the density sweep
  (Experiment A, n=20/50), the entire speed sweep from 20 m/s up (Experiment B), the full 120-second run
  (Experiment C), and 8 of the 10 tiers in the map-size sweep (Experiment D) — its control overhead is also the
  lowest and flattest of the five, so it contributes the least extra load whether the channel is congested by
  density (many UAVs, small map) or made unreliable by sparsity (few UAVs, large map).
- **Exploration-based learning (QGeo, CR-QGeo) rarely wins** because a persistent random-exploration component adds
  hops that are actively wrong under contention or mobility, and a Q-table takes real time to re-converge whenever
  the topology or congestion pattern shifts — a cost that shows up worst exactly when density or speed is high.
  CR-QGeo's congestion-aware reward is the one mechanism in this study whose benefit *grows* with time: it trails
  QGeo in every 30-second snapshot but overtakes it once given a genuinely sustained 120-second run (Experiment C),
  because redirecting traffic away from congested paths needs enough accumulated experience to pay off.
- **Hierarchical clustering (MACG) wins only where local connectivity density is high enough for clusters to form
  quickly and cheaply relative to the traffic they carry** — and it actively hurts once density drops below that
  threshold. At low density and short duration, MACG pays real control-packet cost (the clustering handshake) for
  no return, since Greedy can already reach anyone directly. But Experiments A and D together show this is a single
  underlying variable, not two separate effects: MACG wins at the highest density reached via more UAVs on a fixed
  map (Experiment A, n=100) *and* at the highest density reached via a smaller map at fixed UAV count
  (Experiment D, n=50/300m — its best result in the study, 38.66% PDR), places 2nd across the connected middle of
  both sweeps, climbs from worst- to second-of-five as mobility speed increases past 20 m/s while posting the
  lowest delay of any protocol (Experiment B), finishes a close second over a genuinely sustained run mirroring
  Greedy's dip-then-recover resilience (Experiment C) — and becomes the outright *worst* protocol tested at the
  sparsest tier reached (Experiment D, n=10/1600m, 8.80% PDR with more than triple any other protocol's routing
  load). All of this is one coherent story: clustering has a setup cost that only enough local density, or enough
  time, lets it recoup.

## 7. Overall conclusions

1. **No single protocol wins everywhere.** DSDV excels only in the light-load, short-duration, low-churn regime and
   fails badly under density, sparsity, or sustained duration (control-overhead flooding in every case). Greedy is
   the most consistently robust protocol across density, speed, duration, and map size in this single-seed testing,
   winning the plurality of tiers in every one of the four experiments. QGeo and CR-QGeo are the weakest protocols
   under density and speed stress. CR-QGeo and MACG are the two protocols whose relative ranking *improves* under
   some condition rather than only ever degrading — CR-QGeo with duration (Experiment C), MACG with local
   connectivity density (Experiments A and D) and, on delay, mobility speed (Experiment B).
2. **CR-QGeo vs. QGeo specifically:** across a 30-second snapshot (`PROTOCOL_COMPARISON_REPORT.md` Part 2, and
   Experiment A's n=10 tier), CR-QGeo trails QGeo slightly. Across UAV-count, speed, and map-size sweeps at 30–120s,
   the two mostly track each other closely with no consistent winner. But over a genuinely sustained 120-second run
   at fixed density (Experiment C), CR-QGeo delivers ~15% more traffic overall than QGeo (48.85% vs 42.59% PDR),
   trading lower per-packet throughput/higher per-packet delay for a higher aggregate delivery ratio — consistent
   with the congestion-aware reward mechanism needing time to accumulate enough Q-table experience to redirect
   traffic away from congested paths. This is a single-seed result and should not be treated as conclusive, but it
   is evidence that CR-QGeo's core hypothesis (congestion/reliability-awareness pays off under sustained load) holds
   in at least one scenario.
3. **MACG vs. flat routing specifically:** MACG is uncompetitive in every small-swarm, sparse, or short-snapshot
   condition tested — n=10/20 in Experiment A, most speeds in Experiment B, most map sizes in Experiment D — where
   local connectivity density is too low, or the run too short, for clustering to be worth its handshake overhead.
   But it wins outright at the highest density reached via either UAV count (Experiment A, n=100) or map size
   (Experiment D, n=50/300m), is 2nd-of-five at higher mobility speeds with the lowest delay of all five protocols
   (Experiment B), and is a close 2nd-of-five over a genuinely sustained run mirroring Greedy's dip-then-recover
   resilience (Experiment C). Experiment D adds the other half of the picture: at the sparsest tier reached
   (n=10/1600m), MACG is not merely uncompetitive but the single worst protocol tested, with by far the worst
   routing load of the five — confirming that clustering's cost is not always recoverable, only recoverable above
   some local-density threshold. This is a coherent, non-cherry-picked pattern across four independent sweeps: MACG
   loses in the regime its clustering design does not target (low density, short duration) and wins or nearly wins
   in the regimes it does target (high density from either direction, higher mobility, sustained duration).

## 8. Caveats

- All results are **single-seed (2025)**; no statistical confidence claims are made. Multiple seeds would be needed
  to confirm any of the rankings above are not run-specific noise, especially the closer margins (e.g. CR-QGeo vs
  QGeo in Experiment A/B, or MACG vs Greedy in Experiment C/D).
- Experiment A holds map size fixed while increasing UAV count, so "UAV count" there really means "channel density
  on a fixed-size channel," not "larger deployment area." Experiment D was run specifically to address this by
  varying map size independently, and confirms MACG's win condition is local connectivity density regardless of
  which of the two variables produces it — but only two UAV counts (10 and 50) were tested against five map sizes;
  intermediate UAV counts at the sparser map tiers would help confirm whether MACG's density threshold is a sharp
  cliff or a smooth crossover (see `ExperimentD.md` §5).
- No simulator parameter or routing-protocol weight/threshold was tuned in response to seeing results, per the
  research guardrail from the original CR-QGeo task, extended to every protocol added since. `INITIAL_ENERGY` is
  the one exception, and it was raised for a different reason: so drones do not exhaust their flight energy
  mid-run and prematurely stop participating, which would otherwise confound Experiment B's speed sweep and make
  Experiment C's and D's later time windows/tiers empty. It is applied identically across every protocol compared
  in each experiment, so it does not bias the comparison between protocols — full details in `ExperimentB.md` §4,
  `ExperimentC.md` §1, and `ExperimentD.md` §1. MACG's own timing constants, thresholds, and similarity weights
  (`MACG_*` in `utils/config.py`) were likewise never adjusted after seeing any of these experiment results — the
  values are exactly the Version-1 defaults from `SPECIFCATION3.md` §12/§47, fixed at implementation time.
- MACG's density-driven wins (Experiment A n=100, Experiment D n=50/300m) and its Experiment C sustained-run showing
  are each single scenarios; the 20-m/s dip in Experiment B (where MACG is worst-of-five) and the collapse to
  worst-of-five at Experiment D's sparsest tier show its behavior is not simply "more density/duration is always
  better" — there is a real failure mode (too sparse to cluster) alongside the success mode, and the exact boundary
  between them is not yet mapped precisely.

## 9. Files produced

- `ExperimentA.md` — UAV count sweep, full tables and analysis
- `ExperimentB.md` — mobility speed sweep, as-collected + energy-neutralized tables and analysis
- `ExperimentC.md` — 120s time-windowed run, full tables and analysis
- `ExperimentD.md` — map size sweep (at two UAV counts), full tables and analysis
- `Experiment.md` — this summary

## 10. Code changes made to support these experiments

- `utils/config.py`: added `DRONE_SPEED = 10` (new tunable; previously the homogeneous-case speed was hardcoded).
- `simulator/simulator.py`: the one hardcoded `speed = 10` line in the homogeneous-case branch now reads
  `speed = config.DRONE_SPEED`. No other change to this file.
- `utils/config.py`: `INITIAL_ENERGY` set to `200 * 1e3` (200,000 J), up from the out-of-the-box default of
  `20 * 1e3` (20,000 J), so drones have enough flight energy to remain active for the full duration of these
  experiments (see Section 1). Applied identically across all protocols compared.
- No changes to `routing/`, `energy/`, `mobility/`, `mac/`, `phy/`, or any other guarded module — only the
  `config.py` constants they read from were touched. MACG's own routing package (`routing/macg/`) and its entry in
  `entities/drone.py`'s routing selector already existed prior to these experiments; no further code changes were
  needed to include it, since every swept parameter across all four experiments (`NUMBER_OF_DRONES`, `DRONE_SPEED`,
  `INITIAL_ENERGY`, `SIM_TIME`, `MAP_LENGTH`/`MAP_WIDTH`) is a config constant every protocol, including MACG,
  already reads the same way. Experiment D needed no code changes at all — `MAP_LENGTH`/`MAP_WIDTH` were already
  ordinary config constants read fresh by the simulator at construction time.
