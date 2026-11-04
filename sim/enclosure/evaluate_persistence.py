"""Continue the saved actor past the old 10 s cutoff, without resets or retries.

Report both base-only stable recovery and the historical straight-joint goal.
Simulation only: no serial, upload or physical motion.
"""
from pathlib import Path
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
import sys
os.environ.setdefault('MPLCONFIGDIR', '/tmp/2dof-mpl-cache')
HERE = Path(__file__).resolve().parent
os.environ['ROBOT_MODEL_PATH'] = str(HERE/'robot.xml')
sys.path.insert(0, str(HERE.parent/'recovery'))
import numpy as np
import torch
from stable_baselines3 import PPO
import search
from evaluate_filter import FilteredEnv
from filter_runtime import FilterRuntime


def requests():
    rows = []
    for mode in ('nominal', 'development'):
        for index, (case, pose) in enumerate(search.CASES.items()):
            seed = (100 if mode == 'nominal' else 3000)+index*100
            pose = dict(pose)
            if mode != 'nominal':
                rng = np.random.default_rng(seed)
                pose['tilt'] += np.deg2rad(rng.uniform(-10, 10))
                pose['azimuth'] += np.deg2rad(rng.uniform(-10, 10))
            rows.append({'mode': mode, 'case': case, 'seed': seed, 'requested_start': pose})
    return rows


def evaluate_chunk(task):
    rows, actor_path, horizon = task
    torch.set_num_threads(1)
    actor = PPO.load(actor_path, device='cpu')
    runtime = FilterRuntime()
    results = []
    for request in rows:
        env = FilteredEnv(runtime=runtime, randomize=request['mode'] != 'nominal')
        obs, _ = env.reset(seed=request['seed'], options=request['requested_start'])
        first_base = first_strict = None
        base_dwell = 0
        termination = 'horizon'
        path = []
        # Historical terminated/truncated success/time flags are measurements,
        # not reasons to stop this test. Only faults stop control early.
        for frame in range(round(horizon/.02)):
            obs, _, terminated, _, info = env.step(actor.predict(obs, deterministic=True)[0])
            seconds = (frame+1)*.02
            contact = any(
                (c.geom1 == env.floor_id and env.model.geom_bodyid[c.geom2] == env.base_id)
                or (c.geom2 == env.floor_id and env.model.geom_bodyid[c.geom1] == env.base_id)
                for c in env.data.contact)
            base_good = (info['upright'] > np.cos(np.deg2rad(10)) and contact
                         and np.linalg.norm(env.data.sensor('gyro').data) < .4)
            base_dwell = base_dwell+1 if base_good else 0
            if base_dwell >= 50 and first_base is None:
                first_base = seconds
            if info['is_success'] and first_strict is None:
                first_strict = seconds
            finite = np.isfinite(env.data.qpos).all() and np.isfinite(env.data.qvel).all()
            warnings = sum(int(w.number) for w in env.data.warning)
            if info.get('filter_fault') or not finite or warnings or (terminated and not info['is_success']):
                termination = 'filter_fault' if info.get('filter_fault') else 'invalid_or_numerical_fault'
                break
            path.append(env.data.qpos[-2:].copy())
            if first_strict is not None:
                termination = 'strict_goal_reached'
                break
        samples = np.asarray(path[-251:])
        tail_travel = np.sum(np.abs(np.diff(samples, axis=0)), axis=0) if len(samples) > 1 else np.zeros(2)
        row = {**request, 'first_base_only_stable_s': first_base,
               'first_strict_success_s': first_strict, 'controlled_seconds': seconds,
               'termination': termination, 'final_base_tilt_deg': float(np.rad2deg(np.arccos(np.clip(info['upright'], -1, 1)))),
               'final_joint_angles_deg': np.rad2deg(env.data.qpos[-2:]).tolist(),
               'last_up_to_5s_joint_travel_deg': np.rad2deg(tail_travel).tolist(),
               'mujoco_warnings': sum(int(w.number) for w in env.data.warning)}
        results.append(row)
        print(json.dumps({'case': request['case'], 'mode': request['mode'],
                          'base_s': first_base, 'strict_s': first_strict, 'end': termination}), flush=True)
        env.close()
    runtime.close()
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=60.)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--actor', type=Path, default=HERE/'results/best.zip')
    parser.add_argument('--out', type=Path, default=HERE/'results/persistence_evaluation.json')
    args = parser.parse_args()
    assert args.seconds >= 10 and 1 <= args.workers <= 3
    cases = requests()
    tasks = [(cases[i::args.workers], str(args.actor.resolve()), args.seconds) for i in range(args.workers)]
    if args.workers == 1:
        chunks = [evaluate_chunk(tasks[0])]
    else:
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=multiprocessing.get_context('spawn')) as pool:
            chunks = list(pool.map(evaluate_chunk, tasks))
    order = {(r['mode'], r['case']): i for i, r in enumerate(cases)}
    trials = sorted([r for chunk in chunks for r in chunk], key=lambda r: order[r['mode'], r['case']])
    thresholds = sorted(set([10., 30., args.seconds]))
    metrics = {str(int(t)): {
        'base_only_stable': sum(r['first_base_only_stable_s'] is not None and r['first_base_only_stable_s'] <= t for r in trials),
        'strict_success': sum(r['first_strict_success_s'] is not None and r['first_strict_success_s'] <= t for r in trials)} for t in thresholds if t <= args.seconds}
    output = {'status': 'Offline diagnostic; does not retrain, select or upload weights',
              'actor_sha256': hashlib.sha256(args.actor.read_bytes()).hexdigest(),
              'robot_xml_sha256': hashlib.sha256((HERE/'robot.xml').read_bytes()).hexdigest(),
              'horizon_seconds': args.seconds, 'episodes': len(trials), 'metrics_at_seconds': metrics,
              'base_only_goal': 'Base tilt <10 deg, base-floor contact, base angular speed <0.4 rad/s for 1 continuous second; joints unrestricted',
              'strict_goal': 'Same base goal plus both joints <0.18 rad from neutral for 1 continuous second',
              'control': 'Unchanged deterministic actor; no reset, forced retry, altered observation or added exploration at 10 s. Stop at strict success or a fault, otherwise continue to horizon.',
              'time_origin': 'Policy start after sensor initialization and 0.8 s free settling',
              'interpretation': 'Finite-horizon results cannot prove eventual recovery or intent to give up. Joint travel is a motion diagnostic, not a recovery attempt count.',
              'physical_robot_commands_sent': False, 'trials': trials}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps({'episodes': len(trials), 'metrics_at_seconds': metrics, 'out': str(args.out)}), flush=True)


if __name__ == '__main__':
    main()
