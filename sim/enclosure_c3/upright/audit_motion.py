"""Check actual simulated travel and non-floor contact during selected recoveries."""
import json
import mujoco,numpy as np,torch
from robust_env import RobustEnv,HERE
from stable_baselines3 import PPO
torch.set_num_threads(1);actor=PPO.load(HERE/'results/best.zip',device='cpu');rows=[]
for az in range(0,360,45):
 e=RobustEnv(randomize=False);obs,_=e.reset(seed=100+az,options={'tilt':np.pi/2,'azimuth':np.deg2rad(az)})
 original=e.physics_observer;peak=np.zeros(2);depth=[0.]
 def observe(env):
  original(env);peak[:]=np.maximum(peak,np.abs(np.rad2deg(env.data.qpos[-2:])))
  for c in env.data.contact:
   if env.model.geom_bodyid[c.geom1] and env.model.geom_bodyid[c.geom2]:depth[0]=max(depth[0],float(-c.dist*1000))
 e.physics_observer=observe;first=None
 for frame in range(1250):
  obs,_,_,_,info=e.step(actor.predict(obs,deterministic=True)[0])
  if info['is_success']:first=(frame+1)*.02;break
  if info['control_fault']:break
 rows.append({'azimuth_deg':az,'upright_straight_s':first,'max_actual_joint_abs_deg':peak.tolist(),'max_nonfloor_penetration_mm':depth[0],'fault':info['control_fault']});e.close()
 print(rows[-1],flush=True)
r={'status':'dynamic geometry diagnostic, not a servo-travel measurement','trials':rows}
(HERE/'dynamic_contact_audit.json').write_text(json.dumps(r,indent=2)+'\n')
