"""
Aggregates per-scenario result.json files from the 120s Experiment A/B rerun into
CSV/JSON raw-data files and markdown table fragments.

This script does NOT write the narrative/interpretation sections of ExperimentA_120s.md /
ExperimentB_120s.md / ExperimentAB_120s_Summary.md -- those require judgment about *why*
a protocol wins that shouldn't be templated. It produces the data tables and raw exports
those reports are built from, and enforces the mandatory energy-validation gate: it
refuses (non-zero exit) to certify an experiment's data as report-ready if any scenario
in that experiment shows a UAV went to sleep before the run ended.
"""

import argparse
import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_LABEL = {
    'dsdv': 'DSDV', 'greedy': 'Greedy', 'qgeo': 'QGeo', 'cr_qgeo': 'CR-QGeo', 'macg': 'MACG',
}
PROTOCOL_ORDER = ['dsdv', 'greedy', 'qgeo', 'cr_qgeo', 'macg']


def load_results(out_root, scenario_ids):
    results = {}
    missing = []
    for sid in scenario_ids:
        path = Path(out_root) / sid / 'result.json'
        if not path.exists():
            missing.append(sid)
            continue
        with open(path) as f:
            results[sid] = json.load(f)
    return results, missing


def experiment_a_scenarios():
    return [f"A_n{n}_{p}" for n in (10, 20, 50, 100) for p in PROTOCOL_ORDER]


def experiment_b_scenarios():
    return [f"B_v{v}_{p}" for v in (10, 20, 30, 40) for p in PROTOCOL_ORDER]


def fmt(x, nd=2):
    return "" if x is None else (round(x, nd) if isinstance(x, float) else x)


def energy_gate(results, label):
    offenders = []
    for sid, r in results.items():
        if r.get("status") != "ok":
            offenders.append((sid, "run failed, cannot validate"))
            continue
        ev = r.get("energy_validation") or {}
        if ev.get("any_drone_slept"):
            offenders.append((sid, f"slept at t={ev.get('first_sleep_time_s')}s "
                                    f"(drone {ev.get('first_sleep_drone_id')})"))
    if offenders:
        print(f"ENERGY VALIDATION FAILED for Experiment {label}:")
        for sid, msg in offenders:
            print(f"  {sid}: {msg}")
        return False
    print(f"Energy validation OK for Experiment {label}: {len(results)} scenarios, zero sleeps.")
    return True


def write_wide_csv(results, scenario_ids, path, tier_key, tier_label_fn):
    fieldnames = [
        "scenario_id", "protocol", tier_key, "status",
        "packets_generated", "packets_delivered", "pdr_pct", "avg_e2e_delay_ms",
        "routing_load", "avg_throughput_kbps", "avg_hop_count", "collisions",
        "avg_mac_delay_ms", "control_packets_sent",
        "any_drone_slept", "min_final_residual_energy_j", "avg_final_residual_energy_j",
        "wall_clock_seconds",
    ]
    for i in range(1, 5):
        fieldnames += [f"w{i}_generated", f"w{i}_delivered", f"w{i}_pdr_pct",
                       f"w{i}_avg_e2e_delay_ms", f"w{i}_avg_throughput_kbps",
                       f"w{i}_avg_hop_count", f"w{i}_collisions", f"w{i}_control_packets_sent",
                       f"w{i}_routing_load", f"w{i}_avg_mac_delay_ms"]

    rows = []
    for sid in scenario_ids:
        r = results.get(sid)
        if r is None:
            rows.append({"scenario_id": sid, "status": "missing"})
            continue
        row = {
            "scenario_id": sid,
            "protocol": PROTOCOL_LABEL.get(r["protocol"], r["protocol"]),
            tier_key: tier_label_fn(r),
            "status": r["status"],
        }
        overall = r.get("overall") or {}
        for k in ["packets_generated", "packets_delivered", "pdr_pct", "avg_e2e_delay_ms",
                  "routing_load", "avg_throughput_kbps", "avg_hop_count", "collisions",
                  "avg_mac_delay_ms", "control_packets_sent"]:
            row[k] = fmt(overall.get(k))
        ev = r.get("energy_validation") or {}
        row["any_drone_slept"] = ev.get("any_drone_slept")
        row["min_final_residual_energy_j"] = fmt(ev.get("min_final_residual_energy_j"))
        row["avg_final_residual_energy_j"] = fmt(ev.get("avg_final_residual_energy_j"))
        row["wall_clock_seconds"] = fmt(r.get("wall_clock_seconds"), 1)
        for w in (r.get("windows") or []):
            i = w["window_index"]
            row[f"w{i}_generated"] = w.get("generated")
            row[f"w{i}_delivered"] = w.get("delivered")
            row[f"w{i}_pdr_pct"] = fmt(w.get("pdr_pct"))
            row[f"w{i}_avg_e2e_delay_ms"] = fmt(w.get("avg_e2e_delay_ms"))
            row[f"w{i}_avg_throughput_kbps"] = fmt(w.get("avg_throughput_kbps"))
            row[f"w{i}_avg_hop_count"] = fmt(w.get("avg_hop_count"))
            row[f"w{i}_collisions"] = w.get("collisions")
            row[f"w{i}_control_packets_sent"] = w.get("control_packets_sent")
            row[f"w{i}_routing_load"] = fmt(w.get("routing_load"))
            row[f"w{i}_avg_mac_delay_ms"] = fmt(w.get("avg_mac_delay_ms"))
        rows.append(row)

    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def markdown_overall_table(results, tier_scenarios):
    header = ("| Protocol | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | "
               "Routing Load | Avg Throughput (Kbps) | Avg Hop Count | Collisions | "
               "Avg MAC Delay (ms) | Control Pkts |")
    sep = "|---|---|---|---|---|---|---|---|---|---|---|"
    lines = [header, sep]
    for sid in tier_scenarios:
        r = results.get(sid)
        if r is None or r.get("status") != "ok":
            proto = sid.split('_')[-1]
            lines.append(f"| {PROTOCOL_LABEL.get(proto, proto)} | FAILED/MISSING ({sid}) | | | | | | | | | |")
            continue
        o = r["overall"]
        lines.append(
            f"| {PROTOCOL_LABEL[r['protocol']]} | {o['packets_generated']} | {o['packets_delivered']} | "
            f"{fmt(o['pdr_pct'])} | {fmt(o['avg_e2e_delay_ms'])} | {fmt(o['routing_load'], 3)} | "
            f"{fmt(o['avg_throughput_kbps'])} | {fmt(o['avg_hop_count'], 3)} | {o['collisions']} | "
            f"{fmt(o['avg_mac_delay_ms'])} | {o['control_packets_sent']} |"
        )
    return "\n".join(lines)


