"""PTK 7465 MG concept, millimetres. Requires cadquery >=2.5.

The nominal envelope uses the published 7465-family dimensions, including a
7465W drawing as a proxy for flange details. Horn and mounting dimensions
must be checked against the delivered non-W servos before final printing.
"""
from pathlib import Path
import json
import cadquery as cq

OUT = Path(__file__).resolve().parent
BASE_X, BASE_Y, BASE_T = 70.0, 64.0, 3.0
J1_Z, J2_Z, TIP_Z = 27.0, 72.0, 132.0
SERVO_MODEL = 'PTK 7465 MG (nominal 7465-family envelope; incoming fit check required)'
BODY_L, BODY_W, BODY_DEPTH = 23.9, 12.0, 22.0
FLANGE_SPAN, MOUNT_PITCH = 31.8, 27.8
OUTPUT_OFFSET_Z = 6.0  # output axis from body long-axis midpoint, toward one end
FLANGE_FROM_BACK = 18.4  # published side-view nominal, front mounting face
SERVO_BACK_X = -16.0
FLANGE_FRONT_X = SERVO_BACK_X + FLANGE_FROM_BACK
FLANGE_T = 1.6
MOUNT_TOP_Z = -OUTPUT_OFFSET_Z + MOUNT_PITCH/2
MOUNT_BOTTOM_Z = -OUTPUT_OFFSET_Z - MOUNT_PITCH/2
CLEARANCE = 0.30  # radial / per-side cavity clearance
HORN_FACE = 16.5  # provisional OEM horn's outer face from joint centre
PAD_T = 2.5
M2_CLEAR = 2.2
BEARING_OD, BEARING_ID, BEARING_W = 8.0, 3.0, 3.0  # MR83ZZ
PIN_D, PIN_L = 3.0, 12.0
BEARING_INNER_X = 27.0
PIN_INNER_X = 20.0
HUB_OUTER_X = 23.5

def box(x,y,z,center):
    return cq.Workplane('XY').box(x,y,z).translate(center)

def hole_x(x,y,z,d,length):
    return cq.Workplane('YZ',origin=(x,y,z)).circle(d/2).extrude(length)

def hole_y(x,y,z,d,length):
    # XZ normal is -Y.
    return cq.Workplane('XZ',origin=(x,y,z)).circle(d/2).extrude(length)

def servo():
    """Approximate PTK envelope; axis +X, output centre y=z=0."""
    s=box(BODY_DEPTH,BODY_W,BODY_L,
          (SERVO_BACK_X+BODY_DEPTH/2,0,-OUTPUT_OFFSET_Z))
    s=s.union(hole_x(SERVO_BACK_X+BODY_DEPTH,0,0,11,4.4))
    s=s.union(box(FLANGE_T,BODY_W,FLANGE_SPAN,
                  (FLANGE_FRONT_X-FLANGE_T/2,0,-OUTPUT_OFFSET_Z)))
    # 25T ~5 mm shaft; do not print or use this as a spline mating profile.
    s=s.union(hole_x(SERVO_BACK_X+BODY_DEPTH+4.4,0,0,5,3.7))
    for z in (MOUNT_TOP_Z,MOUNT_BOTTOM_Z):
        s=s.cut(hole_x(FLANGE_FRONT_X-FLANGE_T-.5,0,z,2,FLANGE_T+1))
    return s

def ring_x(z):
    # The mounting frame sits behind the two servo ears, leaving the body open.
    r=box(3,21,FLANGE_SPAN+5.5,(-.7,0,z-OUTPUT_OFFSET_Z))
    r=r.cut(box(8,BODY_W+2*CLEARANCE,BODY_L+2*CLEARANCE,
                (-.7,0,z-OUTPUT_OFFSET_Z)))
    for dz in (MOUNT_TOP_Z,MOUNT_BOTTOM_Z):
        r=r.cut(hole_x(-3,0,z+dz,M2_CLEAR,6))
    return r

def cut_adapter(a,z):
    # OEM 25T horn and its center screw pass through this access opening.
    # The print does not try to mate directly with the metal output spline.
    a=a.cut(hole_x(HORN_FACE-1,0,z,6.8,10))
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

def outboard_hub_x(z):
    """Moving journal. Pin bore is blind, preserving the horn screw cavity."""
    hub=hole_x(HORN_FACE+PAD_T-.2,0,z,12,HUB_OUTER_X-(HORN_FACE+PAD_T-.2))
    return hub.cut(hole_x(PIN_INNER_X,0,z,3.05,HUB_OUTER_X-PIN_INNER_X+.2))

def bearing_block_x(z):
    """Fixed support with an outside-in 3 mm bearing seat and inner shoulder."""
    block=box(5,14,16,(27.5,0,z))
    # Rear relief clears the rotating inner ring; the annular shoulder bears
    # only near the OD of the stationary outer ring.
    block=block.cut(hole_x(24.8,0,z,6.2,5.4))
    block=block.cut(hole_x(BEARING_INNER_X,0,z,8.05,3.2))
    return block

