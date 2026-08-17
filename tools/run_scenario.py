"""
Single-scenario driver for the 120s Experiment A/B rerun.

Runs exactly one (protocol, UAV count, speed, map size, energy) scenario in its own
process. Overrides `utils.config` attributes in-memory BEFORE importing
`simulator.simulator.Simulator` (mirroring the reproduction recipe already documented
in ExperimentC.md Section 6) so that no repository source file is ever modified on
disk. Collects overall (0-120s) metrics using the exact same formulas already present
in `simulator.metrics.Metrics.print_metrics`, plus independent per-window metrics by
snapshotting `sim.metrics` at four equally-spaced time checkpoints and diffing
consecutive snapshots -- also the technique ExperimentC.md Section 6 documents.

Intended to be invoked as its own OS subprocess (never imported and reused across
scenarios in one long-lived interpreter): `mobility/start_coords.py` seeds the global
`random` module per Simulator construction, and `utils.config`'s in-memory overrides
here are process-global, so scenario isolation depends on process isolation.
"""

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # must happen before any project import pulls in pyplot

import numpy as np


def parse_args():
    p = argparse.ArgumentParser(description="Run a single UAV routing scenario headlessly.")
    p.add_argument('--experiment', required=True, choices=['A', 'B'])
    p.add_argument('--protocol', required=True, choices=['dsdv', 'greedy', 'qgeo', 'cr_qgeo', 'macg'])
    p.add_argument('--n-drones', required=True, type=int)
    p.add_argument('--speed', required=True, type=float)
    p.add_argument('--map-length', type=float, default=600)
    p.add_argument('--map-width', type=float, default=600)
    p.add_argument('--map-height', type=float, default=100)
    p.add_argument('--sim-time-s', type=float, default=120)
    p.add_argument('--initial-energy', required=True, type=float)
    p.add_argument('--seed', type=int, default=2025)
    p.add_argument('--n-windows', type=int, default=4)
    p.add_argument('--out-dir', required=True)
    p.add_argument('--logging-level', default='WARNING')
    p.add_argument('--scenario-id', required=True)
    return p.parse_args()


def build_result_skeleton(args):
    return {
        "scenario_id": args.scenario_id,
        "experiment": args.experiment,
        "protocol": args.protocol,
        "params": {
            "n_drones": args.n_drones,
            "speed": args.speed,
            "map_length": args.map_length,
            "map_width": args.map_width,
            "map_height": args.map_height,
            "initial_energy": args.initial_energy,
            "seed": args.seed,
            "sim_time_s": args.sim_time_s,
            "n_windows": args.n_windows,
        },
        "status": "failed",
        "overall": None,
        "windows": None,
        "energy_validation": None,
        "wall_clock_seconds": None,
    }


def safe_mean(values):
    return float(np.mean(values)) if len(values) > 0 else None


def make_window_record(index, start_us, end_us, generated, new_ids, deliver_time_dict,
                        throughput_dict, hop_cnt_dict, collisions, control_packets,
                        mac_delay_values):
    delivered = len(new_ids)
    delay_values = [deliver_time_dict[pid] / 1e3 for pid in new_ids]
    throughput_values = [throughput_dict[pid] / 1e3 for pid in new_ids]
    hop_values = [hop_cnt_dict[pid] for pid in new_ids]
    return {
        "window_index": index,
        "label": f"{start_us / 1e6:.0f}-{end_us / 1e6:.0f}s",
        "start_s": start_us / 1e6,
        "end_s": end_us / 1e6,
        "generated": generated,
        "delivered": delivered,
        "pdr_pct": (delivered / generated * 100) if generated > 0 else None,
        "avg_e2e_delay_ms": safe_mean(delay_values),
        "avg_throughput_kbps": safe_mean(throughput_values),
        "avg_hop_count": safe_mean(hop_values),
        "collisions": collisions,
        "control_packets_sent": control_packets,
        "routing_load": (control_packets / delivered) if delivered > 0 else None,
        "avg_mac_delay_ms": safe_mean(mac_delay_values),
    }