def markdown_window_table(results, tier_scenarios):
    header = ("| Protocol | Window | Generated | Delivered | PDR (%) | Avg E2E Delay (ms) | "
               "Avg Throughput (Kbps) | Avg Hop Count | Collisions | Control Pkts | Routing Load | Avg MAC Delay (ms) |")
    sep = "|---|---|---|---|---|---|---|---|---|---|---|---|"
    lines = [header, sep]
    for sid in tier_scenarios:
        r = results.get(sid)
        if r is None or r.get("status") != "ok":
            continue
        for w in r["windows"]:
            lines.append(
                f"| {PROTOCOL_LABEL[r['protocol']]} | {w['label']} | {w['generated']} | {w['delivered']} | "
                f"{fmt(w['pdr_pct'])} | {fmt(w['avg_e2e_delay_ms'])} | {fmt(w['avg_throughput_kbps'])} | "
                f"{fmt(w['avg_hop_count'], 3)} | {w['collisions']} | {w['control_packets_sent']} | "
                f"{fmt(w['routing_load'], 3)} | {fmt(w['avg_mac_delay_ms'])} |"
            )
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out-root', default=str(REPO_ROOT / 'results' / '120s'))
    p.add_argument('--experiment', choices=['a', 'b', 'both'], default='both')
    args = p.parse_args()
    out_root = Path(args.out_root)

    ok = True

    if args.experiment in ('a', 'both'):
        scenario_ids = experiment_a_scenarios()
        results, missing = load_results(out_root, scenario_ids)
        if missing:
            print(f"Experiment A: MISSING result.json for {missing}")
            ok = False
        if not energy_gate(results, "A"):
            ok = False
        rows = write_wide_csv(results, scenario_ids, out_root / 'ExperimentA_120s.csv',
                               'n_drones', lambda r: r['params']['n_drones'])
        with open(out_root / 'ExperimentA_120s.json', 'w') as f:
            json.dump(results, f, indent=2)
        for n in (10, 20, 50, 100):
            tier = [f"A_n{n}_{p}" for p in PROTOCOL_ORDER]
            (out_root / f'A_n{n}_overall_table.md').write_text(markdown_overall_table(results, tier))
            (out_root / f'A_n{n}_window_table.md').write_text(markdown_window_table(results, tier))
        print(f"Experiment A: wrote {len(rows)} rows to ExperimentA_120s.csv")

    if args.experiment in ('b', 'both'):
        scenario_ids = experiment_b_scenarios()
        results, missing = load_results(out_root, scenario_ids)
        if missing:
            print(f"Experiment B: MISSING result.json for {missing}")
            ok = False
        if not energy_gate(results, "B"):
            ok = False
        rows = write_wide_csv(results, scenario_ids, out_root / 'ExperimentB_120s.csv',
                               'speed', lambda r: r['params']['speed'])
        with open(out_root / 'ExperimentB_120s.json', 'w') as f:
            json.dump(results, f, indent=2)
        for v in (10, 20, 30, 40):
            tier = [f"B_v{v}_{p}" for p in PROTOCOL_ORDER]
            (out_root / f'B_v{v}_overall_table.md').write_text(markdown_overall_table(results, tier))
            (out_root / f'B_v{v}_window_table.md').write_text(markdown_window_table(results, tier))
        print(f"Experiment B: wrote {len(rows)} rows to ExperimentB_120s.csv")

    if not ok:
        print("build_reports: one or more gates failed -- see above. Not certifying reports as complete.")
        raise SystemExit(1)
    print("All gates passed.")


if __name__ == '__main__':
    main()
