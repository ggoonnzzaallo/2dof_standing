"""Search bounded waypoint motions in the exploratory simulator, never on hardware.

Cross-entropy optimization produces open-loop trajectories, not an RL policy.
All candidate commands pass through SelfRightingEnv.step and its servo dynamics.
"""
from pathlib import Path
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import sys
import time
import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from environment import SelfRightingEnv

CASES = {
    **{f'side_{angle:03d}': {'tilt':float(np.pi/2),'azimuth':float(np.deg2rad(angle))} for angle in range(0,360,45)},
    'inverted': {'tilt':float(np.pi),'azimuth':0.},
    'upright': {'tilt':0.,'azimuth':0.},
}
ENV = None
INITIAL = {}
STATE = mujoco.mjtState.mjSTATE_INTEGRATION


def initialize():
    global ENV
    ENV = SelfRightingEnv(randomize=False)


def restore(case,seed):
    key = (case,seed)
    if key not in INITIAL:
        ENV.reset(seed=seed,options=CASES[case])
        state = np.empty(mujoco.mj_stateSize(ENV.model,STATE))
        mujoco.mj_getState(ENV.model,ENV.data,state,STATE)
        INITIAL[key] = state
    mujoco.mj_resetData(ENV.model,ENV.data)
    mujoco.mj_setState(ENV.model,ENV.data,INITIAL[key],STATE)
    mujoco.mj_forward(ENV.model,ENV.data)
    ENV.command = np.zeros(2); ENV.servo_target = np.zeros(2); ENV.previous = np.zeros(2)
    ENV.queue = []; ENV.steps = 0; ENV.dwell = 0


def rollout(task,record=False,reset=True):
    case,seed,waypoints,segment,hold = task
    if reset:
        restore(case,seed)
    knots = np.vstack([np.zeros(2),waypoints,np.zeros(2)])
    times = np.arange(len(knots))*segment
    steps = round((times[-1]+hold)/.02)
    rewards,ups,joints = [],[],[]
    trace = {'observation':[],'action':[],'qpos':[],'qvel':[],'command':[],'upright':[],'reward':[]}
    success = False
    invalid = False
    for i in range(steps):
        target = np.array([np.interp((i+1)*.02,times,knots[:,j]) for j in range(2)])
        action = np.clip((target-ENV.command)/.06,-1,1).astype(np.float32)
        observation = ENV._obs()
        qpos,qvel = ENV.data.qpos.copy(),ENV.data.qvel.copy()
        _,reward,terminated,truncated,info = ENV.step(action)
        rewards.append(reward);ups.append(info['upright']);joints.append(ENV.data.qpos[-2:].copy())
        if record:
            for key,value in [('observation',observation),('action',action),('qpos',qpos),('qvel',qvel),
                              ('command',ENV.command.copy()),('upright',info['upright']),('reward',reward)]:
                trace[key].append(value)
        if any(w.number for w in ENV.data.warning):
            invalid = True
            break
        if terminated or truncated:
            success = bool(info['is_success'])
            invalid = terminated and not success
            break
    smooth = np.convolve(ups,np.ones(min(10,len(ups)))/min(10,len(ups)),mode='valid')
    score = (50*success - 20*invalid + np.mean(rewards) + 5*np.mean(ups[-25:])
             + np.max(smooth) - np.mean(np.abs(joints[-1])))
    result = {'score':float(score),'success':success,'invalid':bool(invalid),'steps':len(ups),
              'final_upright':float(ups[-1]),'best_smoothed_upright':float(np.max(smooth)),
              'final_joint_degrees':np.rad2deg(joints[-1]).tolist()}
    if record:
        trace = {k:np.asarray(v) for k,v in trace.items()}
        trace['final_qpos'] = ENV.data.qpos.copy()
        trace['waypoints_rad'] = np.asarray(waypoints)
        return result,trace
    return result