def window_checkpoint_collector(env, sim, windows_out, checkpoint_state, n_windows):
    """Snapshot sim.metrics at n_windows-1 intermediate checkpoints and diff consecutively.

    Same technique ExperimentC.md Section 6 documents: because simpy is single-threaded
    and processes events in time order, dict insertion order / list append order are
    time-ordered, so a plain checkpoint-diff correctly attributes generated packets to
    the window containing their creation time and delivered packets (+ their delay/
    throughput/hop-count/mac-delay/collision/control-packet events) to the window
    containing their arrival time -- with zero changes to simulator/metrics.py.

    Only the first n_windows-1 boundaries are scheduled here: simpy's env.run(until=X)
    does not reliably fire an event scheduled at exactly time X (confirmed empirically:
    a checkpoint scheduled at the final boundary silently never ran), so the LAST window
    is instead computed in main() after env.run() returns, by diffing the final overall
    state against the cumulative state exposed here via `checkpoint_state`.
    """
    total = sim.total_simulation_time
    prev_generated = 0
    prev_delivered_ids = set()
    prev_collision = 0
    prev_control = 0
    prev_mac_len = 0
    prev_boundary = 0.0

    for i in range(1, n_windows):
        boundary = total * i / n_windows
        delay = boundary - env.now
        if delay > 0:
            yield env.timeout(delay)

        cur_generated = sim.metrics.datapacket_generated_num
        cur_delivered_ids = set(sim.metrics.deliver_time_dict.keys())
        cur_collision = sim.metrics.collision_num
        cur_control = sim.metrics.control_packet_num
        cur_mac_len = len(sim.metrics.mac_delay)

        new_ids = cur_delivered_ids - prev_delivered_ids
        windows_out.append(make_window_record(
            i, prev_boundary, boundary, cur_generated - prev_generated, new_ids,
            sim.metrics.deliver_time_dict, sim.metrics.throughput_dict, sim.metrics.hop_cnt_dict,
            cur_collision - prev_collision, cur_control - prev_control,
            sim.metrics.mac_delay[prev_mac_len:cur_mac_len],
        ))

        prev_generated = cur_generated
        prev_delivered_ids = cur_delivered_ids
        prev_collision = cur_collision
        prev_control = cur_control
        prev_mac_len = cur_mac_len
        prev_boundary = boundary

    checkpoint_state.update({
        "prev_generated": prev_generated,
        "prev_delivered_ids": prev_delivered_ids,
        "prev_collision": prev_collision,
        "prev_control": prev_control,
        "prev_mac_len": prev_mac_len,
        "prev_boundary": prev_boundary,
    })


def energy_poller(env, sim, energy_state, poll_interval_us=1e6):
    """Pure-read poll of drone.sleep / drone.residual_energy for diagnostic validation.

    Only needed to catch the *first* sleep transition time at reasonable (1s) precision;
    final state is read directly off sim.drones after env.run() returns without polling.
    """
    energy_state["first_sleep_time_s"] = None
    energy_state["first_sleep_drone_id"] = None
    energy_state["min_residual_energy_seen_j"] = min(d.residual_energy for d in sim.drones)
    prev_sleep = {d.identifier: d.sleep for d in sim.drones}

    while True:
        yield env.timeout(poll_interval_us)
        cur_min = min(d.residual_energy for d in sim.drones)
        if cur_min < energy_state["min_residual_energy_seen_j"]:
            energy_state["min_residual_energy_seen_j"] = cur_min
        for d in sim.drones:
            if d.sleep and not prev_sleep.get(d.identifier, False):
                if energy_state["first_sleep_time_s"] is None:
                    energy_state["first_sleep_time_s"] = env.now / 1e6
                    energy_state["first_sleep_drone_id"] = d.identifier
            prev_sleep[d.identifier] = d.sleep


