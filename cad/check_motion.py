"""Coarse rigid-envelope sweep. Does not include wires, screws or real horn shapes."""
import json
from pathlib import Path
from build_cad import parts,J1_Z,J2_Z

def rot1(s,a):return s.rotate((0,0,J1_Z),(1,0,J1_Z),a)
def rot2(s,a):return s.rotate((0,0,J2_Z),(0,1,J2_Z),a)
def overlaps(a,b):
    x=a.val().BoundingBox(); y=b.val().BoundingBox()
    if any(getattr(x,k+'max')<=getattr(y,k+'min') or getattr(y,k+'max')<=getattr(x,k+'min') for k in 'xyz'):return 0.
    return a.intersect(b).val().Volume()
fixed={n:parts[n][0] for n in ('base','servo_1_envelope','bearing_1_envelope','battery_envelope','controller_envelope','switch_envelope')}
records=[]
angles=list(range(-80,81,20))
for a in angles:
    mid={n:rot1(parts[n][0],a) for n in ('middle_link','servo_2_envelope','bearing_2_envelope','pin_1_envelope')}
    for b in angles:
        upper={n:rot1(rot2(parts[n][0],b),a) for n in ('paddle','pin_2_envelope')}
        for n,s in mid.items():
            for m,t in fixed.items():
                v=overlaps(s,t)
                if v>.1: records.append({'q1_deg':a,'q2_deg':b,'parts':[n,m],'volume_mm3':round(v,2)})
        for n,s in upper.items():
            for m,t in {**fixed,**mid}.items():
                v=overlaps(s,t)
                if v>.1: records.append({'q1_deg':a,'q2_deg':b,'parts':[n,m],'volume_mm3':round(v,2)})
result={'grid_angles_deg':angles,'configurations':len(angles)**2,'scope':'Rigid nominal envelopes including outboard bearings and pins; excludes horns, fasteners and wires. Discrete samples only.','clashes':records}
Path(__file__).with_name('motion_check.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
