"""C3-matched persistent recovery PPO; keeps observations/MCU actor contract fixed.

Only simulation. New reward: stable base first; neutral joints a soft preference.
Episodes continue after recovery, including mild disturbances, with no give-up
termination after a failed attempt. Historical strict scores remain separate.
"""
from pathlib import Path
import argparse,csv,hashlib,json,os,sys,time
HERE=Path(__file__).resolve().parent
os.environ['ROBOT_MODEL_PATH']=str(HERE/'robot.xml')
os.environ.setdefault('MPLCONFIGDIR','/tmp/2dof-mpl-cache')
sys.path.insert(0,str(HERE.parent/'recovery'))
import mujoco
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv,VecNormalize
from stable_baselines3.common.monitor import Monitor
from evaluate_filter import FilteredEnv

class PersistentEnv(FilteredEnv):
    def before_settle(self):
        # Trapped/ongoing recovery states can have bent joints and stored targets.
        # Match all latent command state; do not expose true joint angles to actor.
        if self.randomize and self.np_random.random()<.25:
            q=self.np_random.uniform(-.9,.9,2)
            self.data.qpos[-2:]=q;self.command=q.copy();self.servo_target=q.copy()
            self.queue=[q.copy() for _ in range(self.delay)]
            mujoco.mj_forward(self.model,self.data)
        super().before_settle()
    def reset(self,seed=None,options=None):
        obs,info=super().reset(seed=seed,options=options)
        self.base_dwell=0;self.recovery_rewarded=False
        return obs,info
    def step(self,action):
        old=self.previous.copy();before=float(self.data.xmat[self.base_id].reshape(3,3)[2,2])
        self.data.xfrc_applied[:]=0
        # Continue learning after success; small physical impulses rather than resets.
        if self.randomize and self.steps in (250,251,252,500,501,502):
            self.data.xfrc_applied[self.model.body('upper').id,:2]=self.np_random.uniform(-.22,.22,2)
        obs,_,terminated,_,info=super().step(action)
        upright=float(info['upright']);gyro=self.data.sensor('gyro').data
        contact=any((c.geom1==self.floor_id and self.model.geom_bodyid[c.geom2]==self.base_id) or
                    (c.geom2==self.floor_id and self.model.geom_bodyid[c.geom1]==self.base_id) for c in self.data.contact)
        good=upright>np.cos(np.deg2rad(10)) and np.linalg.norm(gyro)<.4 and contact
        self.base_dwell=self.base_dwell+1 if good else 0
        base_success=self.base_dwell>=50
        q=self.data.qpos[-2:];a=np.clip(action,-1,1)
        reward=2.5*upright+1.5*good+.25*np.exp(-3*np.sum(q*q))*max(upright,0)
        reward+=10*(.995*upright-before)
        reward-=.02*float(a@a)+.02*float((a-old)@(a-old))+.001*float(gyro@gyro)
        if base_success and not self.recovery_rewarded:reward+=100;self.recovery_rewarded=True
        invalid=info.get('filter_fault',False) or (terminated and not info['is_success'])
        if invalid:reward-=50
        return obs,float(reward),bool(invalid),self.steps>=1000,{**info,'is_success':base_success,'strict_success':bool(info['is_success']),'episode_recovered':self.recovery_rewarded,'control_fault':bool(invalid)}