def main():
    args = parse_args()
    assert args.seed == 2025, "This experiment rerun must use seed=2025 for every run."

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = build_result_skeleton(args)
    start_wall = time.time()

    try:
        # Step 1: override utils.config BEFORE importing anything that reads it,
        # so every downstream module (routing/, mac/, phy/, entities/drone.py) sees
        # the scenario's values with zero source-file changes.
        import utils.config as config

        config.NUMBER_OF_DRONES = args.n_drones
        config.DRONE_SPEED = args.speed
        config.MAP_LENGTH = args.map_length
        config.MAP_WIDTH = args.map_width
        config.MAP_HEIGHT = args.map_height
        config.SIM_TIME = args.sim_time_s * 1e6
        config.INITIAL_ENERGY = args.initial_energy
        config.ROUTING_PROTOCOL = args.protocol
        config.LOGGING_LEVEL = getattr(__import__('logging'), args.logging_level.upper())

        # Recompute the two constants that utils/config.py derives at its own
        # module-import time from values we just swept.
        config.MAX_TTL = config.NUMBER_OF_DRONES + 1
        config.MACG_MAX_VELOCITY_DIFFERENCE = 2 * config.DRONE_SPEED

        # Step 2: claim the root logger with an absolute, per-scenario path before
        # simulator.log's own basicConfig() (a no-op once handlers exist) runs.
        import logging
        logging.basicConfig(
            filename=str(out_dir / 'running_log.log'),
            filemode='w',
            format='%(levelname)s - %(message)s',
            level=config.LOGGING_LEVEL,
        )

        # Step 3: only now import the simulator, so it picks up the overridden config.
        import simpy
        from simulator.simulator import Simulator

        env = simpy.Environment()
        channel_states = {i: simpy.Resource(env, capacity=1) for i in range(config.NUMBER_OF_DRONES)}
        sim = Simulator(
            seed=2025,
            env=env,
            channel_states=channel_states,
            n_drones=config.NUMBER_OF_DRONES,
            total_simulation_time=config.SIM_TIME,
        )

        windows_out = []
        checkpoint_state = {}
        energy_state = {}
        env.process(window_checkpoint_collector(env, sim, windows_out, checkpoint_state, args.n_windows))
        env.process(energy_poller(env, sim, energy_state))

        env.run(until=config.SIM_TIME)

        # Overall metrics -- identical formulas to Metrics.print_metrics, just read
        # directly instead of only printed.
        m = sim.metrics
        n_delivered = len(m.datapacket_arrived)

        # Final window: diff the final cumulative state against the last intermediate
        # checkpoint (env.run(until=X) does not reliably fire an event scheduled at
        # exactly X, so this boundary is computed here instead of inside the process).
        final_delivered_ids = set(m.deliver_time_dict.keys())
        new_ids = final_delivered_ids - checkpoint_state.get("prev_delivered_ids", set())
        windows_out.append(make_window_record(
            args.n_windows, checkpoint_state.get("prev_boundary", 0.0), config.SIM_TIME,
            m.datapacket_generated_num - checkpoint_state.get("prev_generated", 0), new_ids,
            m.deliver_time_dict, m.throughput_dict, m.hop_cnt_dict,
            m.collision_num - checkpoint_state.get("prev_collision", 0),
            m.control_packet_num - checkpoint_state.get("prev_control", 0),
            m.mac_delay[checkpoint_state.get("prev_mac_len", 0):],
        ))
        overall = {
            "packets_generated": m.datapacket_generated_num,
            "packets_delivered": n_delivered,
            "pdr_pct": (n_delivered / m.datapacket_generated_num * 100) if m.datapacket_generated_num > 0 else None,
            "avg_e2e_delay_ms": safe_mean([v / 1e3 for v in m.deliver_time_dict.values()]),
            "routing_load": (m.control_packet_num / n_delivered) if n_delivered > 0 else None,
            "avg_throughput_kbps": safe_mean([v / 1e3 for v in m.throughput_dict.values()]),
            "avg_hop_count": safe_mean(list(m.hop_cnt_dict.values())),
            "collisions": m.collision_num,
            "avg_mac_delay_ms": safe_mean(m.mac_delay),
            "control_packets_sent": m.control_packet_num,
        }

        final_residuals = [d.residual_energy for d in sim.drones]
        final_sleeping = [d.sleep for d in sim.drones]
        num_sleeping_at_end = sum(1 for s in final_sleeping if s)
        energy_validation = {
            "any_drone_slept": (num_sleeping_at_end > 0) or (energy_state.get("first_sleep_time_s") is not None),
            "first_sleep_time_s": energy_state.get("first_sleep_time_s"),
            "first_sleep_drone_id": energy_state.get("first_sleep_drone_id"),
            "min_final_residual_energy_j": min(final_residuals),
            "avg_final_residual_energy_j": float(np.mean(final_residuals)),
            "num_sleeping_drones_at_end": num_sleeping_at_end,
            "min_residual_energy_seen_j": energy_state.get("min_residual_energy_seen_j"),
        }

        result["overall"] = overall
        result["windows"] = windows_out
        result["energy_validation"] = energy_validation
        result["status"] = "ok"

    except Exception:
        (out_dir / 'error.txt').write_text(traceback.format_exc())
        result["status"] = "failed"

    result["wall_clock_seconds"] = time.time() - start_wall

    with open(out_dir / 'result.json', 'w') as f:
        json.dump(result, f, indent=2)

    print(json.dumps({"scenario_id": args.scenario_id, "status": result["status"],
                       "wall_clock_seconds": result["wall_clock_seconds"]}))

    if result["status"] != "ok":
        sys.exit(1)


if __name__ == '__main__':
    main()