def search_case(args,case,pool):
    rng = np.random.default_rng(args.seed+list(CASES).index(case))
    shape = (args.knots,2)
    limit = ENV.limit
    mean = np.zeros(shape)
    std = np.full(shape,.95)
    best = np.zeros(shape)
    best_result = None
    history = []
    baseline = rollout((case,args.seed,np.zeros(shape),args.segment,args.hold))
    for iteration in range(args.iterations):
        population = np.clip(rng.normal(mean,std,(args.population,*shape)),-limit,limit)
        population[0] = best
        if iteration == 0:
            population[1] = 0
            # Seed broad bend/reverse motions as well as unconstrained samples.
            for i in range(2,min(10,len(population))):
                phase = (i-2)*np.pi/4
                population[i,:,0] = limit*np.sin(np.arange(args.knots)*np.pi/2+phase)
                population[i,:,1] = limit*np.cos(np.arange(args.knots)*np.pi/2+phase)
        tasks = [(case,args.seed,p,args.segment,args.hold) for p in population]
        results = list(pool.map(rollout,tasks)) if pool else [rollout(t) for t in tasks]
        order = np.argsort([r['score'] for r in results])[::-1]
        if best_result is None or results[order[0]]['score'] > best_result['score']:
            best_result = results[order[0]];best = population[order[0]].copy()
        elite = population[order[:max(4,args.population//6)]]
        mean = .25*mean + .75*elite.mean(axis=0)
        std = np.maximum(.12,.25*std+.75*elite.std(axis=0))
        row = {'iteration':iteration,'case':case,'best':best_result,
               'successful_candidates':sum(r['success'] for r in results)}
        history.append(row);print(json.dumps(row),flush=True)
    result,trace = rollout((case,args.seed,best,args.segment,args.hold),record=True)
    assert np.isclose(result['score'],best_result['score'],atol=1e-8), 'Worker/main replay differs.'
    np.savez_compressed(args.out/f'{case}.npz',**trace)
    initial_quat = trace['qpos'][0,3:7]
    return {'case':case,'requested_start':CASES[case],'settle_seconds_before_control':.8,
            'control_start_qpos':trace['qpos'][0].tolist(),
            'control_start_upright_cosine':float(1-2*(initial_quat[1]**2+initial_quat[2]**2)),
            'zero_motion_baseline':baseline,'result':result,'waypoints_rad':best.tolist(),
            'trace_file':f'{case}.npz','iterations':history}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',nargs='+',choices=list(CASES),default=['side_000','side_090','side_180','side_270'])
    parser.add_argument('--population',type=int,default=48)
    parser.add_argument('--iterations',type=int,default=6)
    parser.add_argument('--knots',type=int,default=6)
    parser.add_argument('--segment',type=float,default=.5)
    parser.add_argument('--hold',type=float,default=1.5)
    parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--seed',type=int,default=17)
    parser.add_argument('--out',type=Path,default=Path('runs/recovery_search'))
    args = parser.parse_args()
    assert args.population>=8 and args.iterations>=1 and args.knots>=1
    assert args.segment>0 and args.hold>=1
    args.out.mkdir(parents=True,exist_ok=True)
    initialize()
    start = time.monotonic()
    report = {'status':'Exploratory open-loop trajectory search; not a policy or hardware validation',
              'robot_xml_sha256':hashlib.sha256((HERE.parent/'robot.xml').read_bytes()).hexdigest(),
              'config':{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
              'success_definition':'Environment requires base upright within 10 degrees, joints near neutral, low angular rate and floor contact for one second',
              'adjacent_collision_audit':'Pending; candidates are not validated demonstrations for hardware transfer',
              'results':[],'physical_robot_commands_sent':False,'rl_training_performed':False}
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn'),initializer=initialize) if args.workers>1 else __import__('contextlib').nullcontext(None) as pool:
        for case in args.cases:
            report['results'].append(search_case(args,case,pool))
            report['wall_seconds'] = time.monotonic()-start
            (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Report: '+str(args.out/'report.json'),flush=True)


if __name__ == '__main__':
    main()
