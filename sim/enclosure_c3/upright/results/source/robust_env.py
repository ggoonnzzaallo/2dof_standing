"""C3 recovery with extra mass, broad surface/servo variation and portable retries."""
from pathlib import Path
import os,sys
HERE=Path(__file__).resolve().parent
os.environ['ROBOT_MODEL_PATH']=str(HERE/'robot.xml')
sys.path.insert(0,str(HERE.parents[1]/'recovery'))
import mujoco,numpy as np
from evaluate_filter import FilteredEnv
from strategy import Strategy

class RobustEnv(FilteredEnv):
    def __init__(self,randomize=True,retries=True):
        self.action_increment=.10;self.use_retries=retries;self.strategy=Strategy()
        super().__init__(randomize=randomize,model_path=HERE/'robot.xml')
        self.ipos0=self.model.body_ipos.copy()
        update=self.runtime.update
        def observed(accel,gyro,dt,*args,**kwargs):
            self.strategy.observe(self.mount@np.asarray(accel),self.mount@(np.asarray(gyro)-self.bias),dt)
            return update(accel,gyro,dt,*args,**kwargs)
        self.runtime.update=observed
    def before_settle(self):
        if self.randomize:
            factors=self.np_random.uniform(.93,1.15,len(self.mass0))
            self.model.body_mass[:]=self.mass0*factors
            self.model.body_inertia[:]=self.inertia0*factors[:,None]
            self.model.body_ipos[:]=self.ipos0
            for name in ('base','middle','upper'):
                i=self.model.body(name).id;self.model.body_ipos[i]+=self.np_random.uniform(-.002,.002,3)
            self.friction=float(self.np_random.uniform(.15,1.35))
            self.torque=float(self.np_random.uniform(.032,.07))
            self.speed=float(self.np_random.uniform(2.6,5.5))
            self.kp=float(self.np_random.uniform(.3,.7))
            self.delay=int(self.np_random.integers(0,4));self.queue=[self.command.copy() for _ in range(self.delay)]
            if self.np_random.random()<.40:
                self.data.qpos[-2:]=self.np_random.uniform(-1.15,1.15,2)
        else:
            self.friction=.7;self.torque=.052;self.speed=4.;self.kp=.5
            self.model.body_ipos[:]=self.ipos0
        self.model.geom_friction[:,0]=self.friction
        # mj_setConst overwrites qpos/qvel with the model reference pose.
        # Preserve the requested fallen pose and bent joints across mass updates.
        qpos=self.data.qpos.copy();qvel=self.data.qvel.copy()
        mujoco.mj_setConst(self.model,self.data)
        self.data.qpos[:]=qpos;self.data.qvel[:]=qvel
        mujoco.mj_forward(self.model,self.data)
        # Bent joints change the support envelope. Lift the whole robot only
        # enough to remove ground penetration before releasing it into physics.
        from model_geometry import geom_vertices_world
        low=min(float(geom_vertices_world(self.model,self.data,i)[:,2].min())
                for i in range(self.model.ngeom) if self.model.geom_bodyid[i]!=0 and self.model.geom_contype[i]!=0)
        if low<.001:self.data.qpos[2]+=.001-low;mujoco.mj_forward(self.model,self.data)
        self.pre_release_qpos=self.data.qpos.copy()
        self.pre_release_up=float(self.data.xmat[self.base_id].reshape(3,3)[2,2])
        super().before_settle()
    def reset(self,seed=None,options=None):
        self.strategy.reset(seed)
        obs,info=super().reset(seed=seed,options=options)
        self.gyro_smooth=np.zeros(3);self.base_dwell=0;self.episode_retries=0;self.recovery_rewarded=False
        self.max_target=0.;self.action_overridden=False
        return obs,info
    def step(self,action):
        before=float(self.data.xmat[self.base_id].reshape(3,3)[2,2]);old=self.previous.copy()
        self.raw_action=np.clip(np.asarray(action,dtype=np.float32),-1,1)
        applied,self.action_overridden=self.strategy.apply(self.runtime.down,self.command,self.raw_action,self.runtime.gyro) if self.use_retries else (self.raw_action,False)
        obs,_,terminated,_,info=super().step(applied)
        upright=float(info['upright']);gyro=self.data.sensor('gyro').data
        contact=any((c.geom1==self.floor_id and self.model.geom_bodyid[c.geom2]==self.base_id) or
                    (c.geom2==self.floor_id and self.model.geom_bodyid[c.geom1]==self.base_id) for c in self.data.contact)
        self.gyro_smooth=.8*self.gyro_smooth+.2*gyro
        # A sub-millimetre solver contact gap is still a resting base; angular
        # rate is averaged over ~100 ms to reject stiff-contact chatter.
        resting=contact or self.data.qpos[2]<.0125
        base_good=upright>np.cos(np.deg2rad(8)) and np.linalg.norm(self.gyro_smooth)<.4 and resting
        straight=np.max(np.abs(self.data.qpos[-2:]))<.12 and np.max(np.abs(self.command))<.05
        good=base_good and straight
        self.base_dwell=self.base_dwell+1 if good else 0;success=self.base_dwell>=50
        self.recovery_rewarded|=success
        # Urgency and terminal recovery dominate; almost no cost for useful effort.
        reward=-1.+.35*upright+1.*base_good+1.*good+8*(.995*upright-before)
        reward+=1.*np.exp(-3*float(self.data.qpos[-2:]@self.data.qpos[-2:]))*max(upright,0)
        reward-=.002*float(applied@applied)+.001*float((applied-old)@(applied-old))+.0001*float(gyro@gyro)
        if success:reward+=150
        invalid=info.get('filter_fault',False) or (terminated and not info['is_success'])
        if invalid:reward-=100
        self.max_target=max(self.max_target,float(np.max(np.abs(self.command))));self.episode_retries=self.strategy.retries
        return obs,float(reward),bool(success or invalid),self.steps>=1500,{**info,'is_success':bool(success),'strict_success':bool(success),'base_good':bool(base_good),'straight':bool(straight),
          'episode_recovered':bool(self.recovery_rewarded),'control_fault':bool(invalid),'retry_count':self.episode_retries,'max_target_deg':float(np.rad2deg(self.max_target))}
    def close(self):self.strategy.close();super().close()
