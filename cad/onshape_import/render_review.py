"""Two-view orthographic mesh preview without a plotting/font-cache dependency."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'geometry.json').read_text())
shaft=data['candidate_joints'][2]['origin_mm']
alignment=data['joint_alignment']['upper']
W,H=1800,1200
im=Image.new('RGB',(W,H),'#f4f6f8');draw=ImageDraw.Draw(im)
fontpath='/System/Library/Fonts/Supplemental/Arial.ttf'
def font(size):return ImageFont.truetype(fontpath,size)
colors={'base':np.array([.21,.53,.78]),'middle':np.array([.91,.57,.20]),'upper':np.array([.61,.39,.79])}
def view(panel,center,yaw,pitch,scale):
 cy,sy=np.cos(yaw),np.sin(yaw);cp,sp=np.cos(pitch),np.sin(pitch)
 matrix=np.array([[cy,-sy,0],[cp*sy,cp*cy,-sp],[sp*sy,sp*cy,cp]])
 def project(points):
  transformed=(np.asarray(points)-center)@matrix.T
  return np.c_[panel[0]+transformed[:,0]*scale,panel[1]-transformed[:,2]*scale],transformed[:,1]
 polygons=[];light=np.array([.3,-.6,.75]);light/=np.linalg.norm(light)
 for part in data['parts'].values():
  vertices=np.array(part['vertices']);tri=np.array(part['triangles']);faces=vertices[tri]
  normal=np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
  shade=.58+.42*np.abs(normal@light)
  projected,depth=project(vertices)
  for i,indices in enumerate(tri):
   points=projected[indices]
   if not (points[:,0].max()<panel[2] or points[:,0].min()>panel[3] or points[:,1].max()<panel[4] or points[:,1].min()>panel[5]):
    polygons.append((float(depth[indices].mean()),points,tuple((255*colors[part['group']]*shade[i]).astype(int))))
 # Camera looks along +Y; farther surfaces are painted first.
 layer=Image.new('RGB',(W,H),'#f4f6f8');ld=ImageDraw.Draw(layer)
 for _,points,color in sorted(polygons,key=lambda x:x[0],reverse=True):ld.polygon([tuple(p) for p in points],fill=color)
 im.paste(layer.crop((panel[2],panel[4],panel[3],panel[5])),(panel[2],panel[4]))
 for a,b,col in [([-29,0,24.4],[29,0,24.4],'#18232c'),([-2.35,-30,61.4],[-2.35,30,61.4],'#18232c'),([shaft[0],-30,shaft[2]],[shaft[0],30,shaft[2]],'#df2834')]:
  points,_=project([a,b])
  if all(panel[2]<=p[0]<=panel[3] and panel[4]<=p[1]<=panel[5] for p in points):draw.line([tuple(p) for p in points],fill=col,width=3)
view((450,610,30,870,150,1000),np.array([0,0,74.5]),-.73,.28,5.2)
view((1340,600,900,1770,150,1000),np.array([-2.35,0,65]),.05,0,14)
draw.text((65,35),'FINAL ONSHAPE ASSEMBLY / JOINT REVIEW',font=font(35),fill='#172b3b')
draw.text((150,110),'As exported: proposed rigid groups',font=font(25),fill='#172b3b')
draw.text((1000,110),'Upper joint: alignment review',font=font(25),fill='#172b3b')
for x,(key,label) in zip((430,790,1150),(('base','Base group'),('middle','Middle group'),('upper','Upper group'))):
 draw.rectangle((x,1015,x+25,1040),fill=tuple((colors[key]*255).astype(int)))
 draw.text((x+38,1010),label,font=font(25),fill='#172b3b')
draw.text((65,1070),'Black: structural axes  |  Red: upper servo shaft (as exported)',font=font(24),fill='#172b3b')
draw.text((65,1110),f"Upper structure Z=61.40 mm | Shaft Z={shaft[2]:.2f} mm | Remaining axis offset={alignment['distance_mm']:.2f} mm",font=font(24),fill='#9c3235')
draw.text((65,1153),'Corrected export, original placements retained. Structural upper axis is the user-confirmed reference.',font=font(20),fill='#52616c')
im.save(ROOT/'review.png')
print('Wrote review.png',flush=True)
