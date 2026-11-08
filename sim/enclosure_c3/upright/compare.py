"""Matched harder-physics comparison; keep old rate/retries explicit."""
from pathlib import Path
import argparse,hashlib,json,time
import train
from robust_env import RobustEnv
from stable_baselines3 import PPO
import torch

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('actor',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--episodes',type=int,default=50);p.add_argument('--seed',type=int,default=71000);p.add_argument('--seconds',type=float,default=25)
    p.add_argument('--old-runtime',action='store_true');p.add_argument('--no-retries',action='store_true');a=p.parse_args();torch.set_num_threads(1)
    def make(retries=True):
        e=RobustEnv(retries=retries and not a.old_runtime and not a.no_retries)
        e.action_increment=.06 if a.old_runtime else .10
        return e
    train.RobustEnv=make;start=time.monotonic()
    r=train.evaluate(PPO.load(a.actor,device='cpu'),range(a.seed,a.seed+a.episodes),seconds=a.seconds)
    r.update(status='Matched robust simulation; not physical recovery',horizon_s=a.seconds,first_seed=a.seed,
             action_increment_rad=.06 if a.old_runtime else .10,retries_enabled=not a.old_runtime and not a.no_retries,
             actor_sha256=hashlib.sha256(a.actor.read_bytes()).hexdigest(),wall_seconds=time.monotonic()-start)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='trials'},indent=2),flush=True)
if __name__=='__main__':main()
