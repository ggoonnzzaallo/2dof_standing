"""Compare C3 policies with the firmware IMU filter; no robot I/O.

Standard cases are development diagnostics. Use fresh seeds only after selection.
Historical strict success and base-only recovery are both reported.
"""
from pathlib import Path
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib,json,multiprocessing,os,sys,time
HERE=Path(__file__).resolve().parent
os.environ['ROBOT_MODEL_PATH']=str(HERE/'robot.xml')
os.environ.setdefault('MPLCONFIGDIR','/tmp/2dof-mpl-cache')
sys.path.insert(0,str(HERE.parent/'recovery'))
import numpy as np
import torch
from stable_baselines3 import PPO
import search
from evaluate_filter import FilteredEnv

ENV=None;ACTOR=None

def initialize(actor):
    global ENV,ACTOR
    torch.set_num_threads(1)
    ENV=FilteredEnv(randomize=True)
    ACTOR=PPO.load(actor,device='cpu')

def trial(task):
    label,seed,options,randomize,seconds=task
    ENV.randomize=randomize
    obs,_=ENV.reset(seed=seed,options=options)
    dwell=0;first_base=None;first_strict=None;failure=None;targets=[]
    for frame in range(round(seconds/.02)):
        action=ACTOR.predict(obs,deterministic=True)[0]
        obs,_,terminated,truncated,info=ENV.step(action)
        base_good=(info['upright']>np.cos(np.deg2rad(10)) and np.linalg.norm(ENV.data.sensor('gyro').data)<.4 and
                   any((c.geom1==ENV.floor_id and ENV.model.geom_bodyid[c.geom2]==ENV.base_id) or
                       (c.geom2==ENV.floor_id and ENV.model.geom_bodyid[c.geom1]==ENV.base_id) for c in ENV.data.contact))
        dwell=dwell+1 if base_good else 0
        if dwell>=50 and first_base is None:first_base=(frame+1)*.02
        if info['is_success']:
            first_strict=(frame+1)*.02;break
        if info.get('filter_fault') or (terminated and not info['is_success']):failure='filter_or_invalid_state';break
        if any(w.number for w in ENV.data.warning):failure='physics_warning';break
        targets.append(ENV.command.copy())
    return {'case':label,'seed':seed,'requested_pose':options,'randomized':randomize,
            'first_base_only_stable_s':first_base,'first_strict_success_s':first_strict,
            'seconds':(frame+1)*.02,'failure':failure,'final_upright':float(info['upright']),
            'final_command_deg':np.rad2deg(ENV.command).tolist(),
            'final_true_joints_deg':np.rad2deg(ENV.data.qpos[-2:]).tolist(),
            'mujoco_warnings':sum(int(w.number) for w in ENV.data.warning)}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('actor',type=Path);ap.add_argument('--suite',choices=['standard','fresh'],default='standard')
    ap.add_argument('--seconds',type=float,default=20);ap.add_argument('--workers',type=int,default=3)
    ap.add_argument('--episodes',type=int,default=30);ap.add_argument('--seed',type=int,default=47000)
    ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    tasks=[]
    if args.suite=='standard':
        for mode,start in [('nominal',100),('development',3000)]:
            for i,(name,pose) in enumerate(search.CASES.items()):
                seed=start+i*100;options=dict(pose);rng=np.random.default_rng(seed)
                if mode!='nominal':
                    options['tilt']+=np.deg2rad(rng.uniform(-10,10));options['azimuth']+=np.deg2rad(rng.uniform(-10,10))
                tasks.append((mode+'/'+name,seed,options,mode!='nominal',args.seconds))
    else:
        for i in range(args.episodes):
            seed=args.seed+i;rng=np.random.default_rng(seed)
            tasks.append(('fresh',seed,{'tilt':float(rng.uniform(0,np.pi)),'azimuth':float(rng.uniform(0,2*np.pi))},True,args.seconds))
    start=time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn'),initializer=initialize,initargs=(str(args.actor),)) as pool:
        rows=[]
        for row in pool.map(trial,tasks):
            rows.append(row);print(row['case'],row['first_base_only_stable_s'],row['first_strict_success_s'],row['failure'],flush=True)
    r={'status':'offline simulation, not physical validation','suite':args.suite,'horizon_seconds':args.seconds,
       'actor_sha256':hashlib.sha256(args.actor.read_bytes()).hexdigest(),
       'robot_xml_sha256':hashlib.sha256((HERE/'robot.xml').read_bytes()).hexdigest(),
       'filter_header_sha256':hashlib.sha256((HERE.parents[1]/'firmware/policy_shadow/GravityFilter.h').read_bytes()).hexdigest(),
       'episodes':len(rows),'metrics':{str(t):{key:sum(row[key] is not None and row[key]<=t and not row['failure'] for row in rows) for key in ('first_base_only_stable_s','first_strict_success_s')} for t in (10,args.seconds)},
       'faults':sum(bool(row['failure']) for row in rows),'wall_seconds':time.monotonic()-start,
       'trials':rows,'physical_robot_commands_sent':False}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='trials'},indent=2),flush=True)
if __name__=='__main__':main()
