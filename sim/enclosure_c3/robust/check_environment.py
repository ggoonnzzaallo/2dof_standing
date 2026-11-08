"""Regression for mass changes preserving genuine fallen starting poses."""
import numpy as np
from robust_env import RobustEnv
for randomize in (False,True):
    env=RobustEnv(randomize=randomize)
    try:
        for i,(tilt,azimuth) in enumerate([(0,0),(np.pi/2,0),(np.pi/2,np.pi/2),(np.pi,0),(2.3,1.1)]):
            obs,_=env.reset(seed=91+i,options={'tilt':tilt,'azimuth':azimuth})
            assert abs(env.pre_release_up-np.cos(tilt))<1e-8,'Mass setup lost fallen orientation'
            expected=np.array([np.cos(tilt/2),np.sin(tilt/2)*np.cos(azimuth),np.sin(tilt/2)*np.sin(azimuth),0])
            assert np.allclose(env.pre_release_qpos[3:7],expected),'Reset quaternion overwritten'
            assert np.isfinite(obs).all() and len(obs)==10 and env.action_increment==.1
            for frame in range(50):
                obs,r,t,tr,info=env.step(np.array([.5,-.5],dtype=np.float32))
                assert np.isfinite(obs).all() and np.isfinite(r)
                assert np.max(np.abs(env.command))<=env.limit+1e-7
                if t or tr:break
    finally:env.close()
print('PASS: mass/COM randomization retains true fallen poses; finite 10/2 contract, target bounds and faster rate.')
