"""Software verification only: the 512-step smoke policy is NOT a learned controller."""
import ctypes, json, subprocess, tempfile
from pathlib import Path
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from environment import SelfRightingEnv
from export_actor import export

torch.set_num_threads(1)
env=SelfRightingEnv(); check_env(env)
env.reset(seed=4)
for i in range(1500):
    obs,r,done,trunc,info=env.step(env.action_space.sample())
    assert np.isfinite(obs).all() and np.isfinite(r)
    if done or trunc: env.reset()
model=PPO('MlpPolicy',env,n_steps=512,batch_size=128,device='cpu',seed=2,
          policy_kwargs={'net_arch':{'pi':[64,64],'vf':[64,64]},'activation_fn':torch.nn.Tanh})
model.learn(512)
with tempfile.TemporaryDirectory() as temp:
    p=Path(temp); model.save(p/'smoke')
    count=export(p/'smoke.zip',p/'policy.h')
    (p/'test.c').write_text('#include "policy.h"\nvoid infer(const float *x,float *y){robot_policy(x,y);}\n')
    subprocess.run(['cc','-shared','-fPIC','-O2',str(p/'test.c'),'-o',str(p/'policy.so'),'-lm'],check=True)
    lib=ctypes.CDLL(str(p/'policy.so')); ptr=ctypes.POINTER(ctypes.c_float)
    lib.infer.argtypes=[ptr,ptr]; lib.infer.restype=None
    err=0.
    for obs in np.random.default_rng(2).uniform(-1,1,(100,10)).astype(np.float32):
        out=np.zeros(2,dtype=np.float32); lib.infer(obs.ctypes.data_as(ptr),out.ctypes.data_as(ptr))
        expected=model.predict(obs,deterministic=True)[0]
        err=max(err,float(np.max(np.abs(out-expected))))
    assert err<1e-5
result={'gymnasium_check':'passed','random_steps_finite':1500,'ppo_smoke_steps':512,
        'actor_parameters':count,'actor_flash_bytes':4*count,'c_parity_max_abs_error':err,
        'trained_policy_delivered':False,'physical_robot_tested':False}
Path(__file__).with_name('validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
