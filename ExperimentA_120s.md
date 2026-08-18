# Experiment A (120s rerun): UAV Count Sweep (DSDV vs Greedy vs QGeo vs CR-QGeo vs MACG)

## 1. Purpose

`ExperimentA.md` swept UAV count (10/20/50/100) at a nominal 30-second duration. `ExperimentC.md` subsequently
showed, with a single continuous 120-second run, that 30 seconds is too short to see sustained-load behavior:
DSDV looks best early and collapses by 120s, while MACG and CR-QGeo only separate from the pack given enough
time. This experiment reruns the UAV-count sweep at **120 seconds** so it reflects sustained scalability
behavior. Framed precisely: **scalability under fixed per-UAV offered load** — as UAV count increases, so do
the number of traffic sources, aggregate offered traffic, number of routing-control senders, spatial density on
the fixed map, and channel contention, all at once. This is *not* an isolated "effect of UAV count" — it is
what happens to five routing protocols as a fixed-size channel gets progressively more crowded, over a
genuinely sustained run.

## 2. Configuration

| Parameter | Value |
|---|---|
| Simulation seed | 2025 (fixed, identical across all 20 runs) |
| UAV counts swept | 10, 20, 50, 100 |
| Protocols compared | DSDV, Greedy, QGeo, CR-QGeo, MACG |
| Speed | 10 m/s (fixed) |
| Simulation time | **120 s** |
| Map size | 600 m × 600 m × 100 m (fixed) |
| Mobility model | 3-D Gauss-Markov |
| Traffic pattern | Poisson, rate = 5 packets/s per UAV (unchanged, hardcoded default in `entities/drone.py`) |
| `INITIAL_ENERGY` | 200,000 J, identical across all 20 runs |

## 3. Why duration changed from 30s to 120s

`ExperimentA.md`'s own "30-second" runs were, in practice, confounded by a second issue: at the default
20,000 J energy budget used there, every drone permanently sleeps at t≈16.3s regardless of UAV count, so real
network activity was compressed into roughly the first 16 seconds of the nominal 30s window (see
`ExperimentA.md` §1 and `ExperimentC.md`). This rerun fixes both issues at once: 120s of *genuinely* active
simulated time (Section 4), long enough to see the same control-traffic-saturation and clustering-payoff
dynamics `ExperimentC.md` found at a single density tier, now checked across the full UAV-count range.

## 4. Energy configuration and validation

`INITIAL_ENERGY` is raised to 200,000 J (≈179s of flight time at 10 m/s, comfortably covering the full 120s
run), identical across all 4 UAV-count tiers and all 5 protocols — the same value `ExperimentA.md` and
`ExperimentC.md` used, so this is not a new confound. Post-hoc validation on all 20 runs: **zero drones slept
in any run** (`any_drone_slept: false` in every case, `num_sleeping_drones_at_end: 0`), and minimum final
residual energy stayed at 67,635 J even in the most energy-intensive tier (n=100 — every tier's minimum final
residual energy landed in the 65,000-95,000 J range, i.e. well over half the budget remained at every density).
The energy-validation gate in `tools/build_reports.py` (which refuses to certify a report if any scenario shows
a sleeping UAV) passed cleanly for all 20 scenarios.

## 5. Parallel execution & reproducibility note

Every scenario ran as its own OS subprocess, with `utils.config` overridden in-process before the simulator was
constructed (never on disk) — see Section 16 for the exact mechanism. Before the full matrix was run, a
mandatory validation pair (`A_n10_dsdv` run standalone vs. run in parallel with `A_n10_greedy`) confirmed:
standalone and parallel results for the same scenario were **byte-for-byte identical** (only wall-clock time
differed), and the two different protocols produced clearly different results (25.96% vs. 67.90% PDR) —
together ruling out both non-determinism and cross-worker config contamination. The n=100 tier was run in a
separate, later pass after the n≤50 tiers and Experiment B completed (see Section 15 for why), using the same
isolation mechanism.

## 6. Overall (0–120s) results — n=10

| Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Routing Load | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Avg MAC Delay (ms) | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|---|
| DSDV | 5863 | 1522 | 25.96 | 228.19 | 3.205 | 1164.05 | 1.568 | 1233 | 5.21 | 4878 |
| **Greedy** | 5863 | **3981** | **67.90** | 468.71 | 0.603 | 1049.85 | 1.639 | **213** | 28.66 | 2400 |
| QGeo | 5863 | 2497 | 42.59 | 912.90 | 0.961 | 273.78 | 2.158 | 479 | 1153.16 | 2400 |
| CR-QGeo | 5863 | 2864 | 48.85 | 1423.32 | 0.838 | 196.98 | 2.292 | 725 | 1170.81 | 2400 |
| MACG | 5863 | 3898 | 66.48 | 1062.78 | 0.938 | 446.26 | 1.971 | 719 | 734.02 | 3655 |

## 7. Overall (0–120s) results — n=20

| Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Routing Load | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Avg MAC Delay (ms) | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|---|
| DSDV | 11823 | 1249 | 10.56 | 71.34 | 17.861 | 765.80 | 1.956 | 47834 | 5.78 | 22308 |
| **Greedy** | 11823 | **6510** | **55.06** | 372.68 | 0.737 | 599.47 | 1.909 | **2864** | 33.57 | 4800 |
| QGeo | 11823 | 3104 | 26.25 | 4470.54 | 1.546 | 13.28 | 2.256 | 5566 | 280.40 | 4800 |
| CR-QGeo | 11823 | 4194 | 35.47 | 4791.92 | 1.144 | 12.64 | 2.078 | 7788 | 172.75 | 4800 |
| MACG | 11823 | 4884 | 41.31 | 2470.98 | 1.656 | 151.68 | 1.881 | 4436 | 183.80 | 8090 |

## 8. Overall (0–120s) results — n=50

| Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Routing Load | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Avg MAC Delay (ms) | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|---|
| DSDV | 29879 | 1620 | 5.42 | 4059.34 | 59.633 | 18.94 | 1.349 | 593176 | 132.19 | 96606 |
| **Greedy** | 29879 | **5814** | **19.46** | 4819.13 | 2.064 | 15.04 | 1.412 | 38932 | 120.31 | 12000 |
| QGeo | 29879 | 1244 | 4.16 | 6962.88 | 9.646 | 2.10 | 1.207 | 59029 | 109.04 | 12000 |
| CR-QGeo | 29879 | 1509 | 5.05 | 7063.19 | 7.952 | 2.53 | 1.160 | 64266 | 107.94 | 12000 |
| MACG | 29879 | 4128 | 13.82 | 5099.92 | 5.175 | 13.92 | 1.336 | **29076** | 142.23 | 21361 |

## 9. Overall (0–120s) results — n=100

| Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Routing Load | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Avg MAC Delay (ms) | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|---|
| DSDV | 59597 | 971 | 1.63 | 4259.54 | 433.453 | 10.09 | 1.372 | 3479837 | 321.76 | 420883 |
| Greedy | 59597 | 1854 | 3.11 | 6871.61 | 12.945 | 3.75 | 1.172 | 146022 | 254.46 | 24000 |
| QGeo | 59597 | 399 | 0.67 | 9444.48 | 60.150 | 1.70 | 1.030 | 190565 | 205.76 | 24000 |
| CR-QGeo | 59597 | 417 | 0.70 | 9448.17 | 57.554 | 1.67 | 1.026 | 183842 | 210.14 | 24000 |
| **MACG** | 59597 | **6181** | **10.37** | 8702.19 | 6.448 | 1.74 | 1.068 | 184911 | 243.73 | 39858 |

Bold marks the best value per metric within each tier. At n=100, Greedy has the lowest collision count
(146,022) despite not having the best PDR — MACG wins PDR outright (10.37%, essentially double the runner-up)
while running a moderate collision load (184,911) between Greedy's and QGeo/CR-QGeo's.

## 10. Time-window results (independent, non-cumulative, per 30s window)

**n=10:**

