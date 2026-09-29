"""Preliminary physics: replace approximate collisions and measured servo model before transfer."""
from pathlib import Path
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import mujoco

class SelfRightingEnv(gym.Env):
    metadata = {'render_modes': []}
    def __init__(self, randomize=True):
        self.model=mujoco.MjModel.from_xml_path(str(Path(__file__).with_name('robot.xml')))
        self.data=mujoco.MjData(self.model)
        self.randomize=randomize
        self.mass0=self.model.body_mass.copy(); self.inertia0=self.model.body_inertia.copy()
        self.base_id=mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_BODY,'base')
        self.floor_id=mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_GEOM,'floor')
        self.action_space=spaces.Box(-1.,1.,(2,),dtype=np.float32)
        self.observation_space=spaces.Box(-1.,1.,(10,),dtype=np.float32)
        self.limit=1.3963; self.steps=0; self.dwell=0

    def _obs(self):
        R=self.data.xmat[self.base_id].reshape(3,3)
        # Body-frame DOWN, then body-frame angular rate divided by 10 rad/s.
        g=R.T @ np.array([0.,0.,-1.])
        gyro=self.data.sensor('gyro').data.copy()
        if self.randomize:
            g=g+self.np_random.normal(0,.015,3); g=g/np.linalg.norm(g)
            gyro+=self.np_random.normal(0,.03,3)
        return np.clip(np.r_[g,gyro/10,self.command/self.limit,self.previous],-1,1).astype(np.float32)

    def _physics(self, target):
        for _ in range(10):
            self.servo_target+=np.clip(target-self.servo_target,-self.speed*.002,self.speed*.002)
            q=self.data.qpos[-2:]; v=self.data.qvel[-2:]
            requested=self.kp*(self.servo_target-q)-.012*v
            # Approximate motoring torque-speed envelope; braking is also bounded.
            ceiling=self.torque*np.clip(1-np.sign(requested)*v/self.speed,0,1)
            self.data.ctrl[:]=np.clip(requested,-ceiling,ceiling)
            mujoco.mj_step(self.model,self.data)

    def reset(self,seed=None,options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model,self.data)
        factor=self.np_random.uniform(.9,1.1,len(self.mass0)) if self.randomize else np.ones_like(self.mass0)
        self.model.body_mass[:]=self.mass0*factor
        self.model.body_inertia[:]=self.inertia0*factor[:,None]
        self.model.geom_friction[:,0]=self.np_random.uniform(.35,1.) if self.randomize else .7
        mujoco.mj_setConst(self.model,self.data)
        self.torque=self.np_random.uniform(.045,.07) if self.randomize else .07
        self.speed=self.np_random.uniform(3.,5.) if self.randomize else 5.
        self.kp=self.np_random.uniform(.35,.65) if self.randomize else .5
        self.delay=int(self.np_random.integers(0,3)) if self.randomize else 0
        self.command=np.zeros(2); self.servo_target=np.zeros(2); self.previous=np.zeros(2)
        self.queue=[np.zeros(2) for _ in range(self.delay)]
        self.steps=0; self.dwell=0
        options=options or {}
        # Axis in the horizontal plane covers cardinal/diagonal falls and inverted starts.
        az=float(options.get('azimuth',self.np_random.uniform(0,2*np.pi)))
        angle=float(options.get('tilt',self.np_random.choice([0.,.6,np.pi/2,2.2,np.pi])))
        self.data.qpos[:3]=[0,0,.18]
        self.data.qpos[3:7]=[np.cos(angle/2),np.sin(angle/2)*np.cos(az),np.sin(angle/2)*np.sin(az),0]
        mujoco.mj_forward(self.model,self.data)
        for _ in range(40): self._physics(np.zeros(2))
        return self._obs(),{}

    def step(self,action):
        action=np.clip(np.asarray(action,dtype=float),-1,1)
        old=self.previous.copy()
        self.command=np.clip(self.command+.06*action,-self.limit,self.limit)
        self.queue.append(self.command.copy()); delayed=self.queue.pop(0)
        self._physics(delayed)
        self.previous=action.copy(); self.steps+=1
        R=self.data.xmat[self.base_id].reshape(3,3); upright=float(R[2,2])
        q=self.data.qpos[-2:]; gyro=self.data.sensor('gyro').data
        base_contact=any((c.geom1==self.floor_id and self.model.geom_bodyid[c.geom2]==self.base_id) or
                         (c.geom2==self.floor_id and self.model.geom_bodyid[c.geom1]==self.base_id)
                         for c in self.data.contact)
        good=(upright>np.cos(np.deg2rad(10)) and np.max(np.abs(q))<.18 and np.linalg.norm(gyro)<.4 and base_contact)
        self.dwell=self.dwell+1 if good else 0
        success=self.dwell>=50
        reward=1.5*upright + .5*np.exp(-4*np.sum(q*q))*max(upright,0) + .5*good
        reward-=.02*float(action@action)+.04*float((action-old)@(action-old))+.002*float(gyro@gyro)
        if success: reward+=20
        invalid=not np.all(np.isfinite(self.data.qpos)) or np.linalg.norm(self.data.qpos[:2])>1.
        if invalid: reward-=20
        return self._obs(),float(reward),bool(success or invalid),self.steps>=500,{'is_success':success,'upright':upright}
