from pathlib import Path
import json
import mujoco,numpy as np
H=Path(__file__).resolve().parent;m=mujoco.MjModel.from_xml_path(str(H.parent/'robust/robot.xml'));d=mujoco.MjData(m)
rows=[]
for low,upper in [(90,90),(90,110)]:
 bad=[];minimum=0.;samples=0
 for a in np.arange(-low,low+.1,1):
  for b in np.arange(-upper,upper+.1,1):
   d.qpos[:]=m.qpos0;d.qpos[2]=1;d.qpos[-2:]=np.deg2rad([a,b]);mujoco.mj_forward(m,d);samples+=1
   con=[c for c in d.contact if m.geom_bodyid[c.geom1] and m.geom_bodyid[c.geom2]]
   depth=min((c.dist for c in con),default=0);minimum=min(minimum,depth)
   if depth<-.0002 and len(bad)<10:bad.append({'q_deg':[float(a),float(b)],'penetration_mm':float(-depth*1000)})
 rows.append({'lower_limit_deg':low,'upper_limit_deg':upper,'grid_deg':1,'samples':samples,'max_penetration_mm':float(-minimum*1000),'collision_examples':bad});print(rows[-1],flush=True)
(H/'asymmetric_audit.json').write_text(json.dumps(rows,indent=2)+'\n')
