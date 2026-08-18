# Experiment B (120s rerun): Mobility Speed Sweep (DSDV vs Greedy vs QGeo vs CR-QGeo vs MACG)

## 1. Purpose

`ExperimentB.md` swept mobility speed (10/20/30/40 m/s) at a 30-second simulation duration. `ExperimentC.md`
subsequently showed, with a single continuous 120-second run, that 30 seconds is too short to see a protocol's
real sustained-load behavior — DSDV looks best at 30s and collapses to worst by 120s, while MACG and CR-QGeo
only pull ahead given enough sustained time. This experiment reruns the speed sweep at **120 seconds** so the
comparison reflects sustained mobility/routing behavior rather than a short transient, answering: **how does
UAV mobility speed affect routing performance during sustained operation, with energy-induced UAV death
removed as a confounding factor?** This is a mobility/routing experiment, not an energy-efficiency experiment
— `INITIAL_ENERGY` is deliberately oversized (see Section 4) specifically to take energy out of the picture.

## 2. Configuration

| Parameter | Value |
|---|---|
| Simulation seed | 2025 (fixed, identical across all 20 runs) |
| Speeds swept | 10, 20, 30, 40 m/s |
| Protocols compared | DSDV, Greedy, QGeo, CR-QGeo, MACG |
| Number of UAVs | 10 (fixed) |
| Simulation time | **120 s** |
| Map size | 600 m × 600 m × 100 m (fixed) |
| Mobility model | 3-D Gauss-Markov |
| Traffic pattern | Poisson, rate = 5 packets/s per UAV (unchanged, hardcoded default in `entities/drone.py`) |
| `INITIAL_ENERGY` | 5,000,000 J, identical across all 20 runs |

No routing/MAC/PHY/mobility/energy source file was modified to produce this rerun (see Section 5 and 16) —
every scenario parameter is set by overriding `utils.config` attributes in-process before the simulator is
constructed, exactly the way `ExperimentC.md` §6 already documented and validated as this repo's own
reproduction recipe.

## 3. Why 120 seconds is used

Per `ExperimentC.md`, a 30-second snapshot hides real protocol behavior: DSDV's routing-table flooding takes
tens of seconds to saturate the channel, CR-QGeo's congestion-aware reward needs sustained time to redirect
traffic away from congested paths, and MACG's clustering overhead only pays for itself over enough time/density.
Rerunning the speed sweep at 120s (binned into four 30s windows) lets the same effects that `ExperimentC.md`
found for a single density/speed tier be checked across the full speed range.

## 4. Why `INITIAL_ENERGY` = 5,000,000 J

Unlike UAV count or map size, mobility speed directly changes flight power under this simulator's rotary-wing
power model (`energy/energy_model.py`, unmodified) — `ExperimentB.md` §2 already documented that the
power-vs-speed relationship is non-monotonic, so a fixed small energy budget would make different speeds run
out of energy at different times, confounding "mobility effect" with "how much active network time this speed
happened to get before its UAVs went permanently silent." `ExperimentB.md`'s own energy-neutralized pass
(§4) already established 5,000,000 J (≈ tens of minutes of flight at any of these four speeds) as sufficient to
remove that confound for a 30s run; the same value is used here, unchanged, and confirmed sufficient for the
full 120s duration (Section 5) — applied identically across all 20 runs, so it cannot bias the comparison
between protocols or between speeds.

## 5. Confirmation that no UAV sleeps

Every one of the 20 runs was checked post-hoc: `energy_validation.any_drone_slept` is `false` for all 20
scenarios, `num_sleeping_drones_at_end` is 0 in every case, and minimum final residual energy across all runs
and all drones stayed above ~4.99 million J (i.e. UAVs used well under 0.2% of their energy budget over the
full 120s at every speed tested) — confirming the 5,000,000 J budget removes energy exhaustion as a factor
entirely, exactly as intended.

## 6. Overall (0–120s) results — 10 m/s

| Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Routing Load | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Avg MAC Delay (ms) | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|---|
| DSDV | 5863 | 1522 | 25.96 | 228.19 | 3.205 | 1164.05 | 1.568 | 1233 | 5.21 | 4878 |
| **Greedy** | 5863 | **3981** | **67.90** | 468.71 | 0.603 | 1049.85 | 1.639 | **213** | 28.66 | 2400 |
| QGeo | 5863 | 2497 | 42.59 | 912.90 | 0.961 | 273.78 | 2.158 | 479 | 1153.16 | 2400 |
| CR-QGeo | 5863 | 2864 | 48.85 | 1423.32 | 0.838 | 196.98 | 2.292 | 725 | 1170.81 | 2400 |
| MACG | 5863 | 3429 | 58.49 | 900.91 | 1.073 | 477.66 | 1.791 | 741 | 857.28 | 3678 |

## 7. Overall (0–120s) results — 20 m/s

| Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Routing Load | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Avg MAC Delay (ms) | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|---|
| DSDV | 5863 | 613 | 10.46 | 325.73 | 11.591 | 1064.86 | 1.706 | 2564 | 4.50 | 7105 |
| **Greedy** | 5863 | **4531** | **77.28** | 715.97 | 0.530 | 919.20 | 1.746 | 281 | 46.92 | 2400 |
| QGeo | 5863 | 2042 | 34.83 | 1778.59 | 1.175 | 191.71 | 2.517 | 512 | 960.84 | 2400 |
| CR-QGeo | 5863 | 1621 | 27.65 | 1396.78 | 1.481 | 147.94 | 2.381 | 466 | 989.28 | 2400 |
| MACG | 5863 | 1366 | 23.30 | 705.24 | 2.673 | 587.96 | 1.634 | **182** | 584.35 | 3651 |

## 8. Overall (0–120s) results — 30 m/s

| Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Routing Load | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Avg MAC Delay (ms) | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|---|
| DSDV | 5863 | 680 | 11.60 | 468.29 | 6.459 | 1031.11 | 1.654 | 1492 | 8.60 | 4392 |
| **Greedy** | 5863 | **3896** | **66.45** | 945.85 | 0.616 | 927.32 | 1.718 | 244 | 111.01 | 2400 |
| QGeo | 5863 | 862 | 14.70 | 822.27 | 2.784 | 319.40 | 2.244 | **114** | 660.31 | 2400 |
| CR-QGeo | 5863 | 1546 | 26.37 | 1493.36 | 1.552 | 181.30 | 2.424 | 260 | 1253.46 | 2400 |
| MACG | 5863 | 2277 | 38.84 | 579.84 | 1.613 | 656.43 | 1.703 | 366 | 275.16 | 3672 |

## 9. Overall (0–120s) results — 40 m/s

| Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Routing Load | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Avg MAC Delay (ms) | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|---|
| DSDV | 5863 | 500 | 8.53 | 392.06 | 11.408 | 1055.16 | 1.634 | 2052 | 7.23 | 5704 |
| **Greedy** | 5863 | **2578** | **43.97** | 642.03 | 0.931 | 1013.39 | 1.659 | **175** | 103.30 | 2400 |
| QGeo | 5863 | 1201 | 20.48 | 1366.06 | 1.998 | 229.79 | 2.429 | 301 | 772.68 | 2400 |
| CR-QGeo | 5863 | 1555 | 26.52 | 1967.79 | 1.543 | 136.11 | 2.568 | 366 | 1065.65 | 2400 |
| MACG | 5863 | 2403 | 40.99 | 893.49 | 1.543 | 610.78 | 1.862 | 307 | 330.04 | 3707 |

Bold marks the best value per metric within each speed tier.

## 10. Time-window results (independent, non-cumulative, per 30s window)

