"""Render actual exported geometry, not a generated concept illustration."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

p=Path(__file__).resolve().parent
d=json.loads((p/'geometry.json').read_text())
fig=plt.figure(figsize=(12,8),facecolor='#f5f6f4')
for i,az in enumerate((-55,35)):
    ax=fig.add_subplot(1,2,i+1,projection='3d',facecolor='#f5f6f4')
    for name,part in d['parts'].items():
        verts=np.array(part['vertices']); faces=verts[np.array(part['triangles'])]
        normals=np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0])
        normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
        light=np.array([.3,-.5,.8]); light/=np.linalg.norm(light)
        brightness=.55+.45*np.abs(normals@light)
        ax.add_collection3d(Poly3DCollection(faces,facecolors=np.array(part['color'])*brightness[:,None],linewidths=0))
    ax.set(xlim=(-45,45),ylim=(-45,45),zlim=(0,140))
    ax.set_box_aspect((90,90,140)); ax.view_init(21,az); ax.set_axis_off()
    ax.quiver(0,0,27,25,0,0,color='#c64d45',arrow_length_ratio=.25,linewidth=2)
    ax.quiver(0,0,72,0,25,0,color='#5075bc',arrow_length_ratio=.25,linewidth=2)
    ax.text(25,0,27,' J1 · X',color='#9c3535',fontsize=10)
    ax.text(0,25,72,' J2 · Y',color='#365aa0',fontsize=10)
fig.suptitle('SELF-RIGHTING ARM  /  REV A CONCEPT',x=.08,ha='left',fontsize=20,fontweight='bold',y=.96)
fig.text(.08,.90,'70 × 64 mm base  •  132 mm upright  •  orthogonal serial joints',fontsize=13,color='#48565b')
fig.text(.08,.065,'Teal: printed base + middle link    Amber: printed paddle    Gray: servo + battery envelopes',fontsize=11,color='#48565b')
fig.text(.08,.025,'Prototype CAD — OEM horn fit, fastener clearance, full motion and self-righting require physical validation.',fontsize=10,color='#9c3535')
fig.subplots_adjust(left=0,right=1,bottom=.1,top=.88,wspace=-.15)
fig.savefig(p/'preview.png',dpi=170,facecolor=fig.get_facecolor())
