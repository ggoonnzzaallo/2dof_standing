"""PPO for forceful C3 recovery; select on randomized weak/heavy/slippery cases."""
from pathlib import Path
import argparse,csv,hashlib,json,os,time
os.environ.setdefault('MPLCONFIGDIR','/tmp/2dof-mpl-cache')
from robust_env import RobustEnv,HERE
import numpy as np,torch
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv,VecNormalize

def evaluate(actor,seeds,seconds=20,retries=True):
    env=RobustEnv(retries=retries);rows=[]
    try:
        for seed in seeds:
            rng=np.random.default_rng(seed)
            pose={'tilt':float(rng.uniform(.8,np.pi)),'azimuth':float(rng.uniform(0,2*np.pi))}
            obs,_=env.reset(seed=seed,options=pose);first=None;fault=False
            mass=float(env.model.body_mass.sum());fric=env.friction;torque=env.torque
            for i in range(round(seconds/.02)):
                obs,_,t,_,info=env.step(actor.predict(obs,deterministic=True)[0])
                if info['is_success']:first=(i+1)*.02;break
                if info['control_fault'] or any(w.number for w in env.data.warning):fault=True;break
            rows.append({'seed':seed,'pose':pose,'first_stable_s':first,'fault':fault,'max_target_deg':float(np.rad2deg(env.max_target)),
                         'retries':env.strategy.retries,'mass_g':mass*1000,'friction':fric,'servo_torque_Nm':torque,'speed_rad_s':env.speed,
                         'final_up':float(info['upright'])})
    finally:env.close()
    return {'episodes':len(rows),'successes':sum(r['first_stable_s'] is not None for r in rows),'faults':sum(r['fault'] for r in rows),
            'successes_by_5s':sum(r['first_stable_s'] is not None and r['first_stable_s']<=5 for r in rows),
            'mean_capped_recovery_s':float(np.mean([r['first_stable_s'] or seconds for r in rows])),'trials':rows}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--steps',type=int,default=262144);p.add_argument('--seed',type=int,default=83)
    p.add_argument('--warm-start',type=Path,default=HERE.parent/'results/best.zip');p.add_argument('--out',type=Path,default=Path('runs/c3_robust_seed83'))
    p.add_argument('--envs',type=int,default=3);p.add_argument('--evaluate',type=Path);p.add_argument('--episodes',type=int,default=50);p.add_argument('--first-seed',type=int,default=69000)
    p.add_argument('--no-retries',action='store_true');a=p.parse_args();torch.set_num_threads(1)
    if a.evaluate:
        r=evaluate(PPO.load(a.evaluate,device='cpu'),range(a.first_seed,a.first_seed+a.episodes),retries=not a.no_retries)
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='trials'},indent=2),flush=True);return
    a.out.mkdir(parents=True,exist_ok=True)
    env=make_vec_env(RobustEnv,n_envs=a.envs,seed=a.seed,vec_env_cls=SubprocVecEnv,vec_env_kwargs={'start_method':'spawn'},monitor_dir=str(a.out/'episodes'),
                     monitor_kwargs={'info_keywords':('episode_recovered','control_fault','retry_count','max_target_deg')})
    env=VecNormalize(env,norm_obs=False,norm_reward=True,clip_reward=10,gamma=.995)
    model=PPO('MlpPolicy',env,n_steps=512,batch_size=128,device='cpu',seed=a.seed,gamma=.995,gae_lambda=.95,
              policy_kwargs={'net_arch':{'pi':[64,64],'vf':[64,64]},'activation_fn':torch.nn.Tanh},learning_rate=8e-5,clip_range=.12,ent_coef=.015,verbose=0)
    src=PPO.load(a.warm_start,device='cpu');model.policy.mlp_extractor.policy_net.load_state_dict(src.policy.mlp_extractor.policy_net.state_dict());model.policy.action_net.load_state_dict(src.policy.action_net.state_dict())
    with torch.no_grad():model.policy.log_std.fill_(-.8)
    r={'date':'2026-11-07','status':'offline robust C3 training','config':{**{k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},'filtered':True,'action_increment_rad':.1,'retry_supervisor':True},
       'robot_xml_sha256':hashlib.sha256((HERE/'robot.xml').read_bytes()).hexdigest(),'strategy_sha256':hashlib.sha256((HERE.parents[2]/'firmware/policy_control/RecoveryStrategy.h').read_bytes()).hexdigest(),
       'environment_sha256':hashlib.sha256((HERE/'robust_env.py').read_bytes()).hexdigest(),'training_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       'warm_start_sha256':hashlib.sha256(a.warm_start.read_bytes()).hexdigest(),'stages':[],'selected_actual_steps':0}
    start=time.monotonic();last=0;best=(-1,-1e9)
    for steps in [0]+list(range(32768,a.steps+1,32768)):
        if steps:model.learn(total_timesteps=steps-last,reset_num_timesteps=False);last=steps
        score=evaluate(model,range(65000,65020));key=(score['successes'],-score['mean_capped_recovery_s'])
        r['stages'].append({'actual_steps':model.num_timesteps,'evaluation':score})
        if key>best:best=key;model.save(a.out/'best');r['selected_actual_steps']=model.num_timesteps
        model.save(a.out/f'checkpoint_{model.num_timesteps:06d}');env.save(str(a.out/f'return_normalization_{model.num_timesteps:06d}.pkl'))
        completed=[]
        for f in (a.out/'episodes').glob('*.monitor.csv'):
            with f.open() as s:next(s);completed.extend(csv.DictReader(s))
        r['completed_episodes']=len(completed);r['recovered_episodes']=sum(row['episode_recovered']=='True' for row in completed);r['faulted_episodes']=sum(row['control_fault']=='True' for row in completed)
        r['wall_seconds']=time.monotonic()-start;(a.out/'training_report.json').write_text(json.dumps(r,indent=2)+'\n')
        print(json.dumps({'steps':model.num_timesteps,**{k:v for k,v in score.items() if k!='trials'},'selected':r['selected_actual_steps'],'completed_training_episodes':len(completed),'wall_seconds':r['wall_seconds']}),flush=True)
    env.close()
if __name__=='__main__':main()
