"""Validate revised geometry, inertia, sensors, selective contacts and free dynamics."""
from pathlib import Path
import hashlib
import json
import sys
import mujoco
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from model_geometry import neutral_collision_vertices,place_neutral_robot
from environment import SelfRightingEnv
from asset_hashes import snapshot

def main():
    path=HERE/'robot.xml';m=mujoco.MjModel.from_xml_path(str(path));d=mujoco.MjData(m)
    r=json.loads((HERE/'model_report.json').read_text());orig=json.loads((HERE.parent/'onshape/body_properties.json').read_text())
    assert snapshot(path)['mesh_assets_sha256']==r['mesh_assets_sha256'], 'Mesh assets changed since model build'
    assert hashlib.sha256((HERE.parent/'robot.xml').read_bytes()).hexdigest()==r['original_model_sha256']
    assert np.isclose(m.body_mass.sum(),r['whole_upright']['mass_kg'],atol=1e-12)
    mujoco.mj_forward(m,d)
    assert d.ncon==0, 'Neutral pose has false fitted-part contact'
    assert np.allclose(m.site('imu').pos,r['imu_site_cad_m'])
    for name,p in r['groups'].items():
        b=m.body(name);rotation=np.empty(9);mujoco.mju_quat2Mat(rotation,b.iquat);rotation=rotation.reshape(3,3)
        actual=rotation@np.diag(b.inertia)@rotation.T
        assert np.linalg.norm(actual-np.array(p['inertia_com_cad_kg_m2']))/np.linalg.norm(actual)<1e-6
        assert np.allclose(b.ipos+np.array(orig['body_frame_origins_cad_mm'][name])/1000,p['com_cad_m'],atol=1e-10)
    support=neutral_collision_vertices(m)
    assert abs(support[:,2].min()+.012)<2e-7
    # A substantial non-mating clash must create actual contact, not be hidden.
    grid=[]
    for a in np.linspace(-80,80,9):
        for b in np.linspace(-80,80,9):
            mujoco.mj_resetData(m,d);d.qpos[-2:]=np.deg2rad([a,b]);mujoco.mj_forward(m,d)
            contacts=[c for c in d.contact if m.geom_bodyid[c.geom1] and m.geom_bodyid[c.geom2] and c.dist<-.0002]
            if contacts:grid.append({'joint_degrees':[a,b],'deepest_mm':-min(c.dist for c in contacts)*1000})
    # Deliberately fold beyond the allowed range to prove masks do not suppress
    # external self-contact. This is a static diagnostic, never an action target.
    d.qpos[-2:]=np.deg2rad([180,0]);mujoco.mj_forward(m,d)
    forced=[c for c in d.contact if m.geom_bodyid[c.geom1] and m.geom_bodyid[c.geom2] and c.dist<-.0002]
    assert forced,'External self-contact incorrectly suppressed'
    cases=[('upright',0,0)]+[(f'side_{a}',90,a) for a in range(0,360,45)]+[('inverted',180,0)]
    trials=[]
    for name,tilt,az in cases:
        mujoco.mj_resetData(m,d);place_neutral_robot(m,d,*np.deg2rad([tilt,az]),support_points=support)
        penetration=0.;joint=0.
        for _ in range(2000):
            d.ctrl[:]=np.clip(-.5*d.qpos[-2:]-.012*d.qvel[-2:],-.07,.07)
            mujoco.mj_step(m,d)
            assert np.isfinite(d.qpos).all() and np.isfinite(d.qvel).all()
            penetration=min(penetration,min((c.dist for c in d.contact),default=0))
            joint=max(joint,float(np.max(np.abs(np.rad2deg(d.qpos[-2:])))))
        warnings=sum(int(w.number) for w in d.warning)
        assert not warnings and penetration>-.01 and joint<86,(name,penetration,joint,warnings)
        cosine=float(d.xmat[m.body('base').id].reshape(3,3)[2,2])
        if name=='upright':assert cosine>.999 and np.max(np.abs(d.qpos[-2:]))<.02
        trials.append({'case':name,'warnings':warnings,'deepest_penetration_mm':-penetration*1000,'max_joint_abs_deg':joint})
    env=SelfRightingEnv(randomize=True,model_path=path);obs,_=env.reset(seed=21)
    for step in range(1000):
        obs,reward,term,trunc,_=env.step(np.random.default_rng(step).uniform(-1,1,2))
        assert np.isfinite(obs).all() and np.isfinite(reward)
        assert not any(w.number for w in env.data.warning)
        if term or trunc:env.reset(seed=step+100)
    env.close()
    out={'status':'passed','date':r.get('date','2026-11-03'),'robot_xml_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'mass_g':m.body_mass.sum()*1000,'whole_com_cad_mm':(np.array(r['whole_upright']['com_cad_m'])*1000).tolist(),
        'imu_site_cad_mm':(m.site('imu').pos*1000).tolist(),'old_model_and_policy_preserved':True,
        'neutral_false_contacts':0,'inertia_checks':'passed','ground_bottom_cad_mm':-12,
        'compound_grid_poses':81,'poses_with_active_nonmating_contacts':grid,
        'out_of_range_fold_contact_count':len(forced),
        'placed_fall_trials':trials,'random_action_steps':1000,'physical_robot_commands_sent':False}
    (HERE/'validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('poses_with_active_nonmating_contacts','placed_fall_trials')},indent=2))
if __name__=='__main__':main()