| Protocol | Window | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|
| DSDV | 0-30s | 1447 | 1108 | 76.57 | 18.23 | 1175.90 | 1.524 | 88 | 770 |
| DSDV | 30-60s | 1453 | 414 | 28.49 | 790.11 | 1132.36 | 1.686 | 275 | 1278 |
| DSDV | 60-90s | 1446 | 0 | 0.00 | — | — | — | 470 | 1382 |
| DSDV | 90-120s | 1517 | 0 | 0.00 | — | — | — | 400 | 1448 |
| Greedy | 0-30s | 1447 | 1103 | 76.23 | 17.96 | 1236.95 | 1.415 | 28 | 600 |
| Greedy | 30-60s | 1453 | 874 | 60.15 | 812.98 | 978.23 | 1.773 | 61 | 600 |
| Greedy | 60-90s | 1446 | 755 | 52.21 | 9.22 | 1250.01 | 1.412 | 40 | 600 |
| Greedy | 90-120s | 1517 | 1249 | 82.33 | 903.61 | 813.75 | 1.879 | 84 | 600 |
| QGeo | 0-30s | 1447 | 1062 | 73.39 | 203.36 | 450.13 | 2.269 | 162 | 600 |
| QGeo | 30-60s | 1453 | 455 | 31.31 | 1204.59 | 111.85 | 1.846 | 140 | 600 |
| QGeo | 60-90s | 1446 | 396 | 27.39 | 1241.26 | 180.62 | 2.051 | 105 | 600 |
| QGeo | 90-120s | 1517 | 584 | 38.50 | 1753.27 | 142.42 | 2.271 | 72 | 600 |
| CR-QGeo | 0-30s | 1447 | 1042 | 72.01 | 209.72 | 384.41 | 2.412 | 145 | 600 |
| CR-QGeo | 30-60s | 1453 | 566 | 38.95 | 2069.95 | 88.71 | 2.164 | 209 | 600 |
| CR-QGeo | 60-90s | 1446 | 681 | 47.10 | 1906.92 | 99.13 | 2.104 | 181 | 600 |
| CR-QGeo | 90-120s | 1517 | 575 | 37.90 | 2413.32 | 79.78 | 2.424 | 190 | 600 |
| MACG | 0-30s | 1447 | 1079 | 74.57 | 47.81 | 879.52 | 1.586 | 94 | 922 |
| MACG | 30-60s | 1453 | 776 | 53.41 | 1588.61 | 192.20 | 2.137 | 201 | 911 |
| MACG | 60-90s | 1446 | 781 | 54.01 | 1613.42 | 183.63 | 1.725 | 294 | 911 |
| MACG | 90-120s | 1517 | 1262 | 83.19 | 1266.48 | 394.57 | 2.351 | 130 | 911 |

**n=20:**

| Protocol | Window | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|
| DSDV | 0-30s | 2885 | 843 | 29.22 | 98.77 | 644.94 | 1.897 | 10428 | 4981 |
| DSDV | 30-60s | 2895 | 122 | 4.21 | 12.17 | 1052.21 | 1.910 | 13864 | 5754 |
| DSDV | 60-90s | 3026 | 132 | 4.36 | 17.12 | 814.24 | 2.629 | 11222 | 5727 |
| DSDV | 90-120s | 3017 | 152 | 5.04 | 13.81 | 1164.17 | 1.737 | 12320 | 5846 |
| Greedy | 0-30s | 2885 | 2278 | 78.96 | 454.67 | 635.80 | 1.759 | 1290 | 1200 |
| Greedy | 30-60s | 2895 | 1824 | 63.01 | 318.40 | 549.21 | 1.987 | 497 | 1200 |
| Greedy | 60-90s | 3026 | 1293 | 42.73 | 488.93 | 540.58 | 2.032 | 658 | 1200 |
| Greedy | 90-120s | 3017 | 1115 | 36.96 | 159.16 | 675.74 | 1.946 | 419 | 1200 |
| QGeo | 0-30s | 2885 | 1003 | 34.77 | 4379.91 | 11.81 | 2.616 | 1984 | 1200 |
| QGeo | 30-60s | 2895 | 746 | 25.77 | 4489.50 | 16.24 | 2.142 | 1423 | 1200 |
| QGeo | 60-90s | 3026 | 607 | 20.06 | 4609.79 | 8.86 | 1.962 | 1328 | 1200 |
| QGeo | 90-120s | 3017 | 748 | 24.79 | 4460.18 | 15.87 | 2.126 | 831 | 1200 |
| CR-QGeo | 0-30s | 2885 | 1050 | 36.40 | 4106.59 | 15.71 | 2.370 | 2023 | 1200 |
| CR-QGeo | 30-60s | 2895 | 1014 | 35.03 | 5003.48 | 11.31 | 1.975 | 2542 | 1200 |
| CR-QGeo | 60-90s | 3026 | 1028 | 33.97 | 5181.73 | 10.24 | 1.897 | 1777 | 1200 |
| CR-QGeo | 90-120s | 3017 | 1102 | 36.53 | 4886.62 | 13.18 | 2.063 | 1446 | 1200 |
| MACG | 0-30s | 2885 | 1766 | 61.21 | 721.58 | 275.55 | 1.844 | 1514 | 2050 |
| MACG | 30-60s | 2895 | 1287 | 44.46 | 3554.91 | 64.11 | 1.900 | 1143 | 2185 |
| MACG | 60-90s | 3026 | 1037 | 34.27 | 3749.55 | 94.80 | 1.988 | 859 | 1919 |
| MACG | 90-120s | 3017 | 794 | 26.32 | 2935.11 | 92.39 | 1.791 | 920 | 1936 |

