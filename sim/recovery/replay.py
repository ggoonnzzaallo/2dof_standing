"""Record deterministic neural-controller trajectories in simulation."""
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
    parser.add_argument('--cases',nargs='+',choices=list(search.CASES),default=['side_000','inverted'])
    parser.add_argument('--out',type=Path,default=Path('runs/neural_replay'))
    args = parser.parse_args()
    torch.set_num_threads(1)
    model = PPO.load(args.model,device='cpu')
    audit = AdjacentAudit()
    args.out.mkdir(parents=True,exist_ok=True)
    results = []
    for case in args.cases:
        env = search.SelfRightingEnv(randomize=False)
        obs,_ = env.reset(seed=17,options=search.CASES[case])
        trace = {k:[] for k in ['qpos','qvel','observation','action']}
        for _ in range(500):
            action = model.predict(obs,deterministic=True)[0]
            trace['qpos'].append(env.data.qpos.copy());trace['qvel'].append(env.data.qvel.copy())
            trace['observation'].append(obs.copy());trace['action'].append(action.copy())
            obs,_,terminated,truncated,info = env.step(action)
            if terminated or truncated:
                break
        trace = {k:np.array(v) for k,v in trace.items()}
        trace['final_qpos'] = env.data.qpos.copy()
        np.savez_compressed(args.out/f'{case}.npz',**trace)
        results.append({'case':case,'requested_start':search.CASES[case],
                        'control_start_qpos':trace['qpos'][0].tolist(),'settle_seconds_before_control':.8,
                        'success':bool(info['is_success']),'seconds':len(trace['qpos'])*.02,
                        'adjacent_audit':audit.check(np.vstack([trace['qpos'],trace['final_qpos']])),
                        'trace_file':f'{case}.npz'})
        env.close()
    report = {'status':'Neural controller replay in simulation only','model_sha256':hashlib.sha256(args.model.read_bytes()).hexdigest(),
              'robot_xml_sha256':hashlib.sha256((search.HERE.parent/'robot.xml').read_bytes()).hexdigest(),
              'physical_robot_commands_sent':False,'results':results}
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
