"""Original parametric concept, millimetres. Requires cadquery >=2.5.

FT90M body/flange dimensions from manufacturer drawing; horn-plane offset and
horn hole radii are fit-check parameters, not measured hardware dimensions.
Exported STEP/STLs are prototype geometry, not a tested production release.
"""
from pathlib import Path
import json
import cadquery as cq

OUT = Path(__file__).resolve().parent
BASE_X, BASE_Y, BASE_T = 70.0, 64.0, 3.0
J1_Z, J2_Z, TIP_Z = 27.0, 72.0, 132.0
BODY_L, BODY_W = 23.3, 12.1
CLEARANCE = 0.30  # radial / per-side cavity clearance
HORN_FACE = 13.8  # fit-check: OEM horn's outer face from robot centre
PAD_T = 2.5
M2_CLEAR = 2.2

def box(x,y,z,center):
    return cq.Workplane('XY').box(x,y,z).translate(center)

def hole_x(x,y,z,d,length):
    return cq.Workplane('YZ',origin=(x,y,z)).circle(d/2).extrude(length)

def hole_y(x,y,z,d,length):
    # XZ normal is -Y.
    return cq.Workplane('XZ',origin=(x,y,z)).circle(d/2).extrude(length)

def servo():
    """Servo axis is +X; output centre at y=z=0. Back face x=-16."""
    s=box(21.45,BODY_W,BODY_L,(-16+21.45/2,0,-5.8))
    s=s.union(hole_x(5.45,0,0,11,3.8))
    s=s.union(box(1.6,BODY_W,32.5,(1.6,0,-5.7)))
    s=s.union(hole_x(9.25,0,0,3.95,3.2))
    for z in (8.55,-19.95):
        s=s.cut(hole_x(-1,0,z,2,6))
    return s

def ring_x(z):
    r=box(3,21,38,(-.7,0,z-5))
    r=r.cut(box(8,BODY_W+2*CLEARANCE,BODY_L+2*CLEARANCE,(-.7,0,z-5.8)))
    for dz in (8.55,-19.95):
        r=r.cut(hole_x(-3,0,z+dz,M2_CLEAR,6))
    return r

def cut_adapter(a,z):
    a=a.cut(hole_x(HORN_FACE-1,0,z,5.2,10))
    # Four radial slots accept an OEM cross/double horn, drilled to 2.2 mm.
    for rot in (0,90,180,270):
        slot=cq.Workplane('YZ',origin=(HORN_FACE-1,0,z)).center(0,7.5).slot2D(5,M2_CLEAR,90).extrude(10)
        slot=slot.rotate((0,0,z),(1,0,z),rot)
        a=a.cut(slot)
    return a

def adapter_x(z):
    # Keep a 2 mm rim beyond slot ends; tangency to the outer circle makes
    # non-manifold STL edges even when the B-rep kernel accepts the solid.
    return hole_x(HORN_FACE,0,z,24,PAD_T)

base=cq.Workplane('XY').box(BASE_X,BASE_Y,BASE_T,centered=(True,True,False)).edges('|Z').fillet(5)
base=base.union(ring_x(J1_Z))
# Stiffen the base mount without blocking the servo's rear body.
for yy in (-9,9):
    base=base.union(box(8,3,6,(-3,yy,5)))
# Battery locating rails: the straps restrain it; do not crush the pouch.
for yy in (-31,-10):
    base=base.union(box(60,1.4,2,(0,yy,4)))
# Strap slots for battery (59.5 x 19 x 7.5), controller and power switch.
strap_sets=[(-22,-20.5,21),(22,-20.5,21),(23,18,20),(-23,18,18)]
for x,y,span in strap_sets:
    for sy in (-1,1):
        base=base.cut(box(3.2,2,10,(x,y+sy*span/2,3)))
    base=base.cut(box(3.2,span+3,1.2,(x,y,.5)))

link=adapter_x(J1_Z)
link=link.union(box(PAD_T,12,J2_Z-J1_Z-8,(HORN_FACE+PAD_T/2,0,(J1_Z+8+J2_Z)/2)))
# Rotate a second servo mount 90 degrees to make its output axis +Y.
upper_ring=ring_x(0).rotate((0,0,0),(0,0,1),90).translate((0,0,J2_Z))
link=link.union(upper_ring)
link=link.union(box(17,3,5,(8,-1.7,J2_Z-23)))
link=cut_adapter(link,J1_Z)

