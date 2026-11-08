"""Static collision sweep of actual C3 geometry; does not infer servo hard stops."""
from pathlib import Path
import hashlib,json
import mujoco,numpy as np
HERE=Path(__file__).resolve().parent
path=HERE.parent/'robust/robot.xml';m=mujoco.MjModel.from_xml_path(str(path));d=mujoco.MjData(m)
# Hold the floating base clear of the floor. Only contacts between robot bodies
# constrain articulated clearance; do not disable adjacent-body masks/contacts.
rows=[]
for limit in (80,90,100,110):
    collisions=[];samples=0;byaxis={}
    for a in range(-limit,limit+1,2):
        for b in range(-limit,limit+1,2):
            d.qpos[:]=m.qpos0;d.qpos[2]=1.;d.qpos[-2:]=np.deg2rad([a,b]);mujoco.mj_forward(m,d);samples+=1
            contacts=[c for c in d.contact if m.geom_bodyid[c.geom1] and m.geom_bodyid[c.geom2] and c.dist<-.0002]
            if contacts:
                c=min(contacts,key=lambda c:c.dist)
                collisions.append({'q_deg':[a,b],'depth_mm':float(-c.dist*1000),
                  'bodies':[m.body(int(m.geom_bodyid[g])).name for g in (c.geom1,c.geom2)],
                  'geoms':[m.geom(g).name for g in (c.geom1,c.geom2)]})
    for joint in (0,1):
        bad=[]
        for deg in np.arange(-120,120.01,.5):
            d.qpos[:]=m.qpos0;d.qpos[2]=1.;d.qpos[-2:]=0;d.qpos[-2+joint]=np.deg2rad(deg);mujoco.mj_forward(m,d)
            contacts=[c for c in d.contact if m.geom_bodyid[c.geom1] and m.geom_bodyid[c.geom2] and c.dist<-.0002]
            if contacts:bad.append(float(deg))
        byaxis[str(joint)]={'first_positive_clash_deg':min((v for v in bad if v>0),default=None),'first_negative_clash_deg':max((v for v in bad if v<0),default=None)}
    row={'limit_deg':limit,'compound_grid_spacing_deg':2,'sampled_poses':samples,'poses_with_penetration_over_0_2mm':len(collisions),
         'max_penetration_mm':max((c['depth_mm'] for c in collisions),default=0),'examples':collisions[:12],'single_axis':byaxis}
    rows.append(row);print(json.dumps(row),flush=True)
r={'status':'static exterior geometry audit; no physical servo-travel claim','model_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
   'adjacent_contacts':'active with existing pivot-interface masks','floor':'base raised to 1 m to isolate self-contact',
   'ranges':rows,'limits':['2-degree compound grid is sampled, not a proof of all continuous paths.','Electrical PWM endpoints, internal servo stops, wires and flexible deformation are not represented.']}
(HERE/'range_audit.json').write_text(json.dumps(r,indent=2)+'\n')
