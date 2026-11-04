"""Behavior-clone simulated demonstrations, optionally refine PPO, then evaluate.

This trains an exploratory 10-input actor for simulation. It never opens serial
ports or uploads firmware. Real sensor/servo calibration remains necessary.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import time
os.environ.setdefault('MPLCONFIGDIR','/tmp/2dof-mpl-cache')
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv, VecNormalize
import search
from evaluate_filter import FilteredEnv


def evaluate(model,mode,repeats=1,filtered=False):
    cases = list(search.CASES)
    rows = []
    for case_index,case in enumerate(cases):
        for repeat in range(repeats):
            seed = {'nominal':100,'development':3000,'held_out_test':5000}[mode]+case_index*100+repeat
            rng = np.random.default_rng(seed)
            options = dict(search.CASES[case])
            if mode!='nominal':
                options['tilt'] += np.deg2rad(rng.uniform(-10,10))
                options['azimuth'] += np.deg2rad(rng.uniform(-10,10))
            env = (FilteredEnv if filtered else search.SelfRightingEnv)(randomize=mode!='nominal')
            obs,_ = env.reset(seed=seed,options=options)
            for step in range(500):
                action = np.zeros(2,dtype=np.float32) if model is None else model.predict(obs,deterministic=True)[0]
                obs,_,terminated,truncated,info = env.step(action)
                if terminated or truncated:
                    break
            rows.append({'case':case,'seed':seed,'requested_start':options,'success':bool(info['is_success']),
                         'seconds':(step+1)*.02,'final_upright':info['upright']})
            env.close()
    return {'mode':mode,'successes':sum(r['success'] for r in rows),'episodes':len(rows),'trials':rows}


def clone_actor(model,data,updates,seed):
    rng = np.random.default_rng(seed)
    episodes = np.unique(data['episode_id'])
    rng.shuffle(episodes)
    validation_ids = episodes[:max(1,len(episodes)//5)]
    validation = np.isin(data['episode_id'],validation_ids)
    train_index = np.flatnonzero(~validation)
    obs = torch.tensor(data['observation'])
    actions = torch.tensor(data['action'])
    parameters = list(model.policy.mlp_extractor.policy_net.parameters())+list(model.policy.action_net.parameters())
    optimizer = torch.optim.Adam(parameters,lr=1e-3)
    best = None;best_loss = float('inf');history = []
    for update in range(updates):
        indices = rng.choice(train_index,256,replace=True)
        prediction = model.policy.get_distribution(obs[indices]).distribution.mean
        # Keep stationary holds from dominating all movement examples.
        weight = 1+4*actions[indices].abs().max(dim=1).values
        loss = ((prediction-actions[indices]).square().mean(dim=1)*weight).mean()
        optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(parameters,1.);optimizer.step()
        if (update+1)%100 == 0 or update==updates-1:
            with torch.no_grad():
                valid_loss = float((model.policy.get_distribution(obs[validation]).distribution.mean-actions[validation]).square().mean())
            if valid_loss<best_loss:
                best_loss=valid_loss;best=copy.deepcopy(model.policy.state_dict())
            history.append({'update':update+1,'train_weighted_mse':float(loss.detach()),'validation_mse':valid_loss})
    model.policy.load_state_dict(best)
    with torch.no_grad():
        model.policy.log_std.fill_(-1.)
    return {'updates':updates,'validation_episode_ids':validation_ids.tolist(),
            'split':'Entire trajectories held out; closed-loop evaluation reported separately',
            'history':history,'best_validation_mse':best_loss}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset',type=Path)
    parser.add_argument('--bc-updates',type=int,default=3000)
    parser.add_argument('--ppo-steps',type=int,default=65536)
    parser.add_argument('--envs',type=int,default=3)
    parser.add_argument('--seed',type=int,default=17)
    parser.add_argument('--out',type=Path,default=Path('runs/recovery_policy'))
    parser.add_argument('--filtered',action='store_true',help='Train and evaluate using the firmware gravity filter and simulated IMU')
    parser.add_argument('--warm-start',type=Path,help='Fine-tune a saved actor instead of behavior cloning; preserve a separate output directory')
    parser.add_argument('--actor-only',action='store_true',help='Transfer actor weights while keeping a fresh value network')
    parser.add_argument('--normalize-rewards',action='store_true',help='Normalize training returns; observations remain unchanged')
    parser.add_argument('--initial-log-std',type=float,help='Override initial PPO action exploration log standard deviation')
    args = parser.parse_args()
    torch.set_num_threads(1);torch.manual_seed(args.seed)
    metadata = json.loads(args.dataset.with_suffix('.json').read_text())
    xml_hash = hashlib.sha256(search.MODEL_PATH.read_bytes()).hexdigest()
    assert metadata['robot_xml_sha256']==xml_hash
    assert metadata['dataset_sha256']==hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    assert metadata.get('filtered_observations',False)==args.filtered, 'Dataset and training sensor pipeline must match'
    if args.filtered:
        assert metadata['filtered_environment_sha256']==hashlib.sha256((search.HERE/'evaluate_filter.py').read_bytes()).hexdigest()
    args.out.mkdir(parents=True,exist_ok=True)
    env = make_vec_env(FilteredEnv if args.filtered else search.SelfRightingEnv,n_envs=args.envs,seed=args.seed,
                       vec_env_cls=SubprocVecEnv if args.envs>1 else None,
                       vec_env_kwargs={'start_method':'spawn'} if args.envs>1 else None)
    if args.normalize_rewards:env=VecNormalize(env,norm_obs=False,norm_reward=True,clip_reward=10.)
    model = PPO('MlpPolicy',env,n_steps=512,batch_size=128,device='cpu',seed=args.seed,
                policy_kwargs={'net_arch':{'pi':[64,64],'vf':[64,64]},'activation_fn':torch.nn.Tanh},
                learning_rate=1e-4,ent_coef=.005,verbose=0)
    start = time.monotonic()
    report = {'status':'Exploratory simulation policy; not validated on hardware',
              'robot_xml_sha256':xml_hash,'dataset_sha256':metadata['dataset_sha256'],
              'reward_success_bonus':float(os.environ.get('ROBOT_SUCCESS_BONUS','20')),
              'config':{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
              'zero_action_baseline':evaluate(None,'nominal',filtered=args.filtered), 'stages':[], 'physical_robot_commands_sent':False}
    if args.warm_start:
        source=PPO.load(args.warm_start,device='cpu')
        if args.actor_only:
            model.policy.mlp_extractor.policy_net.load_state_dict(source.policy.mlp_extractor.policy_net.state_dict())
            model.policy.action_net.load_state_dict(source.policy.action_net.state_dict())
            with torch.no_grad():model.policy.log_std.copy_(source.policy.log_std)
        else:model.policy.load_state_dict(source.policy.state_dict())
        report['behavior_cloning']={'updates':0,'method':'Warm-start saved policy; no new cloning updates',
            'warm_start_sha256':hashlib.sha256(args.warm_start.read_bytes()).hexdigest()}
    else:
        report['behavior_cloning'] = clone_actor(model,np.load(args.dataset),args.bc_updates,args.seed)
    if args.initial_log_std is not None:
        with torch.no_grad():model.policy.log_std.fill_(args.initial_log_std)
    model.save(args.out/'bc')
    best_score = -1
    stages = [0]+list(range(16384,args.ppo_steps+1,16384))
    if stages[-1]!=args.ppo_steps:
        stages.append(args.ppo_steps)
    last = 0
    for requested in stages:
        if requested:
            model.learn(total_timesteps=requested-last,reset_num_timesteps=False)
            last = requested
        nominal = evaluate(model,'nominal',filtered=args.filtered)
        development = evaluate(model,'development',filtered=args.filtered)
        row = {'ppo_steps_actual':model.num_timesteps,'nominal':nominal,'development':development}
        report['stages'].append(row)
        score = nominal['successes']/nominal['episodes']+development['successes']/development['episodes']
        if score>best_score:
            best_score=score;model.save(args.out/'best')
            report['selected_ppo_steps'] = model.num_timesteps
        model.save(args.out/'latest')
        model.save(args.out/f'checkpoint_{model.num_timesteps:06d}')
        if args.normalize_rewards:env.save(str(args.out/f'normalization_{model.num_timesteps:06d}.pkl'))
        report['wall_seconds'] = time.monotonic()-start
        (args.out/'training_report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'ppo_steps':model.num_timesteps,'nominal':nominal['successes'],'development':development['successes'],'episodes_each':nominal['episodes']}),flush=True)
    selected = PPO.load(args.out/'best',device='cpu')
    report['held_out_test'] = evaluate(selected,'held_out_test',repeats=3,filtered=args.filtered)
    report['selection_note'] = 'Checkpoint selected using nominal/development sets only; final held-out seeds were not used for selection.'
    report['wall_seconds'] = time.monotonic()-start
    (args.out/'training_report.json').write_text(json.dumps(report,indent=2)+'\n')
    env.close()
    print('Selected model:',args.out/'best.zip','held-out',report['held_out_test']['successes'],'/',report['held_out_test']['episodes'],flush=True)


if __name__=='__main__':
    main()
