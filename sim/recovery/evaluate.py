"""Evaluate a saved simulation policy on new tilt/azimuth samples (not uniform SO(3))."""
from pathlib import Path
import argparse
import hashlib
import json
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/2dof-mpl-cache')
import numpy as np
import torch
from stable_baselines3 import PPO
import search
from audit import AdjacentAudit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model',type=Path)
    parser.add_argument('--episodes',type=int,default=100)
    parser.add_argument('--out',type=Path,default=Path('runs/recovery_policy_seed17/broad_evaluation.json'))
    args = parser.parse_args()
    torch.set_num_threads(1)
    model = PPO.load(args.model,device='cpu')
    audit = AdjacentAudit()
    rows = []
    for episode in range(args.episodes):
        seed = 9000+episode
        rng = np.random.default_rng(seed)
        options = {'tilt':float(rng.uniform(0,np.pi)),'azimuth':float(rng.uniform(0,2*np.pi))}
        env = search.SelfRightingEnv(randomize=True)
        obs,_ = env.reset(seed=seed,options=options)
        initial = env.data.qpos.copy()
        positions = []
        for step in range(500):
            positions.append(env.data.qpos.copy())
            obs,_,terminated,truncated,info = env.step(model.predict(obs,deterministic=True)[0])
            if terminated or truncated:
                break
        positions.append(env.data.qpos.copy())
        collision = audit.check(np.array(positions))
        warning_count = sum(int(w.number) for w in env.data.warning)
        valid = warning_count==0 and np.isfinite(env.data.qpos).all() and np.isfinite(env.data.qvel).all()
        rows.append({'seed':seed,'requested_start':options,'control_start_qpos':initial.tolist(),
                     'success':bool(info['is_success'] and valid),'mujoco_warning_count':warning_count,
                     'seconds':(step+1)*.02,'adjacent_audit':collision})
        env.close()
    report = {'status':'Exploratory simulation evaluation; not physical validation',
              'model_sha256':hashlib.sha256(args.model.read_bytes()).hexdigest(),
              'robot_xml_sha256':hashlib.sha256((search.HERE.parent/'robot.xml').read_bytes()).hexdigest(),
              'episodes':len(rows),'successes':sum(r['success'] for r in rows),
              'successful_and_audit_passed':sum(r['success'] and r['adjacent_audit']['status']=='passed' for r in rows),
              'pose_sampling':'Requested tilt uniform [0, pi], rotation-axis azimuth uniform [0, 2pi]; not uniform SO(3). Each reset then settles for 0.8 seconds.',
              'randomization':'Existing exploratory mass/friction/servo delay, speed, torque, gain and observation noise; not calibrated physical uncertainty.',
              'seeds':'9000 onward, distinct from demonstration/development/final scripted-case tests',
              'physical_robot_commands_sent':False,'trials':rows}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='trials'},indent=2),flush=True)


if __name__=='__main__':
    main()
