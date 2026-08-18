# Experiments A & B (120s rerun) — Summary

Full setup, tables, and per-experiment analysis are in `ExperimentA_120s.md` and `ExperimentB_120s.md`. This
summarizes both: **Experiment A** — scalability under sustained fixed-per-UAV offered load (UAV count
10/20/50/100, fixed 10 m/s, fixed 600×600m map, 120s); **Experiment B** — mobility robustness under sustained,
energy-neutralized operation (speed 10/20/30/40 m/s, fixed 10 UAVs, 120s, `INITIAL_ENERGY`=5,000,000 J so no
UAV ever runs out of energy). Both rerun the corresponding 30-second experiments (`ExperimentA.md`,
`ExperimentB.md`) at 120s, seed 2025, all 5 protocols (DSDV, Greedy, QGeo, CR-QGeo, MACG), because
`ExperimentC.md` showed a 30-second snapshot hides real sustained-load behavior.

## 1. Compact per-tier table

| Experiment | Tier | Best PDR | Lowest E2E Delay* | Lowest Collisions | Best Throughput* | Notable |
|---|---|---|---|---|---|---|
| A | n=10 | Greedy (67.90%) | DSDV (228ms) | Greedy (213) | DSDV (1164 Kbps) | DSDV collapses by window 3 |
| A | n=20 | Greedy (55.06%) | DSDV (71ms) | Greedy (2864) | DSDV (766 Kbps) | DSDV near-dead by window 2 |
| A | n=50 | Greedy (19.46%) | DSDV (4059ms) | MACG (29,076) | DSDV (19 Kbps) | DSDV dead from window 2 on |
| A | n=100 | **MACG (10.37%)** | DSDV (4260ms) | Greedy (146,022) | DSDV (10 Kbps) | MACG overtakes Greedy — the one density-driven ranking flip |
| B | 10 m/s | Greedy (67.90%) | DSDV (228ms) | Greedy (213) | DSDV (1164 Kbps) | Same scenario as A n=10 (identical seed/params) |
| B | 20 m/s | Greedy (77.28%) | DSDV (326ms) | MACG (182) | DSDV (1065 Kbps) | Greedy's *best* tier of the whole sweep; MACG's *worst* (23.30%) |
| B | 30 m/s | Greedy (66.45%) | DSDV (468ms) | QGeo (114) | DSDV (1031 Kbps) | DSDV dead from window 3 on |
| B | 40 m/s | Greedy (43.97%) | DSDV (392ms) | Greedy (175) | DSDV (1055 Kbps) | DSDV's worst tier — dead from window 2 on |

*DSDV's "lowest delay" / "best throughput" wins are a statistical artifact of averaging over only the handful
of packets it delivers (nearly all in window 1, before its own control flooding kills the channel) — not a
sign it performs well. See each report's caveats section.

## 2. Experiment A: scalability under sustained fixed-per-UAV offered load

Greedy wins outright at n=10/20/50; **MACG overtakes it at n=100** (10.37% vs 3.11%, more than 3×), the one
ranking flip in the sweep. DSDV wins nothing at 120s — it collapses to worst-of-five by n=50 and stays there,
driven by control-traffic flooding that gets more severe, and sets in faster, as density increases (n=100:
3,479,837 collisions, dead after window 1). QGeo and CR-QGeo are the two weakest protocols at every density,
both under 1% PDR by n=100. Full mechanism discussion: `ExperimentA_120s.md` §13.

## 3. Experiment B: mobility robustness under sustained, energy-neutralized operation

Greedy wins **all four** speed tiers outright, non-monotonically (its best tier is actually 20 m/s, not 10 m/s).
DSDV is worst-of-five at every speed and collapses fastest at higher speed (dead after window 1 at 40 m/s vs.
window 3 at 10 m/s) — mobility-driven topology churn compounds with its duration-driven control-flooding
collapse. MACG has a distinct, reproducible weak spot at 20 m/s (23.30%, its worst tier) that does not appear
at 30-40 m/s — the same non-monotonic dip the old 30s sweep found, unchanged in shape at 120s. CR-QGeo beats
QGeo at 3 of 4 speeds at 120s (a reversal from the 30s sweep, where neither consistently won), consistent with
`ExperimentC.md`'s finding that CR-QGeo's congestion-aware reward needs sustained time to pay off. Full
mechanism discussion: `ExperimentB_120s.md` §13.

