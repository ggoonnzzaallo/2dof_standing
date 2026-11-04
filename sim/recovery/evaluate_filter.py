"""Test recovery using the real firmware filter and simulated IMU specific force.

No hardware/serial. These results replace no earlier truth-observation metrics.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
os.environ.setdefault('MPLCONFIGDIR','/tmp/2dof-mpl-cache')
import numpy as np
import torch
from stable_baselines3 import PPO
import search
from filter_runtime import FilterRuntime

ROOT=search.HERE.parents[1]
CALIBRATION=ROOT/'firmware/imu_bench/measurements/2026-11-01/mount_rotation_provisional.json'

class FilteredEnv(search.SelfRightingEnv):
    def __init__(self,runtime=None,truth_down=False,randomize=True,model_path=None):
        self.owns_runtime=runtime is None
        self.runtime=FilterRuntime() if runtime is None else runtime
        self.truth_down=truth_down
        calibration=json.loads(CALIBRATION.read_text())
        self.mount=np.asarray(calibration['R_sensor_to_base'])
        self.bias=np.asarray(calibration['gyro_bias_candidate_sensor_rad_s'])
        super().__init__(randomize=randomize,model_path=model_path,physics_observer=self.feed)
    def close(self):
        if self.owns_runtime:self.runtime.close()
        super().close()
    def reset(self,seed=None,options=None):
        self.runtime.reset();self.next_sample=0.;self.sample_time=None
        self.control_active=False;self.stop_requested=False
        self.sensor_rng=np.random.default_rng(seed)
        self.gyro_drift=self.sensor_rng.normal(0,.003,3)
        self.accel_bias=self.sensor_rng.normal(0,.01,3)
        super().reset(seed=seed,options=options)
        self.control_active=True
        self.stop_requested=not self.runtime.ready
        return self._obs(),{}
    def before_settle(self):
        # Model the operator holding the robot still before releasing it. Feed
        # 30 noisy static IMU samples through the real initializer; do not assign
        # exact DOWN to the filter or the actor. The following 0.8 s is free dynamics.
        R=self.data.xmat[self.base_id].reshape(3,3)
        static_a=self.mount.T@(R.T@np.array([0.,0.,9.81/9.80665]))
        for i in range(30):
            a=static_a+self.accel_bias+self.sensor_rng.normal(0,.0015,3)
            w=self.bias+self.gyro_drift+self.sensor_rng.normal(0,.0015,3)
            self.runtime.update(a,w,0. if i==0 else 1/208)
        assert self.runtime.ready, 'Held-still sensor initialization failed'
        self.filter_init_wait_s=30/208
        self.sample_time=self.data.time;self.next_sample=self.data.time+1/208
    def feed(self,env):
        if self.data.time+1e-10<self.next_sample:return
        self.next_sample+=1/208
        a=self.mount.T@(self.data.sensor('accel').data.copy()/9.80665)
        w=self.mount.T@self.data.sensor('gyro').data.copy()+self.bias
        a+=self.accel_bias+self.sensor_rng.normal(0,.0015,3)
        w+=self.gyro_drift+self.sensor_rng.normal(0,.0015,3)
        dt=0. if self.sample_time is None else self.data.time-self.sample_time
        self.sample_time=self.data.time
        accel_clip=bool(np.max(np.abs(a))>=7.9788)
        gyro_clip=bool(np.max(np.abs(w))>=39.95)
        a=np.clip(a,-7.995,7.995);w=np.clip(w,-40.03,40.03)
        self.runtime.update(a,w,dt,gyro_clip,accel_clip)
        if self.control_active and not self.runtime.ready:self.stop_requested=True
    def step(self,action):
        if self.stop_requested:
            return self._obs(),-20.,True,False,{'is_success':False,'filter_fault':True,'upright':float(self.data.xmat[self.base_id].reshape(3,3)[2,2])}
        obs,reward,terminated,truncated,info=super().step(action)
        if self.stop_requested:
            info={**info,'is_success':False,'filter_fault':True}
            return obs,reward-20,True,truncated,info
        return obs,reward,terminated,truncated,info
    def _obs(self):
        down=self.runtime.down
        if self.truth_down:
            down=self.data.xmat[self.base_id].reshape(3,3).T@np.array([0.,0.,-1.])
        return np.clip(np.r_[down,self.runtime.gyro/10,self.command/self.limit,self.previous],-1,1).astype(np.float32)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episodes',type=int,default=30)
    parser.add_argument('--out',type=Path,default=Path('build/shadow/filter_simulation.json'))
    parser.add_argument('--seed',type=int,default=19000)
    parser.add_argument('--truth-down',action='store_true',help='Diagnostic only: replace filtered DOWN with exact orientation; preserve sensor gyro and identical seeds.')
    parser.add_argument('--actor',type=Path,default=search.HERE/'results/policy_simulation_only.zip')
    args=parser.parse_args();torch.set_num_threads(1)
    model_path=args.actor
    actor=PPO.load(model_path,device='cpu')
    runtime=FilterRuntime();env=FilteredEnv(runtime,args.truth_down);trials=[]
    for episode in range(args.episodes):
        seed=args.seed+episode;rng=np.random.default_rng(seed)
        options={'tilt':float(rng.uniform(0,np.pi)),'azimuth':float(rng.uniform(0,2*np.pi))}
        obs,_=env.reset(seed=seed,options=options);angles=[];unready=False;success=False;steps=0
        for step in range(500):
            if not runtime.ready:unready=True;break
            truth=env.data.xmat[env.base_id].reshape(3,3).T@np.array([0,0,-1.])
            angles.append(float(np.rad2deg(np.arccos(np.clip(runtime.down@truth,-1,1)))))
            obs,_,terminated,truncated,info=env.step(actor.predict(obs,deterministic=True)[0]);steps=step+1
            success=bool(info['is_success'])
            if terminated or truncated:break
        warnings=sum(int(w.number) for w in env.data.warning)
        trials.append({'seed':seed,'requested_pose':options,'success':bool(success and not warnings and not unready),
                       'filter_initialization_extra_settle_s':env.filter_init_wait_s,
                       'filter_fault':env.stop_requested,
                       'filter_unready_during_control':unready,'mujoco_warnings':warnings,'seconds':steps*.02,
                       'gravity_error_mean_deg':float(np.mean(angles)) if angles else None,
                       'gravity_error_max_deg':max(angles) if angles else None})
    report={'status':'Exploratory simulation with firmware filter, not physical recovery validation',
            'actor_down_input':'exact orientation (diagnostic ablation)' if args.truth_down else 'firmware gravity filter',
            'episodes':len(trials),'first_seed':args.seed,'successes':sum(t['success'] for t in trials),
            'filter_unready_trials':sum(t['filter_unready_during_control'] for t in trials),
            'robot_xml_sha256':hashlib.sha256(search.MODEL_PATH.read_bytes()).hexdigest(),
            'actor_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),
            'filter_header_sha256':hashlib.sha256((ROOT/'firmware/policy_shadow/GravityFilter.h').read_bytes()).hexdigest(),
            'sensor_model':'30 held-still noisy IMU samples before release, then MuJoCo accelerometer specific force at base IMU site, 208 Hz sampling; measured mounting/bias; exploratory accel bias sigma .01 g, gyro bias sigma .003 rad/s; white noise .0015 g and .0015 rad/s. Filter invalidation terminates control.',
            'limitations':['Mounting is treated as known exactly here; dynamic accelerometer/gyro calibration remains unverified.',
                           'No FIFO, sensor analog filtering, transport latency or clipping recovery calibration.',
                           'Diagnostic ablation uses truth DOWN as actor input.' if args.truth_down else 'Truth orientation is used for scoring error only, not actor input.'],
            'physical_motor_commands_sent':False,'trials':trials}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='trials'},indent=2),flush=True)
    env.close();runtime.close()

if __name__=='__main__':main()
