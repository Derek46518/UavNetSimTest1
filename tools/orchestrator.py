"""
Parallel matrix runner for the 120s Experiment A/B rerun.

Launches each (protocol x tier) scenario as its own OS subprocess (never a reused
worker-pool interpreter, to avoid any risk of `utils.config` module-cache or
mobility/start_coords.py's global-`random` state leaking between scenarios), bounded
to --workers concurrent processes. Every scenario writes to its own output directory;
utils/config.py on disk is never touched by any worker.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROTOCOLS = ['dsdv', 'greedy', 'qgeo', 'cr_qgeo', 'macg']


def venv_python():
    candidate = REPO_ROOT / '.venv' / 'Scripts' / 'python.exe'
    if candidate.exists():
        return str(candidate)
    return sys.executable


def build_matrix(experiment):
    scenarios = []
    if experiment in ('a', 'both'):
        for n in (10, 20, 50, 100):
            for proto in PROTOCOLS:
                scenarios.append({
                    "scenario_id": f"A_n{n}_{proto}",
                    "experiment": "A",
                    "protocol": proto,
                    "n_drones": n,
                    "speed": 10,
                    "initial_energy": 200_000,
                })
    if experiment in ('b', 'both'):
        for v in (10, 20, 30, 40):
            for proto in PROTOCOLS:
                scenarios.append({
                    "scenario_id": f"B_v{v}_{proto}",
                    "experiment": "B",
                    "protocol": proto,
                    "n_drones": 10,
                    "speed": v,
                    "initial_energy": 5_000_000,
                })
    return scenarios


def scenario_status(out_root, scenario_id):
    result_path = Path(out_root) / scenario_id / 'result.json'
    if not result_path.exists():
        return "pending"
    try:
        with open(result_path) as f:
            data = json.load(f)
        return "done" if data.get("status") == "ok" else "failed"
    except Exception:
        return "failed"


def launch(scenario, out_root, sim_time_s, logging_level):
    out_dir = Path(out_root) / scenario["scenario_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    args = [
        venv_python(), '-m', 'tools.run_scenario',
        '--experiment', scenario["experiment"],
        '--protocol', scenario["protocol"],
        '--n-drones', str(scenario["n_drones"]),
        '--speed', str(scenario["speed"]),
        '--initial-energy', str(scenario["initial_energy"]),
        '--sim-time-s', str(sim_time_s),
        '--seed', '2025',
        '--out-dir', str(out_dir),
        '--scenario-id', scenario["scenario_id"],
        '--logging-level', logging_level,
    ]
    stdout_f = open(out_dir / 'stdout.log', 'w')
    stderr_f = open(out_dir / 'stderr.log', 'w')
    env = dict(os.environ)
    env['MPLBACKEND'] = 'Agg'
    proc = subprocess.Popen(args, cwd=str(REPO_ROOT), env=env, stdout=stdout_f, stderr=stderr_f)
    return proc, stdout_f, stderr_f


def write_status(out_root, statuses):
    with open(Path(out_root) / 'status.json', 'w') as f:
        json.dump(statuses, f, indent=2)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--experiment', choices=['a', 'b', 'both'], default='both')
    p.add_argument('--workers', type=int, default=min(4, os.cpu_count() or 4))
    p.add_argument('--out-root', default=str(REPO_ROOT / 'results' / '120s'))
    p.add_argument('--sim-time-s', type=float, default=120)
    p.add_argument('--only-failed', action='store_true')
    p.add_argument('--logging-level', default='WARNING')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--scenario-ids', default=None,
                    help='Comma-separated subset of scenario_ids to run (for validation/targeted reruns).')
    p.add_argument('--exclude-scenario-ids', default=None,
                    help='Comma-separated scenario_ids to exclude from the matrix (e.g. to defer a slow tier).')
    args = p.parse_args()

    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    matrix = build_matrix(args.experiment)

    if args.scenario_ids:
        wanted = set(args.scenario_ids.split(','))
        matrix = [s for s in matrix if s["scenario_id"] in wanted]

    if args.exclude_scenario_ids:
        excluded = set(args.exclude_scenario_ids.split(','))
        matrix = [s for s in matrix if s["scenario_id"] not in excluded]

    if args.only_failed:
        matrix = [s for s in matrix if scenario_status(out_root, s["scenario_id"]) != "done"]

    if args.dry_run:
        for s in matrix:
            print(s["scenario_id"], s)
        print(f"Total: {len(matrix)} scenarios")
        return

    print(f"Launching {len(matrix)} scenarios with {args.workers} workers -> {out_root}")

    pending = list(matrix)
    running = {}  # scenario_id -> (proc, stdout_f, stderr_f, start_time)
    statuses = {s["scenario_id"]: "pending" for s in matrix}
    done_count = 0
    failed_count = 0
    t0 = time.time()
    last_report = 0

    while pending or running:
        while pending and len(running) < args.workers:
            scenario = pending.pop(0)
            proc, out_f, err_f = launch(scenario, out_root, args.sim_time_s, args.logging_level)
            running[scenario["scenario_id"]] = (proc, out_f, err_f, time.time())
            statuses[scenario["scenario_id"]] = "running"

        finished = []
        for sid, (proc, out_f, err_f, start_t) in running.items():
            ret = proc.poll()
            if ret is not None:
                out_f.close()
                err_f.close()
                st = scenario_status(out_root, sid)
                statuses[sid] = st if st != "pending" else "failed"
                if statuses[sid] == "done":
                    done_count += 1
                else:
                    failed_count += 1
                finished.append(sid)
        for sid in finished:
            del running[sid]

        write_status(out_root, statuses)

        now = time.time()
        if now - last_report > 10:
            print(f"[{now - t0:6.0f}s] done={done_count} failed={failed_count} "
                  f"running={len(running)} pending={len(pending)}", flush=True)
            last_report = now

        if pending or running:
            time.sleep(2)

    write_status(out_root, statuses)
    print(f"Matrix complete in {time.time() - t0:.0f}s: done={done_count} failed={failed_count}")
    if failed_count:
        failed_ids = [sid for sid, st in statuses.items() if st == "failed"]
        print("Failed scenarios:", failed_ids)


if __name__ == '__main__':
    main()