Each window's PDR = packets delivered whose *arrival time* falls in that window / packets generated whose
*creation time* falls in that window — an independent per-window ratio, not a cumulative-through-window one
(see Section 15 for why this distinction matters and how it differs from `ExperimentC.md`'s table).

**10 m/s:**

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
| MACG | 0-30s | 1447 | 1098 | 75.88 | 46.63 | 918.22 | 1.633 | 84 | 921 |
| MACG | 30-60s | 1453 | 753 | 51.82 | 1762.49 | 214.43 | 1.951 | 171 | 937 |
| MACG | 60-90s | 1446 | 707 | 48.89 | 1387.68 | 135.67 | 1.542 | 277 | 910 |
| MACG | 90-120s | 1517 | 871 | 57.42 | 837.87 | 427.44 | 2.056 | 209 | 910 |

**20 m/s:**

| Protocol | Window | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|
| DSDV | 0-30s | 1447 | 612 | 42.29 | 326.24 | 1065.63 | 1.704 | 404 | 1594 |
| DSDV | 30-60s | 1453 | 1 | 0.07 | 14.66 | 590.41 | 3.000 | 560 | 1596 |
| DSDV | 60-90s | 1446 | 0 | 0.00 | — | — | — | 700 | 1650 |
| DSDV | 90-120s | 1517 | 0 | 0.00 | — | — | — | 900 | 2265 |
| Greedy | 0-30s | 1447 | 972 | 67.17 | 447.86 | 1057.37 | 1.634 | 60 | 600 |
| Greedy | 30-60s | 1453 | 1018 | 70.06 | 1139.36 | 792.39 | 1.915 | 39 | 600 |
| Greedy | 60-90s | 1446 | 1222 | 84.51 | 711.28 | 814.17 | 1.879 | 139 | 600 |
| Greedy | 90-120s | 1517 | 1319 | 86.95 | 591.14 | 1012.56 | 1.575 | 43 | 600 |
| QGeo | 0-30s | 1447 | 660 | 45.61 | 259.53 | 425.42 | 2.512 | 148 | 600 |
| QGeo | 30-60s | 1453 | 461 | 31.73 | 2961.12 | 69.36 | 2.725 | 143 | 600 |
| QGeo | 60-90s | 1446 | 519 | 35.89 | 2760.07 | 63.97 | 2.339 | 162 | 600 |
| QGeo | 90-120s | 1517 | 402 | 26.50 | 1649.33 | 113.26 | 2.517 | 59 | 600 |
| CR-QGeo | 0-30s | 1447 | 719 | 49.69 | 568.95 | 170.77 | 2.624 | 247 | 600 |
| CR-QGeo | 30-60s | 1453 | 504 | 34.69 | 2416.85 | 88.16 | 2.194 | 126 | 600 |
| CR-QGeo | 60-90s | 1446 | 160 | 11.07 | 1130.59 | 163.60 | 1.637 | 67 | 600 |
| CR-QGeo | 90-120s | 1517 | 238 | 15.69 | 1916.45 | 195.06 | 2.538 | 26 | 600 |
| MACG | 0-30s | 1447 | 651 | 44.99 | 244.43 | 757.38 | 1.576 | 126 | 940 |
| MACG | 30-60s | 1453 | 304 | 20.92 | 1289.73 | 403.68 | 1.641 | 24 | 911 |
| MACG | 60-90s | 1446 | 257 | 17.77 | 1129.57 | 392.71 | 1.677 | 26 | 902 |
| MACG | 90-120s | 1517 | 154 | 10.15 | 791.29 | 561.42 | 1.792 | 6 | 898 |

**30 m/s:**

| Protocol | Window | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|
| DSDV | 0-30s | 1447 | 609 | 42.09 | 245.95 | 1081.95 | 1.593 | 252 | 1018 |
| DSDV | 30-60s | 1453 | 71 | 4.89 | 2375.46 | 595.03 | 2.183 | 280 | 977 |
| DSDV | 60-90s | 1446 | 0 | 0.00 | — | — | — | 530 | 1123 |
| DSDV | 90-120s | 1517 | 0 | 0.00 | — | — | — | 430 | 1274 |
| Greedy | 0-30s | 1447 | 820 | 56.67 | 163.10 | 1138.75 | 1.548 | 124 | 600 |
| Greedy | 30-60s | 1453 | 1157 | 79.63 | 1351.84 | 817.50 | 1.874 | 36 | 600 |
| Greedy | 60-90s | 1446 | 909 | 62.86 | 542.84 | 1028.32 | 1.552 | 28 | 600 |
| Greedy | 90-120s | 1517 | 1010 | 66.58 | 1478.98 | 790.58 | 1.829 | 56 | 600 |
| QGeo | 0-30s | 1447 | 430 | 29.72 | 508.03 | 365.06 | 2.779 | 51 | 600 |
| QGeo | 30-60s | 1453 | 194 | 13.35 | 1038.62 | 162.38 | 1.979 | 20 | 600 |
| QGeo | 60-90s | 1446 | 157 | 10.86 | 1066.57 | 404.82 | 1.586 | 20 | 600 |
| QGeo | 90-120s | 1517 | 81 | 5.34 | 1498.71 | 287.52 | 1.309 | 23 | 600 |
| CR-QGeo | 0-30s | 1447 | 532 | 36.77 | 481.90 | 288.83 | 2.624 | 88 | 600 |
| CR-QGeo | 30-60s | 1453 | 490 | 33.72 | 2119.78 | 111.89 | 2.739 | 65 | 600 |
| CR-QGeo | 60-90s | 1446 | 336 | 23.24 | 1800.80 | 153.78 | 1.676 | 30 | 600 |
| CR-QGeo | 90-120s | 1517 | 188 | 12.39 | 2173.40 | 107.13 | 2.372 | 77 | 600 |
| MACG | 0-30s | 1447 | 722 | 49.90 | 333.81 | 719.88 | 1.661 | 138 | 943 |
| MACG | 30-60s | 1453 | 681 | 46.87 | 1197.15 | 513.83 | 1.922 | 111 | 910 |
| MACG | 60-90s | 1446 | 583 | 40.32 | 328.54 | 749.07 | 1.664 | 48 | 918 |
| MACG | 90-120s | 1517 | 291 | 19.18 | 249.06 | 647.09 | 1.375 | 69 | 901 |

**40 m/s:**

| Protocol | Window | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | Avg Throughput (Kbps) | Avg Hop Count | Collisions | Control Pkts |
|---|---|---|---|---|---|---|---|---|---|
| DSDV | 0-30s | 1447 | 500 | 34.55 | 392.06 | 1055.16 | 1.634 | 262 | 1091 |
| DSDV | 30-60s | 1453 | 0 | 0.00 | — | — | — | 600 | 1578 |
| DSDV | 60-90s | 1446 | 0 | 0.00 | — | — | — | 720 | 1601 |
| DSDV | 90-120s | 1517 | 0 | 0.00 | — | — | — | 470 | 1434 |
| Greedy | 0-30s | 1447 | 782 | 54.04 | 541.79 | 1068.18 | 1.566 | 106 | 600 |
| Greedy | 30-60s | 1453 | 721 | 49.62 | 576.75 | 897.91 | 1.782 | 24 | 600 |
| Greedy | 60-90s | 1446 | 735 | 50.83 | 931.88 | 971.45 | 1.756 | 23 | 600 |
| Greedy | 90-120s | 1517 | 340 | 22.41 | 384.39 | 1222.91 | 1.403 | 22 | 600 |
| QGeo | 0-30s | 1447 | 660 | 45.61 | 1128.19 | 235.63 | 2.585 | 209 | 600 |
| QGeo | 30-60s | 1453 | 299 | 20.58 | 2144.99 | 132.22 | 2.632 | 38 | 600 |
| QGeo | 60-90s | 1446 | 146 | 10.10 | 814.45 | 359.75 | 1.445 | 50 | 600 |
| QGeo | 90-120s | 1517 | 96 | 6.33 | 1414.31 | 295.86 | 2.219 | 4 | 600 |
| CR-QGeo | 0-30s | 1447 | 572 | 39.53 | 660.95 | 256.99 | 2.510 | 122 | 600 |
| CR-QGeo | 30-60s | 1453 | 413 | 28.42 | 3324.87 | 33.75 | 2.838 | 135 | 600 |
| CR-QGeo | 60-90s | 1446 | 321 | 22.20 | 2244.66 | 63.72 | 2.467 | 88 | 600 |
| CR-QGeo | 90-120s | 1517 | 249 | 16.41 | 2362.01 | 121.53 | 2.382 | 21 | 600 |
| MACG | 0-30s | 1447 | 723 | 49.97 | 236.49 | 786.81 | 1.559 | 176 | 954 |
| MACG | 30-60s | 1453 | 684 | 47.08 | 1290.44 | 500.81 | 1.889 | 45 | 924 |
| MACG | 60-90s | 1446 | 565 | 39.07 | 1213.13 | 577.37 | 2.074 | 64 | 916 |
| MACG | 90-120s | 1517 | 431 | 28.41 | 946.65 | 533.81 | 2.051 | 22 | 913 |

## 11. Cross-speed comparison

| Speed | Best PDR | Best (lowest) collisions | Notable |
|---|---|---|---|
| 10 m/s | Greedy (67.90%) | Greedy (213) | DSDV and Greedy were close in the old 30s pass (76.57 vs 76.23%); at 120s Greedy pulls clearly ahead as DSDV collapses in windows 3-4 |
| 20 m/s | Greedy (77.28%) | MACG (182) | Greedy's *best* tier of the sweep — non-monotonic with speed; DSDV nearly dead by window 2 (1 packet delivered) |
| 30 m/s | Greedy (66.45%) | QGeo (114) | DSDV dead by window 3; MACG 2nd (38.84%) |
| 40 m/s | Greedy (43.97%) | Greedy (175) | DSDV's worst tier — dead from window 2 onward; MACG edges out CR-QGeo for 2nd (40.99% vs 26.52%) |

## 12. Protocol ranking

Averaged across all four speeds' overall PDR: **Greedy (63.90%) ≫ MACG (40.41%) > CR-QGeo (32.35%) ≈ QGeo
(28.15%) ≫ DSDV (14.14%)**. Greedy wins every single one of the four speed tiers outright on overall PDR — a
stronger, more one-sided result than the old 30s sweep, where DSDV and Greedy were close at 10 m/s. MACG is a
clear second overall despite one weak tier (20 m/s); DSDV is comfortably the worst protocol at every speed once
duration is extended to 120s, a reversal from the 30s sweep where DSDV won the 10 m/s tier outright.

## 13. Mechanism-based interpretation

- **DSDV collapses at every speed once given 120s, and collapses faster as speed increases.** At 10 m/s it
  delivers 0 packets in windows 3 and 4; at 20/30 m/s it is already down to 1 and 71 packets respectively by
  window 2 and fully dead by window 3; at 40 m/s it is dead from window 2 onward — the fastest collapse of the
  sweep. This is exactly the mechanism `ExperimentC.md` documented (periodic table-broadcast control traffic
  keeps flooding the channel even as deliveries hit zero — collisions keep climbing through all four windows at
  every speed here too, e.g. 88→275→470→400 at 10 m/s, 404→560→700→900 at 20 m/s) — and mobility speed adds a
  second stressor on top of duration: faster topology change means DSDV's tables go stale faster, so it needs to
  broadcast updates more often, which saturates the channel sooner. The two effects (duration and speed) compound
  rather than being independent.
- **Greedy is the standout across the entire sweep**, winning all four tiers outright and, unusually, performing
  *better* at 20 m/s (77.28%) than at 10 m/s (67.90%) — its per-window deliveries actually climb across the run
  at 20 m/s (972→1018→1222→1319), the opposite of DSDV's collapse. With no multi-hop route or Q-table to protect
  from staleness, greedy per-hop forwarding to the current nearest neighbor has nothing to compound negatively
  over time, and collision counts stay low and roughly flat across windows at every speed (e.g. 106/24/23/22 at
  40 m/s) — control overhead is also the lowest and flattest of the five (fixed at 600 control packets across
  every 30s window, at every speed).
- **MACG is not simply "moderate" — it has a distinct 20 m/s weak spot** (23.30% overall, its worst tier, with
  deliveries falling every window: 651→304→257→154) that does not reappear at 30 or 40 m/s (38.84%, 40.99%,
  both with a healthier per-window profile). This mirrors the odd non-monotonic dip `ExperimentB.md` already
  found in the 30s sweep (MACG worst-of-five at 20 m/s, climbing back at 30-40 m/s) — the effect survives the
  extension to 120s essentially unchanged in shape, suggesting it's a real property of MACG's clustering dynamics
  at that specific speed/churn combination rather than a 30s-snapshot artifact.
- **CR-QGeo outperforms QGeo at 3 of 4 speed tiers at 120s** (10, 30, 40 m/s; QGeo only wins at 20 m/s), a
  reversal from the 30s sweep where the two tracked closely with no consistent winner. This is consistent with
  `ExperimentC.md`'s finding that CR-QGeo's congestion-aware reward needs sustained time to redirect traffic away
  from congested paths — evidence the same mechanism operates across the mobility sweep, not just at one fixed
  speed/density.

## 14. Comparison with previous 30-second Experiment B

`ExperimentB.md`'s energy-neutralized pass (§4, 5,000,000 J, the directly comparable baseline) is reproduced
*exactly* by this experiment's first 30-second window at every speed (e.g. 10 m/s: DSDV 1447/1108/76.57%,
Greedy 1447/1103/76.23% — identical generated/delivered/PDR figures) — confirming both runs share the same
deterministic seed and initial conditions, and that the only thing this rerun changes is how much longer the
simulation is allowed to continue. The differences that emerge are entirely a duration effect:

