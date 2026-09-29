from pathlib import Path
import argparse
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv
from environment import SelfRightingEnv

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--steps',type=int,default=2_000_000)
    p.add_argument('--envs',type=int,default=4); p.add_argument('--out',default='runs/ppo'); p.add_argument('--seed',type=int,default=1)
    a=p.parse_args(); torch.set_num_threads(1)
    env=make_vec_env(SelfRightingEnv,n_envs=a.envs,seed=a.seed,vec_env_cls=SubprocVecEnv if a.envs>1 else None)
    model=PPO('MlpPolicy',env,policy_kwargs={'net_arch':{'pi':[64,64],'vf':[64,64]},'activation_fn':torch.nn.Tanh},
              n_steps=512,batch_size=128,learning_rate=3e-4,gamma=.99,gae_lambda=.95,device='cpu',seed=a.seed,verbose=1)
    model.learn(total_timesteps=a.steps)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); model.save(a.out); env.close()