def standard_score(actor):
    # Evaluation uses the historical filtered dynamics/goals, not the new reward.
    import importlib.util
    spec=importlib.util.spec_from_file_location('c3_evaluation',HERE/'evaluate.py')
    e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
    e.ENV=FilteredEnv(randomize=True);e.ACTOR=actor
    rows=[]
    try:
        for mode,start in [('nominal',100),('development',3000)]:
            for i,(name,pose) in enumerate(e.search.CASES.items()):
                seed=start+i*100;options=dict(pose);rng=np.random.default_rng(seed)
                if mode!='nominal':
                    options['tilt']+=np.deg2rad(rng.uniform(-10,10));options['azimuth']+=np.deg2rad(rng.uniform(-10,10))
                rows.append(e.trial((mode+'/'+name,seed,options,mode!='nominal',15.)))
    finally:e.ENV.close()
    base=sum(r['first_base_only_stable_s'] is not None and not r['failure'] for r in rows)
    strict=sum(r['first_strict_success_s'] is not None and not r['failure'] for r in rows)
    return {'base_successes':base,'strict_successes':strict,'episodes':len(rows),'trials':rows}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--warm-start',type=Path,default=HERE.parent/'enclosure/results/best.zip')
    ap.add_argument('--steps',type=int,default=196608);ap.add_argument('--envs',type=int,default=3)
    ap.add_argument('--seed',type=int,default=71);ap.add_argument('--out',type=Path,default=Path('runs/enclosure_c3_persistent_seed71'))
    ap.add_argument('--check-env',action='store_true');args=ap.parse_args()
    torch.set_num_threads(1);torch.manual_seed(args.seed)
    if args.check_env:
        from gymnasium.utils.env_checker import check_env
        e=PersistentEnv();check_env(e,skip_render_check=True)
        o,_=e.reset(seed=71)
        for i in range(1100):
            o,r,t,tr,info=e.step(np.zeros(2,dtype=np.float32))
            assert np.isfinite(o).all() and np.isfinite(r)
            if t or tr:o,_=e.reset(seed=i+100)
        e.close();print('PASS: C3 persistent environment, 10/2 contract, 1100 frames and Gymnasium checks.',flush=True);return
    args.out.mkdir(parents=True,exist_ok=True)
    env=make_vec_env(PersistentEnv,n_envs=args.envs,seed=args.seed,vec_env_cls=SubprocVecEnv if args.envs>1 else None,
                     vec_env_kwargs={'start_method':'spawn'} if args.envs>1 else None,monitor_dir=str(args.out/'episodes'),monitor_kwargs={'info_keywords':('is_success','strict_success','episode_recovered','control_fault')})
    env=VecNormalize(env,norm_obs=False,norm_reward=True,clip_reward=10.,gamma=.995)
    model=PPO('MlpPolicy',env,n_steps=512,batch_size=128,device='cpu',seed=args.seed,gamma=.995,gae_lambda=.95,
              policy_kwargs={'net_arch':{'pi':[64,64],'vf':[64,64]},'activation_fn':torch.nn.Tanh},
              learning_rate=1e-4,clip_range=.15,ent_coef=.005,verbose=0)
    source=PPO.load(args.warm_start,device='cpu')
    model.policy.mlp_extractor.policy_net.load_state_dict(source.policy.mlp_extractor.policy_net.state_dict())
    model.policy.action_net.load_state_dict(source.policy.action_net.state_dict())
    with torch.no_grad():model.policy.log_std.fill_(-1.3)
    report={'date':'2026-11-07','status':'C3 offline training, no hardware deployment',
            'config':{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
            'robot_xml_sha256':hashlib.sha256((HERE/'robot.xml').read_bytes()).hexdigest(),
            'warm_start_sha256':hashlib.sha256(args.warm_start.read_bytes()).hexdigest(),
            'training_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'sensor_pipeline':'unchanged firmware filter; observations not normalized',
            'reward':'stable base primary, soft neutral, one recovery bonus; 20 s continuing episodes, mild impulses and varied joint/target starts',
            'selection':'20 nominal/development cases, lexicographic base then strict success; fresh tests reserved until selection',
            'stages':[],'physical_robot_commands_sent':False}
    start=time.monotonic();best=(-1,-1);last=0
    for requested in [0]+list(range(32768,args.steps+1,32768)):
        if requested:model.learn(total_timesteps=requested-last,reset_num_timesteps=False);last=requested
        score=standard_score(model);key=(score['base_successes'],score['strict_successes'])
        stage={'requested_steps':requested,'actual_steps':model.num_timesteps,'evaluation':score}
        report['stages'].append(stage)
        if key>best:
            best=key;model.save(args.out/'best');report['selected_actual_steps']=model.num_timesteps
        model.save(args.out/f'checkpoint_{model.num_timesteps:06d}');model.save(args.out/'latest')
        env.save(str(args.out/f'return_normalization_{model.num_timesteps:06d}.pkl'))
        episodes=[]
        for f in (args.out/'episodes').glob('*.monitor.csv'):
            with f.open() as stream:
                next(stream);episodes.extend(csv.DictReader(stream))
        report['completed_training_episodes']=len(episodes)
        report['episodes_recovered_at_least_once']=sum(e['episode_recovered']=='True' for e in episodes)
        report['episodes_ending_with_control_fault']=sum(e['control_fault']=='True' for e in episodes)
        report['wall_seconds']=time.monotonic()-start
        (args.out/'training_report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'steps':model.num_timesteps,'base':key[0],'strict':key[1],'episodes':score['episodes'],'wall_seconds':report['wall_seconds']}),flush=True)
    env.close()
if __name__=='__main__':main()