paddle=adapter_x(0).rotate((0,0,0),(0,0,1),90).translate((0,0,J2_Z))
paddle=paddle.union(box(16,5.5,TIP_Z-J2_Z-8,(0,HORN_FACE+2.75,(TIP_Z+J2_Z+8)/2)))
paddle=paddle.union(box(24,7,8,(0,HORN_FACE+3.5,TIP_Z-4)))
paddle=paddle.rotate((0,0,J2_Z),(0,0,J2_Z+1),-90).translate((0,0,-J2_Z))
paddle=cut_adapter(paddle,0).rotate((0,0,0),(0,0,1),90).translate((0,0,J2_Z))

# Nominal OEM horn envelopes. For visualization only: spline is deliberately
# not printed. Actual horn geometry must be measured before final release.
horn=hole_x(11.5,0,0,9,2.3).union(box(2.3,5,21,(12.65,0,0)))
horn=horn.cut(hole_x(11,0,0,2.2,4))

# A strapped bridge shields the pouch face; end feet carry strap preload.
# Open long sides provide clearance for wires. Add thin insulation below PCB.
battery_guard=box(63,20,1.5,(0,-20.5,13.25))
for xx in (-30.9,30.9):
    battery_guard=battery_guard.union(box(1.2,20,10.5,(xx,-20.5,8.25)))

parts={
    'base':(base,(.20,.56,.57)),
    'middle_link':(link,(.26,.69,.66)),
    'paddle':(paddle,(.95,.64,.25)),
    'battery_guard':(battery_guard,(.42,.65,.65)),
    'servo_1_envelope':(servo().translate((0,0,J1_Z)),(.17,.19,.22)),
    'servo_2_envelope':(servo().rotate((0,0,0),(0,0,1),90).translate((0,0,J2_Z)),(.17,.19,.22)),
    'horn_1_envelope':(horn.translate((0,0,J1_Z)),(.87,.87,.82)),
    'horn_2_envelope':(horn.rotate((0,0,0),(0,0,1),90).translate((0,0,J2_Z)),(.87,.87,.82)),
    'battery_envelope':(box(59.5,19,7.5,(0,-20.5,7.75)),(.67,.70,.73)),
    'controller_envelope':(box(21,17.8,4,(23,18,6)),(.15,.33,.40)),
    'switch_envelope':(box(15.24,15.24,3,(-23,18,5.5)),(.65,.21,.24)),
}
assembly=cq.Assembly(name='self_righting_robot_concept')
summary={'status':'CONCEPT: horn fit, full travel and physical righting unvalidated','units':'mm','base_mm':[BASE_X,BASE_Y,BASE_T],'joint_origins_mm':[[0,0,J1_Z],[0,0,J2_Z]],'axes_upright':[[1,0,0],[0,1,0]],'parts':{}}
for name,(shape,color) in parts.items():
    solid=shape.val()
    assert solid.isValid(),f'Invalid CAD: {name}'
    if name in ('base','middle_link','paddle','battery_guard'):
        assert len(shape.solids().vals())==1,f'Disconnected print: {name}'
        cq.exporters.export(shape,str(OUT/f'{name}.step'))
        cq.exporters.export(shape,str(OUT/f'{name}.stl'),tolerance=.05,angularTolerance=.15)
    assembly.add(shape,name=name,color=cq.Color(*color))
    vertices,triangles=solid.tessellate(.3)
    summary['parts'][name]={'volume_mm3':solid.Volume(),'color':color,'vertices':[[v.x,v.y,v.z] for v in vertices],'triangles':triangles}
assembly.save(str(OUT/'assembly.step'))
(OUT/'geometry.json').write_text(json.dumps(summary))
print(json.dumps({k:round(v['volume_mm3'],1) for k,v in summary['parts'].items()},indent=2))
clashes=[]
names=list(parts)
for i,n in enumerate(names):
    for m in names[i+1:]:
        volume=parts[n][0].intersect(parts[m][0]).val().Volume()
        if volume>0.1:
            clashes.append({'parts':[n,m],'overlap_mm3':round(volume,2)})
(OUT/'nominal_clashes.json').write_text(json.dumps(clashes,indent=2))
print('Nominal overlaps:',clashes)
