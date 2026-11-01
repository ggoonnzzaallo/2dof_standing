"""Offline checks of CAD placement, combined inertia, contacts and finite dynamics.

No RL training and no physical robot commands. Output is a verification record,
not evidence that a simulated or real recovery policy succeeds.
"""
from pathlib import Path
import json
import hashlib
import time
import sys
import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent / 'robot.xml'
sys.path.insert(0, str(HERE.parent))
from model_geometry import neutral_collision_vertices, place_neutral_robot


def main():
    properties = json.loads((HERE/'body_properties.json').read_text())
    manifest = json.loads((HERE/'manifest.json').read_text())
    model = mujoco.MjModel.from_xml_path(str(MODEL))
    data = mujoco.MjData(model)
    assert (model.nq, model.nv, model.nu) == (9, 8, 2)
    assert model.nbody == 4
    assert np.isclose(model.body_mass.sum(), properties['whole_upright']['mass_kg'], atol=1e-12)
    mujoco.mj_forward(model, data)
    root_offset = data.qpos[:3].copy()
    max_geometry_error = 0.
    for alias, item in manifest['parts'].items():
        geom_id = model.geom(alias+'_visual').id
        mesh_id = model.geom_dataid[geom_id]
        adr, count = model.mesh_vertadr[mesh_id], model.mesh_vertnum[mesh_id]
        vertices = model.mesh_vert[adr:adr+count] @ data.geom_xmat[geom_id].reshape(3,3).T + data.geom_xpos[geom_id]
        expected = np.array(item['bbox_cad_m']) + root_offset
        actual = np.array([vertices.min(axis=0), vertices.max(axis=0)])
        max_geometry_error = max(max_geometry_error, float(np.max(np.abs(actual-expected))))
    assert max_geometry_error < 1e-7, max_geometry_error
    for name, values in properties['groups'].items():
        body = model.body(name)
        rotation = np.empty(9)
        mujoco.mju_quat2Mat(rotation, body.iquat)
        rotation = rotation.reshape(3,3)
        reconstructed = rotation @ np.diag(body.inertia) @ rotation.T
        expected = np.array(values['inertia_com_cad_kg_m2'])
        # MuJoCo's eigensolver can discard ~1e-13 off-diagonals for gram-scale bodies.
        assert np.linalg.norm(reconstructed-expected)/np.linalg.norm(expected) < 1e-6
        origin = np.array(properties['body_frame_origins_cad_mm'][name])/1000
        assert np.allclose(body.ipos+origin, values['com_cad_m'], atol=1e-10)
    # Nonzero two-joint pose verifies serial transforms and upper axis rotation.
    q1, q2 = np.deg2rad([30, -25])
    data.qpos[-2:] = [q1, q2]
    mujoco.mj_forward(model, data)
    rotation = np.array([[1,0,0],[0,np.cos(q1),-np.sin(q1)],[0,np.sin(q1),np.cos(q1)]])
    lower = np.array(properties['body_frame_origins_cad_mm']['middle'])/1000
    upper = np.array(properties['body_frame_origins_cad_mm']['upper'])/1000
    assert np.allclose(data.xanchor[model.joint('j1').id], root_offset+lower, atol=1e-10)
    assert np.allclose(data.xanchor[model.joint('j2').id], root_offset+lower+rotation@(upper-lower), atol=1e-10)
    assert np.allclose(data.xaxis[model.joint('j2').id], rotation@np.array([0,1,0]), atol=1e-10)
    # Compare collision hull volume sums to source mesh; not a union/coverage proof.
    hull_ratios = {alias: p['sum_collision_hull_volume_m3']/p['cad_mesh_volume_m3']
                   for alias,p in manifest['parts'].items() if p['collision_meshes']}
    assert all(.95 < r < 1.10 for r in hull_ratios.values()), hull_ratios
    trials = []
    support_points = neutral_collision_vertices(model)
    start = time.monotonic()
    cases = [('upright',0.,0.)] + [(f'side_{a}',90.,float(a)) for a in range(0,360,45)] + [('inverted',180.,0.)]
    cases = [(name,t,a,mode) for mode in ('placed','drop_stress') for name,t,a in cases]
    steps_per_trial = round(2/model.opt.timestep)
    for name, tilt_deg, azimuth_deg, mode in cases:
        mujoco.mj_resetData(model, data)
        angle, az = np.deg2rad([tilt_deg, azimuth_deg])
        place_neutral_robot(model,data,angle,az,support_points=support_points)
        if mode == 'drop_stress':
            data.qpos[2] = .006 if tilt_deg==0 else .18
        deepest = 0.
        for _ in range(steps_per_trial):
            # Center-hold PD only: a recovery controller is not being evaluated.
            data.ctrl[:] = np.clip(-.5*data.qpos[-2:]-.012*data.qvel[-2:],-.07,.07)
            mujoco.mj_step(model, data)
            deepest = min(deepest, min((c.dist for c in data.contact), default=0.))
            assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
            assert np.linalg.norm(data.qpos[:3]) < 1.
        assert deepest > -.01, (name,deepest)
        assert np.max(np.abs(data.qpos[-2:])) < np.deg2rad(83)
        upright = float(data.xmat[model.body('base').id].reshape(3,3)[2,2])
        if name == 'upright':
            assert upright > .999 and data.ncon > 0
            assert np.max(np.abs(data.qpos[-2:])) < .02
        warnings = [int(w.number) for w in data.warning]
        assert not any(warnings), (name, warnings)
        trials.append({'case':name, 'reset_type':mode, 'simulated_seconds':2., 'deepest_contact_penetration_mm':-deepest*1000,
                       'final_base_upright_cosine':upright, 'final_joint_degrees':np.rad2deg(data.qpos[-2:]).tolist()})
    report = {'status':'passed', 'mujoco_version':mujoco.__version__, 'nq':model.nq,'nv':model.nv,
              'robot_xml_sha256':hashlib.sha256(MODEL.read_bytes()).hexdigest(),
              'moving_bodies':3, 'visual_parts':len(manifest['parts']), 'collision_meshes':sum(len(p['collision_meshes']) for p in manifest['parts'].values()),
              'total_model_mass_g':model.body_mass.sum()*1000,
              'mass_status':'Includes assumed 4 g board and 1.5 g small-hardware allowance; not weighed',
              'visual_aabb_max_error_m':max_geometry_error, 'inertia_and_serial_joint_transform_checks':'passed',
              'collision_hull_volume_sum_over_source':hull_ratios,
              'contact_trials':trials, 'physics_steps':steps_per_trial*len(cases), 'physics_timestep_s':model.opt.timestep,
              'physics_wall_seconds':time.monotonic()-start,
              'limitations':['Adjacent body collisions excluded; mechanical stops and joint limits uncalibrated',
                             'No proof of recovery; drop tests only establish finite contact dynamics',
                             'Hardware mass/COM/inertia and servo/sensor dynamics still provisional',
                             'Collision decomposition is approximate; volume agreement is not a spatial coverage bound'],
              'physical_robot_commands_sent':False, 'rl_training_performed':False}
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