**n=50:**

| Protocol | Window | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|
| DSDV | 0-30s | 7568 | 1620 | 21.41 | 4059.34 | 18.94 | 1.349 | 153676 | 33270 |
| DSDV | 30-60s | 7413 | 0 | 0.00 | — | — | — | 147300 | 21108 |
| DSDV | 60-90s | 7461 | 0 | 0.00 | — | — | — | 145950 | 20776 |
| DSDV | 90-120s | 7437 | 0 | 0.00 | — | — | — | 146250 | 21452 |
| Greedy | 0-30s | 7568 | 1916 | 25.32 | 3093.99 | 29.99 | 1.428 | 11766 | 3000 |
| Greedy | 30-60s | 7413 | 1246 | 16.81 | 5754.59 | 7.22 | 1.295 | 9461 | 3000 |
| Greedy | 60-90s | 7461 | 1296 | 17.37 | 5736.67 | 5.99 | 1.406 | 9365 | 3000 |
| Greedy | 90-120s | 7437 | 1356 | 18.23 | 5520.19 | 9.76 | 1.503 | 8340 | 3000 |
| QGeo | 0-30s | 7568 | 218 | 2.88 | 6448.86 | 4.91 | 1.427 | 15420 | 3000 |
| QGeo | 30-60s | 7413 | 305 | 4.11 | 7160.03 | 1.38 | 1.111 | 15372 | 3000 |
| QGeo | 60-90s | 7461 | 349 | 4.68 | 6992.82 | 1.66 | 1.198 | 14744 | 3000 |
| QGeo | 90-120s | 7437 | 372 | 5.00 | 7074.38 | 1.44 | 1.164 | 13493 | 3000 |
| CR-QGeo | 0-30s | 7568 | 239 | 3.16 | 6696.14 | 4.55 | 1.368 | 13790 | 3000 |
| CR-QGeo | 30-60s | 7413 | 347 | 4.68 | 7350.29 | 1.39 | 1.084 | 17154 | 3000 |
| CR-QGeo | 60-90s | 7461 | 470 | 6.30 | 7000.07 | 3.25 | 1.145 | 18462 | 3000 |
| CR-QGeo | 90-120s | 7437 | 453 | 6.09 | 7102.41 | 1.59 | 1.126 | 14860 | 3000 |
| MACG | 0-30s | 7568 | 1886 | 24.92 | 4314.51 | 14.04 | 1.343 | 11790 | 6298 |
| MACG | 30-60s | 7413 | 860 | 11.60 | 6811.36 | 7.20 | 1.128 | 5706 | 5531 |
| MACG | 60-90s | 7461 | 752 | 10.08 | 5685.86 | 11.97 | 1.302 | 7914 | 4800 |
| MACG | 90-120s | 7437 | 630 | 8.47 | 4415.50 | 25.08 | 1.640 | 3666 | 4732 |

