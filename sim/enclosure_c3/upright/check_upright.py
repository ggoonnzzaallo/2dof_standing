"""Verify level-base straightening, persistence after success and return to recovery."""
from pathlib import Path
import json
from robust_env import RobustEnv,HERE
import mujoco,numpy as np
from stable_baselines3 import PPO
import torch
torch.set_num_threads(1)
actor=PPO.load(HERE/'results/best.zip',device='cpu');rows=[]
for seed in (301,302,303,304,305):
 e=RobustEnv(randomize=True)
 try:
  obs,_=e.reset(seed=seed,options={'tilt':0.,'azimuth':0.})
  # Deliberately start with a bent commanded arm on a flat base. This tests the
  # deployed supervisor regardless of what the network would choose at rest.
  e.command=np.array([.8,-.6]);e.servo_target=e.command.copy();e.queue=[e.command.copy() for _ in range(e.delay)]
  e.data.qpos[-2:]=e.command;mujoco.mj_forward(e.model,e.data);obs=e._obs()
  reached=None;tail=[]
  for frame in range(500):
   obs,_,_,_,info=e.step(actor.predict(obs,deterministic=True)[0])
   assert not info['control_fault'] and not any(w.number for w in e.data.warning)
   if info['is_success'] and reached is None:reached=(frame+1)*.02
   if frame>=250:tail.append({'up':float(info['upright']),'max_q_deg':float(np.rad2deg(np.max(np.abs(e.data.qpos[-2:])))),'max_target':float(np.max(np.abs(e.command)))})
  assert reached is not None,(seed,'failed straight recovery')
  assert max(r['max_target'] for r in tail)<1e-6
  assert max(r['max_q_deg'] for r in tail)<7
  assert min(r['up'] for r in tail)>np.cos(np.deg2rad(8))
  rows.append({'seed':seed,'straight_upright_s':reached,'max_joint_error_after_5s_deg':max(r['max_q_deg'] for r in tail),'target_after_settle_rad':e.command.tolist()})
 finally:e.close()
r={'status':'passed','test':'flat base, initially bent arm, 10 s continuous control with randomized mechanics','cases':rows,'physical_robot_commands_sent':False}
(HERE/'upright_validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True)