## 4. Comparison with the previous 30-second conclusions

- **DSDV: every tier it won at 30s, it loses at 120s.** It won n=10 in `ExperimentA.md` (92.84%, though that
  run only had ~16s of genuinely active time — see `ExperimentA_120s.md` §14) and was competitive/near-tied at
  10 m/s in `ExperimentB.md`; at 120s it is worst-of-five at every tier in both experiments. This is the
  clearest, most consistent 30s→120s ranking flip across both experiments, and it directly confirms
  `ExperimentC.md`'s single-tier finding now holds across the full density *and* speed ranges, not just the one
  scenario it was originally observed in.
- **MACG's n=100 win survives the correction unchanged** (it won n=100 in the old, energy/duration-confounded
  30s sweep too, at 14.75%, and still wins at 120s, now at 10.37%) — the strongest evidence in this whole study
  that MACG's clustering design genuinely pays off at high density, not an artifact of either experiment's
  methodology.
- **MACG's 20 m/s weak spot also survives unchanged** — present in both the 30s and 120s versions of Experiment
  B, in the same shape (worst-of-five at 20 m/s, recovering at 30-40 m/s).
- **CR-QGeo vs. QGeo flips from "no consistent winner" (30s) to "CR-QGeo wins 3 of 4 speed tiers" (120s)** —
  a genuinely new finding only visible at sustained duration, consistent with `ExperimentC.md`'s hypothesis
  that CR-QGeo's congestion-aware reward needs time to redirect traffic.
- **Greedy's dominance strengthens** in both experiments: at 30s it shared the lead with DSDV at low density/low
  speed; at 120s it either wins outright everywhere (Experiment B) or loses only the single highest-density tier
  to MACG (Experiment A).

## 5. Cases where extending 30s→120s changes the ranking

1. **Experiment A, n=10:** DSDV (1st at ~16s-active-30s) → Greedy (1st at 120s), DSDV falls to worst-of-five.
2. **Experiment A, n=20/50/100:** DSDV falls from competitive/2nd-tier to worst-of-five at every one of these
   tiers as well (it was already weak at 30s here, but 120s makes the collapse total — 0% PDR in 3 of 4 windows
   at n=50 and n=100).
3. **Experiment B, all four speeds:** DSDV falls from competitive-or-winning at 10 m/s (30s) to worst-of-five
   at every speed (120s).
4. **Experiment B, CR-QGeo vs QGeo:** no consistent winner (30s) → CR-QGeo wins 3 of 4 tiers (120s).
5. **Experiment A, n=100 (MACG vs Greedy) and Experiment B, MACG's 20 m/s dip: unchanged** — these are the two
   findings that hold steady across the 30s→120s extension, which strengthens confidence they reflect real
   protocol properties rather than snapshot artifacts.

## 6. Caveats

- Single-seed (2025) throughout; no statistical confidence claims.
- Experiment A's n=100 tier was run in a separate later pass from the rest of the matrix because DSDV alone
  took 8.13 hours there (vs. 2.7-3.0 hours for the other four protocols) — see `ExperimentA_120s.md` §15 for
  the full timing breakdown and why this doesn't affect comparability.
- Collisions/control-packets/MAC-delay are attributed to time windows via checkpoint-diffing of existing
  simulator counters, not per-event timestamps — see `ExperimentB_120s.md` §15.
- No routing-protocol parameter was tuned in response to any result in either experiment.

## 7. Files produced

- `ExperimentA_120s.md`, `ExperimentB_120s.md` — full setup, tables, mechanism analysis
- `ExperimentAB_120s_Summary.md` — this file
- `results/120s/ExperimentA_120s.{csv,json}`, `results/120s/ExperimentB_120s.{csv,json}` — aggregated raw data
- `results/120s/<scenario_id>/result.json` — one raw result file per of the 40 scenarios
- `tools/run_scenario.py`, `tools/orchestrator.py`, `tools/build_reports.py` — the experiment-runner
  infrastructure built for this rerun (see either report's final section for exact commands)