- **DSDV wins the 10 m/s tier at 30s (76.57% vs Greedy's 76.23%) but is the worst protocol at every speed by
  120s** (25.96% at 10 m/s, falling to 8.53% at 40 m/s) — the reversal `ExperimentC.md` already demonstrated at
  a single tier now confirmed across the full speed range.
- **Greedy's ranking strengthens**: at 30s it only clearly wins 20-40 m/s (10 m/s was a near-tie with DSDV); at
  120s it wins all four tiers outright, several by a wide margin.
- **CR-QGeo vs. QGeo flips from "no consistent winner" at 30s to "CR-QGeo wins 3 of 4" at 120s** — see Section 13.
- **MACG's 20 m/s weak spot persists unchanged in shape** from 30s to 120s — this looks like a genuine speed-
  dependent property of MACG rather than something duration fixes or worsens.

## 15. Caveats

- All results are **single-seed (2025)**; no statistical confidence claims are made, consistent with every prior
  experiment in this series.
- "Independent per-window PDR" (Section 10) divides packets delivered-in-window (by arrival time) by packets
  generated-in-window (by creation time) — these are not a strict cohort (a packet generated late in one window
  can be delivered in the next), so a window's PDR is not literally "what fraction of this window's own packets
  arrived," but it is the metric the task specifies and it is **not** cumulative-through-window, unlike the
  superficially similar table in `ExperimentC.md` (whose "Cumulative PDR" column is exactly what it says, despite
  looking at a glance like a per-window figure — this report's window PDRs are the corrected, independent
  version).
- Collisions, control-packets-sent, and MAC delay are attributed to windows via checkpoint-diffing (snapshotting
  `sim.metrics` counters at each 30s boundary and taking consecutive differences) rather than per-event
  timestamps, because those three metrics' only increment sites live inside `mac/`, `phy/`, and the per-protocol
  `routing/*/*.py` files, which this task requires to stay untouched. Because simpy processes events in strict
  time order, list/dict insertion order is itself time-ordered, so this diffing is exact, not approximate — but
  it does mean a boundary-tie (an event at the exact microsecond of a window edge) would be attributed by simpy's
  internal same-timestamp scheduling order rather than a per-event log; this is judged negligible given
  continuous random inter-arrival times, and is not visible in any of the collected data.
- Throughput here is `packet_length / per-packet latency`, averaged only over delivered packets — at low PDR
  (e.g. DSDV) this statistic describes the few packets that got through quickly, not aggregate network capacity,
  and should not be read as "DSDV has good throughput" despite its high Kbps figures in Section 6-9.
- No routing-protocol parameter (MACG_*, CR-QGeo weights, QGeo exploration, Greedy/DSDV behavior) was tuned in
  response to any result in this experiment or any prior one in this series.

## 16. Exact commands/scripts used

New, non-production tooling under `tools/` (repository source files were **not** modified — see the top-level
summary for the full list of what was and wasn't touched):

```
tools/run_scenario.py   -- single-scenario subprocess driver (overrides utils.config in-process,
                            runs one Simulator to completion, snapshots sim.metrics at 30/60/90s
                            checkpoints for independent per-window metrics, reads final sim.drones
                            state for energy validation, writes result.json)
tools/orchestrator.py   -- parallel matrix runner (bounded subprocess pool, one OS process per
                            scenario, never a reused worker interpreter)
tools/build_reports.py  -- aggregates all result.json files into CSV/JSON + markdown table fragments,
                            enforces the energy-validation gate
```

Commands actually run for this experiment (in addition to the mandatory 2-scenario validation pair described
in the top-level summary):

```
python -m tools.orchestrator --experiment both --workers 4 \
    --exclude-scenario-ids A_n100_dsdv,A_n100_greedy,A_n100_qgeo,A_n100_cr_qgeo,A_n100_macg \
    --out-root results/120s --sim-time-s 120
# (restarted mid-run at --workers 8 --only-failed to use more of the machine's idle cores;
#  see the top-level summary for why and how continuity was preserved)

python -m tools.build_reports --experiment b --out-root results/120s
```

Raw per-scenario results: `results/120s/B_v{10,20,30,40}_{dsdv,greedy,qgeo,cr_qgeo,macg}/result.json`.
Aggregated: `results/120s/ExperimentB_120s.csv`, `results/120s/ExperimentB_120s.json`.