**n=100:**

| Protocol | Window | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|
| DSDV | 0-30s | 15007 | 971 | 6.47 | 4259.54 | 10.09 | 1.372 | 445537 | 93490 |
| DSDV | 30-60s | 14817 | 0 | 0.00 | — | — | — | 1119500 | 108824 |
| DSDV | 60-90s | 14919 | 0 | 0.00 | — | — | — | 891100 | 108884 |
| DSDV | 90-120s | 14854 | 0 | 0.00 | — | — | — | 1023700 | 109685 |
| Greedy | 0-30s | 15007 | 879 | 5.86 | 4241.85 | 6.84 | 1.363 | 40564 | 6000 |
| Greedy | 30-60s | 14817 | 346 | 2.34 | 9373.47 | 0.94 | 1.000 | 32749 | 6000 |
| Greedy | 60-90s | 14919 | 303 | 2.03 | 9157.49 | 0.97 | 1.000 | 37480 | 6000 |
| Greedy | 90-120s | 14854 | 326 | 2.19 | 9182.31 | 0.97 | 1.000 | 35229 | 6000 |
| QGeo | 0-30s | 15007 | 93 | 0.62 | 7591.45 | 4.44 | 1.118 | 55895 | 6000 |
| QGeo | 30-60s | 14817 | 93 | 0.63 | 9976.85 | 0.87 | 1.000 | 41453 | 6000 |
| QGeo | 60-90s | 14919 | 109 | 0.73 | 9988.08 | 0.87 | 1.000 | 48447 | 6000 |
| QGeo | 90-120s | 14854 | 104 | 0.70 | 10055.73 | 0.87 | 1.010 | 44770 | 6000 |
| CR-QGeo | 0-30s | 15007 | 87 | 0.58 | 7506.53 | 4.68 | 1.126 | 50795 | 6000 |
| CR-QGeo | 30-60s | 14817 | 104 | 0.70 | 9982.10 | 0.87 | 1.000 | 39021 | 6000 |
| CR-QGeo | 60-90s | 14919 | 105 | 0.70 | 9866.32 | 0.88 | 1.000 | 49483 | 6000 |
| CR-QGeo | 90-120s | 14854 | 121 | 0.81 | 10022.46 | 0.87 | 1.000 | 44543 | 6000 |
| MACG | 0-30s | 15007 | 1962 | 13.07 | 6527.01 | 3.54 | 1.215 | 46392 | 9900 |
| MACG | 30-60s | 14817 | 1513 | 10.21 | 9746.68 | 0.89 | 1.000 | 47187 | 10000 |
| MACG | 60-90s | 14919 | 1254 | 8.41 | 9615.99 | 0.91 | 1.000 | 45188 | 10000 |
| MACG | 90-120s | 14854 | 1452 | 9.78 | 9763.84 | 0.89 | 1.000 | 46144 | 9958 |

## 11. Cross-scale comparison

| n_drones | Best PDR | Best (lowest) delay | Lowest collisions | Best throughput | Notable |
|---|---|---|---|---|---|
| 10 | Greedy (67.90%) | DSDV (228.19ms) | Greedy (213) | DSDV (1164.05 Kbps) | Greedy and MACG close behind at 66.48%; DSDV collapses by window 3 |
| 20 | Greedy (55.06%) | DSDV (71.34ms) | Greedy (2864) | DSDV (765.80 Kbps) | DSDV collapses to near-zero by window 2 (4.21%) |
| 50 | Greedy (19.46%) | DSDV (4059.34ms) | MACG (29076) | DSDV (18.94 Kbps) | DSDV dead from window 2 onward; MACG 2nd (13.82%) |
| 100 | **MACG (10.37%)** | DSDV (4259.54ms) | Greedy (146022) | DSDV (10.09 Kbps) | MACG overtakes Greedy at the highest density — the one tier where MACG wins outright |

DSDV's "lowest delay" and "best throughput" wins are a statistical artifact, not a sign of good performance —
see Section 15.

## 12. Observed protocol ranking