def bearing_x(z):
    return hole_x(BEARING_INNER_X,0,z,BEARING_OD,BEARING_W).cut(
        hole_x(BEARING_INNER_X-.1,0,z,BEARING_ID,BEARING_W+.2))

def pin_x(z):
    return hole_x(PIN_INNER_X,0,z,PIN_D,PIN_L)

def to_upper(s):
    return s.rotate((0,0,0),(0,0,1),90).translate((0,0,J2_Z))

base=cq.Workplane('XY').box(BASE_X,BASE_Y,BASE_T,centered=(True,True,False)).edges('|Z').fillet(5)
base=base.union(ring_x(J1_Z))
base=base.union(box(5,14,16.4,(27.5,0,11)))
base=base.union(bearing_block_x(J1_Z))
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
link=link.union(outboard_hub_x(J1_Z))
# The upper outboard bearing is held by a low side bridge. At y>25 it
# crosses underneath the paddle's axial envelope, outside the horn sweep.
link=link.union(box(4,29,5,(HORN_FACE+PAD_T/2,14,J2_Z-13)))
link=link.union(box(18,5,5,(9,27.5,J2_Z-13)))
link=link.union(box(8,5,8,(0,27.5,J2_Z-8)))
link=link.union(to_upper(bearing_block_x(0)))

paddle=adapter_x(0).rotate((0,0,0),(0,0,1),90).translate((0,0,J2_Z))
paddle=paddle.union(box(16,5.5,TIP_Z-J2_Z-8,(0,HORN_FACE+2.75,(TIP_Z+J2_Z+8)/2)))
paddle=paddle.union(box(24,7,8,(0,HORN_FACE+3.5,TIP_Z-4)))
paddle=paddle.rotate((0,0,J2_Z),(0,0,J2_Z+1),-90).translate((0,0,-J2_Z))
paddle=cut_adapter(paddle,0).rotate((0,0,0),(0,0,1),90).translate((0,0,J2_Z))
paddle=paddle.union(to_upper(outboard_hub_x(0)))

# Nominal OEM horn envelopes. For visualization only: spline is deliberately
# not printed. Actual horn geometry must be measured before final release.
horn=hole_x(14.2,0,0,9,2.3).union(box(2.3,5,21,(15.35,0,0)))
horn=horn.cut(hole_x(13.9,0,0,2.2,4))

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
    'bearing_1_envelope':(bearing_x(J1_Z),(.70,.74,.78)),
    'bearing_2_envelope':(to_upper(bearing_x(0)),(.70,.74,.78)),
    'pin_1_envelope':(pin_x(J1_Z),(.83,.83,.87)),
    'pin_2_envelope':(to_upper(pin_x(0)),(.83,.83,.87)),
    'battery_envelope':(box(59.5,19,7.5,(0,-20.5,7.75)),(.67,.70,.73)),
    'controller_envelope':(box(21,17.8,4,(23,18,6)),(.15,.33,.40)),
    'switch_envelope':(box(15.24,15.24,3,(-23,18,5.5)),(.65,.21,.24)),
}
assembly=cq.Assembly(name='self_righting_robot_concept')
summary={'status':'PTK 7465 MG PROVISIONAL: non-W servo dimensions, horn fit, outboard pivot fit, full travel and physical righting unvalidated','units':'mm','servo_model':SERVO_MODEL,'nominal_servo_dimensions_mm':{'body_length':BODY_L,'body_width':BODY_W,'body_depth':BODY_DEPTH,'flange_span':FLANGE_SPAN,'mount_pitch':MOUNT_PITCH,'output_offset_from_body_midpoint':OUTPUT_OFFSET_Z,'horn_face_from_joint_axis':HORN_FACE},'outboard_pivots':{'bearing':'MR83ZZ 3x8x3 mm','pin':'3x12 mm','bearing_axis_start_mm':BEARING_INNER_X,'moving_hub_outer_face_mm':HUB_OUTER_X},'base_mm':[BASE_X,BASE_Y,BASE_T],'joint_origins_mm':[[0,0,J1_Z],[0,0,J2_Z]],'axes_upright':[[1,0,0],[0,1,0]],'parts':{}}
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

# Small, disposable fit prints let the received servo/horn settle uncertain
# dimensions before a full base or moving link is printed.
fit_coupons={
    'servo_mount_fit_coupon':ring_x(0),
    'horn_fit_coupon':cut_adapter(adapter_x(0),0),
    'pivot_fit_coupon':bearing_block_x(0).union(box(14,5,4,(20,0,-6))).union(outboard_hub_x(-12)),
}
for name,shape in fit_coupons.items():
    assert shape.val().isValid() and len(shape.solids().vals())==1,name
    cq.exporters.export(shape,str(OUT/f'{name}.step'))
    cq.exporters.export(shape,str(OUT/f'{name}.stl'),tolerance=.05,angularTolerance=.15)
summary['fit_coupons']=list(fit_coupons)
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
