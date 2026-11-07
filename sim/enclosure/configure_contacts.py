"""Keep adjacent-link dynamics, exempt only convex pieces contained in pivot sleeves.

The entire convex piece must lie within a 6 mm radius of its hinge axis.
This disables that piece against its adjacent link, not against the floor or
nonadjacent link. No body-pair exclusions or per-contact Python callbacks.
"""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from model_geometry import geom_vertices_world

def configure(path=HERE/'robot.xml'):
    model=mujoco.MjModel.from_xml_path(str(path));data=mujoco.MjData(model);mujoco.mj_forward(model,data)
    bodies={n:model.body(n).id for n in ('base','middle','upper')}
    joints={1:model.joint('j1').id,2:model.joint('j2').id}
    group_for={bodies[n]:n for n in bodies}
    candidate_joints={'base':[1],'middle':[1,2],'upper':[2]}
    rows=[]
    for i in range(model.ngeom):
        if not model.geom_contype[i]:continue
        body=int(model.geom_bodyid[i])
        if body==0:rows.append({'name':model.geom(i).name,'group':'world','near':()});continue
        group=group_for[body];points=geom_vertices_world(model,data,i);near=[]
        for n in candidate_joints[group]:
            jid=joints[n];r=points-data.xanchor[jid];a=data.xaxis[jid]
            radial=np.linalg.norm(r-np.outer(r@a,a),axis=1)
            if radial.max()<=.006+1e-8:near.append(n)
        rows.append({'name':model.geom(i).name,'group':group,'near':tuple(near)})
    classes=sorted(set((r['group'],r['near']) for r in rows))
    bits={c:1<<i for i,c in enumerate(classes)}
    def compatible(a,b):
        ga,na=a;gb,nb=b
        if ga==gb:return False
        if 'world' in (ga,gb):return True
        joint=1 if {ga,gb}=={'base','middle'} else 2 if {ga,gb}=={'middle','upper'} else None
        return joint is None or (joint not in na and joint not in nb)
    tree=ET.parse(path);xml=tree.getroot();geoms={g.get('name'):g for g in xml.findall('.//geom') if g.get('name')}
    for r in rows:
        cls=(r['group'],r['near']);g=geoms[r['name']]
        g.set('contype',str(bits[cls]));g.set('conaffinity',str(sum(bit for other,bit in bits.items() if compatible(cls,other))))
    assert not xml.findall('./contact/exclude')
    ET.indent(tree,space='  ');tree.write(path,encoding='unicode')
    report={'method':__doc__,'pivot_sleeve_radius_mm':6.,'whole_body_exclusions':0,
        'excluded_pieces':[r for r in rows if r['near']],
        'classes':[{'group':g,'near_joints':n,'bit':b} for (g,n),b in bits.items()],
        'limitation':'Sleeve pieces are intentionally not collidable against the adjacent body; real bearing fit and clearance remain approximate.'}
    (Path(path).parent/'contact_policy.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Selective contacts:',len(report['excluded_pieces']),'small sleeve pieces;',len(rows),'total collision geoms; no body exclusions',flush=True)
    return report
if __name__=='__main__':configure()