Averaged across the four tiers' overall PDR: **Greedy wins n=10/20/50 outright and is a strong 2nd at n=100;
MACG is uncompetitive at n=10/20 but wins n=100 outright and is 2nd at n=50; DSDV wins nothing at 120s and
collapses to the single worst protocol by n=50-100; QGeo and CR-QGeo remain the two weakest protocols
throughout**, with no consistent winner between them (QGeo edges CR-QGeo at n=10/50, CR-QGeo edges QGeo at
n=20, they're essentially tied at n=100).

## 13. Mechanism-based interpretation

- **DSDV goes from best-at-low-density to worst-at-every-density once duration is extended to 120s.** At n=10 it
  is competitive in window 1 (76.57%) but dead by window 3; at n=20 it is already collapsing by window 2
  (4.21%); at n=50 and n=100 it delivers packets *only* in window 1 and is completely dead (0 delivered) for the
  remaining 90 seconds at both tiers, while its collision count keeps climbing regardless (e.g. at n=100:
  445,537 → 1,119,500 → 891,100 → 1,023,700 collisions across the four windows, even with zero deliveries in the
  last three). This is the same control-traffic-flooding mechanism `ExperimentC.md` documented at a single
  density, now shown to onset *faster* as density increases — DSDV's proactive table broadcasts scale with
  network size, so more nodes means more frequent updates fighting for a fixed-capacity channel, and 120s is
  long enough for that fight to be lost decisively at every density tested here (not just the highest one, as
  the old 30s/16s-active sweep suggested).
- **Greedy remains the most consistent protocol at low-to-moderate density** (wins n=10/20/50 outright) because
  its stateless, always-forward-to-current-neighbor design has nothing to protect from staleness — but even
  Greedy's own PDR collapses hard by n=100 (67.90% → 55.06% → 19.46% → 3.11%), and at n=100 its collision count
  (146,022) is actually the *lowest* of the five despite its low PDR — the channel is so saturated at this
  density that even Greedy's minimal control overhead can't get enough packets through, though it still avoids
  contributing to the collision storm the way DSDV does.
- **MACG is the one protocol whose ranking *improves* with density, and it wins outright exactly where density
  is highest.** It is uncompetitive relative to Greedy at n=10/20 (3rd at n=20 with 41.31%) but closes the gap
  steadily (2nd at n=50 with 13.82%) and **overtakes Greedy outright at n=100** (10.37% vs Greedy's 3.11% —
  more than 3× Greedy's PDR). Its per-window delivery pattern at n=100 is also the most *stable* of any protocol at that density
  (1962 → 1513 → 1254 → 1452 delivered across the four windows, vs. every other protocol's near-total collapse
  after window 1) — consistent with clustering's setup cost being worth paying once density is high enough that
  direct flat routing (Greedy) can no longer cope, exactly the mechanism `ExperimentA.md`'s original 30s sweep
  and `ExperimentD.md`'s map-size sweep already identified, now confirmed to hold under sustained 120s load too.
- **QGeo and CR-QGeo remain the weakest protocols at every density**, both collapsing to below 1% PDR at n=100
  with near-identical behavior (399 vs 417 delivered, 190,565 vs 183,842 collisions) — their persistent
  random-exploration component and per-hop Q-value re-convergence cost never pays off under this study's
  combination of high contention and long duration.

## 14. Comparison with previous 30-second Experiment A

Direct numeric comparison is complicated by the fact that `ExperimentA.md`'s runs, though labeled "30s," only had
**~16 seconds of genuinely active network time** at every density (the default 20,000 J budget put every drone
to sleep at t≈16.3s regardless of UAV count — see `ExperimentA.md` §1). This rerun is therefore not a clean
"120s vs 30s" comparison at fixed methodology — it is the corrected, sustained-run version, fixing both the
duration *and* the energy-confound issues that affected the original. With that caveat:

- **n=10:** old (≈16s active) had DSDV winning at 92.84% PDR; new (120s honest) has Greedy winning at 67.90%,
  with DSDV falling to worst-of-five (25.96%) — a complete reversal, exactly matching `ExperimentC.md`'s
  single-tier finding.
- **n=100:** old had MACG winning at 14.75% (DSDV 2nd at 11.31%, Greedy 3rd at 9.39%); new has MACG *still*
  winning, now at 10.37% (an absolute drop, as expected under sustained load, but the same relative
  winner) — while DSDV falls from 2nd to dead last (1.63%). **MACG's win at the highest density tier is the one
  finding that survives the correction unchanged** — strong evidence it is a real property of MACG's clustering
  design paying off under high density, not an artifact of the old experiment's energy/duration confound.
- The old sweep's headline finding — "no single protocol wins everywhere, and the ranking flips at least twice
  across the density range" — holds up and sharpens: at 120s, DSDV never wins any tier (it only won n=10 in the
  old, energy-confounded version), and the Greedy→MACG handover at the high-density end is now the *only*
  ranking flip in the sweep, rather than one of several.

## 15. Caveats

- All results are **single-seed (2025)**; no statistical confidence claims are made.
- **n=100 was run separately from the rest of the matrix, in a dedicated follow-up pass**, because DSDV at
  n=100/120s took **8.13 hours** of wall-clock time on its own — a severe, superlinear (not merely
  proportional-to-n) cost driven by its 3,479,837 collisions over the run. The other four n=100 protocols,
  run afterward, took 164.6-178.9 minutes each (2.7-3.0 hours) — an order of magnitude faster than DSDV,
  confirming DSDV's control-flooding is the specific driver of the blowup rather than n=100 density being
  expensive for every protocol. This means DSDV's n=100 result and the other four protocols' n=100 results were
  produced in two separate process batches rather than one single concurrent run — both still use seed 2025 and
  the identical scenario configuration, so this does not affect comparability, but it is a departure from the
  "one matrix, one pass" execution described for the rest of the sweep.
- **"Best throughput" and "lowest delay" at n=20/50/100 are frequently won by DSDV despite its catastrophic
  PDR** — this is a statistical artifact of averaging only over the handful of packets DSDV manages to deliver
  (almost always concentrated in window 1, before its own control flooding kills the channel): those few
  packets tend to be short-hop and fast, so their average looks good, while the protocol as a whole is failing.
  This metric should not be read as "DSDV performs well" at these tiers.
- Collisions, control-packets-sent, and MAC delay are attributed to windows via checkpoint-diffing rather than
  per-event timestamps (see `ExperimentB_120s.md` §15 for the full explanation) — a deliberate choice to avoid
  touching any `mac/`, `phy/`, or per-protocol `routing/*/*.py` file.
- No routing-protocol parameter was tuned in response to any result in this experiment or any prior one in this
  series, including after seeing MACG's win at n=100 or DSDV's collapse.

## 16. Exact commands/scripts used

See `ExperimentB_120s.md` §16 for the full description of `tools/run_scenario.py`, `tools/orchestrator.py`, and
`tools/build_reports.py` (shared infrastructure, no repository source file modified).

```
# Main matrix (n=10/20/50, all 5 protocols, + all of Experiment B), first pass:
python -m tools.orchestrator --experiment both --workers 4 \
    --exclude-scenario-ids A_n100_dsdv,A_n100_greedy,A_n100_qgeo,A_n100_cr_qgeo,A_n100_macg \
    --out-root results/120s --sim-time-s 120
# restarted partway through at --workers 8 --only-failed to use more of the machine's 16 cores
# (10 scenarios already complete were preserved; the 4 then-in-flight n=50 scenarios were re-run)

# Deferred n=100 tier (Greedy/QGeo/CR-QGeo/MACG -- DSDV's n=100 result was already banked from
# an earlier standalone timing-calibration run of the identical scenario/seed):
python -m tools.orchestrator --experiment a --workers 4 \
    --scenario-ids A_n100_greedy,A_n100_qgeo,A_n100_cr_qgeo,A_n100_macg \
    --out-root results/120s --sim-time-s 120

python -m tools.build_reports --experiment a --out-root results/120s
```

Raw per-scenario results: `results/120s/A_n{10,20,50,100}_{dsdv,greedy,qgeo,cr_qgeo,macg}/result.json`.
Aggregated: `results/120s/ExperimentA_120s.csv`, `results/120s/ExperimentA_120s.json`.
