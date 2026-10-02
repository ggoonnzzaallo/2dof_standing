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
DECK_Z, DECK_T = 13.0, 3.0
J1_Z, J2_Z, TIP_Z = 42.0, 87.0, 145.0
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
AXIAL_SHIFT = -18.0  # bring the rotating arm back onto the base centerline
HORN_FACE = 16.5 + AXIAL_SHIFT  # provisional OEM horn face in assembly coordinates
PAD_T = 3.0
M2_CLEAR = 2.2
BEARING_OD, BEARING_ID, BEARING_W = 8.0, 3.0, 3.0  # MR83ZZ
PIN_D, PIN_L = 3.0, 12.0
BEARING_INNER_X = 27.0 + AXIAL_SHIFT
PIN_INNER_X = 20.5 + AXIAL_SHIFT
HUB_OUTER_X = 23.5 + AXIAL_SHIFT

def box(x,y,z,center):
    return cq.Workplane('XY').box(x,y,z).translate(center)

def tapered_foot(z0,z1,center_xy,lower_xy,upper_xy):
    """Broad load-spreading root, narrowed into a bearing-support cheek."""
    return (cq.Workplane('XY').workplane(offset=z0).rect(*lower_xy)
            .workplane(offset=z1-z0).rect(*upper_xy).loft(combine=True)
            .translate((center_xy[0],center_xy[1],0)))

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
    # The front hoop sits behind the two servo ears. The same local-axis cage
    # is used at both joints; the upper one is only rotated into position.
    r=box(3.5,22,FLANGE_SPAN+6.5,(-.95,0,z-OUTPUT_OFFSET_Z)).edges('|X').fillet(3)
    r=r.cut(box(9,BODY_W+2*CLEARANCE,BODY_L+2*CLEARANCE,
                (-.95,0,z-OUTPUT_OFFSET_Z)))
    for dz in (MOUNT_TOP_Z,MOUNT_BOTTOM_Z):
        r=r.cut(hole_x(-4,0,z+dz,M2_CLEAR,7))
    return r

def servo_cage_x(z):
    """Open-ended, two-sided servo cradle with a continuous printed load path.

    The body inserts from the output/horn side through both hoops. Side rails
    tie the rear collar to the mounting frame while leaving the case, mounting
    screws, and rear lead exit accessible. All clearances remain provisional.
    """
    rear=box(3.5,22,30,(-14,0,z-OUTPUT_OFFSET_Z)).edges('|X').fillet(3)
    rear=rear.cut(box(6,BODY_W+2*CLEARANCE,BODY_L+2*CLEARANCE,
                      (-14,0,z-OUTPUT_OFFSET_Z)))
    cage=ring_x(z).union(rear)
    for yy in (-9,9):
        rail=box(14,3.5,8,(-7.5,yy,z-OUTPUT_OFFSET_Z)).edges('|X').fillet(1.5)
        cage=cage.union(rail)
    return cage

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
    return hole_x(HORN_FACE,0,z,28,PAD_T)

def outboard_hub_x(z):
    """Moving journal. Pin bore is blind, preserving the horn screw cavity."""
    hub=hole_x(HORN_FACE+PAD_T-.2,0,z,12,HUB_OUTER_X-(HORN_FACE+PAD_T-.2))
    return hub.cut(hole_x(PIN_INNER_X,0,z,3.05,HUB_OUTER_X-PIN_INNER_X+.2))

def bearing_block_x(z):
    """Rounded bearing cheek with an outside-in seat and inner shoulder."""
    block=(cq.Workplane('YZ',origin=(25+AXIAL_SHIFT,0,0))
           .moveTo(-8,z-9).lineTo(8,z-9).lineTo(8,z+1)
           .threePointArc((0,z+9),(-8,z+1)).close().extrude(5))
    return cut_pivot_x(block,z)

def cut_pivot_x(shape,z):
    # Rear relief clears the rotating inner ring; the annular shoulder bears
    # only near the OD of the stationary outer ring.
    shape=shape.cut(hole_x(24.8+AXIAL_SHIFT,0,z,6.2,5.4))
    return shape.cut(hole_x(BEARING_INNER_X,0,z,8.05,3.2))

def cut_upper_pivot(shape):
    shape=shape.cut(to_upper(hole_x(24.8+AXIAL_SHIFT,0,0,6.2,5.4)))
    return shape.cut(to_upper(hole_x(BEARING_INNER_X,0,0,8.05,3.2)))

def bearing_x(z):
    return hole_x(BEARING_INNER_X,0,z,BEARING_OD,BEARING_W).cut(
        hole_x(BEARING_INNER_X-.1,0,z,BEARING_ID,BEARING_W+.2))

def pin_x(z):
    return hole_x(PIN_INNER_X,0,z,PIN_D,PIN_L)

def to_upper(s):
    return s.rotate((0,0,0),(0,0,1),90).translate((0,0,J2_Z))

base=cq.Workplane('XY').box(BASE_X,BASE_Y,BASE_T,centered=(True,True,False)).edges('|Z').fillet(5)
# Centered battery tunnel: lower floor and upper structural deck, open at +X
# for pack insertion. The deck also gives the two lower joint supports one
# continuous load path into the base instead of two narrow feet.
deck=cq.Workplane('XY').box(BASE_X,30,DECK_T,centered=(True,True,False)).translate((0,0,DECK_Z)).edges('|Z').fillet(3)
base=base.union(deck)
for yy in (-12,12):
    base=base.union(box(68,3,10,(0,yy,8)))
base=base.union(box(2,21,10,(-33,0,8)))
# The battery is retained by a tie through the two windows at the open end.
for yy in (-12,12):
    base=base.cut(box(3.5,6,3.2,(32,yy,8)))
base=base.union(servo_cage_x(J1_Z).translate((AXIAL_SHIFT,0,0)))
base=base.union(box(5,16,J1_Z-23.6,(27.5+AXIAL_SHIFT,0,(DECK_Z+DECK_T-.2+J1_Z-8)/2)))
base=base.union(tapered_foot(15.8,23,(27.5+AXIAL_SHIFT,0),(9,20),(5,16)))
base=base.union(bearing_block_x(J1_Z))
base=cut_pivot_x(base,J1_Z)
# Two short ribs reinforce the ear frame without obstructing the servo case.
for yy in (-9,9):
    base=base.union(box(9,4,8,(AXIAL_SHIFT-4,yy,19)))
# Cable-tie slots for board and power switch on the two low side shelves.
for x in (-13.5,13.5):
    base=base.cut(box(3.2,3,5,(x,22.5,1.5)))
for x in (-10,10):
    base=base.cut(box(3.2,3,5,(x,-22.5,1.5)))

link=adapter_x(J1_Z)
spine=box(12,14,J2_Z-J1_Z-26,(0,0,(J1_Z+11+J2_Z-15)/2)).edges('|Z').fillet(3)
link=link.union(spine)
# Both upper joint supports grow from the centered spine. The servo-side web
# is below its case; the bearing-side web is short and clear of the paddle.
upper_cage=to_upper(servo_cage_x(0).translate((AXIAL_SHIFT,0,0)))
link=link.union(upper_cage)
link=link.union(box(14,20,6,(0,-9.5,J2_Z-26)))
link=link.union(box(16,5,14.4,(0,9.5,J2_Z-15)))
link=link.union(tapered_foot(J2_Z-23,J2_Z-15,(0,9.5),(20,9),(16,5)))
link=link.union(to_upper(bearing_block_x(0)))
link=cut_upper_pivot(link)
link=cut_adapter(link,J1_Z)
link=link.union(outboard_hub_x(J1_Z))

paddle=to_upper(adapter_x(0))
paddle=paddle.union(box(16,10,TIP_Z-J2_Z-19,(0,0,(TIP_Z+J2_Z+3)/2)).edges('|Z').fillet(3))
paddle=paddle.union(box(22,10,8,(0,0,TIP_Z-4)).edges('|Z').fillet(3))
paddle=paddle.rotate((0,0,J2_Z),(0,0,J2_Z+1),-90).translate((0,0,-J2_Z))
paddle=cut_adapter(paddle,0).rotate((0,0,0),(0,0,1),90).translate((0,0,J2_Z))
paddle=paddle.union(to_upper(outboard_hub_x(0)))

# Nominal OEM horn envelopes. For visualization only: spline is deliberately
# not printed. Actual horn geometry must be measured before final release.
horn=hole_x(14.2,0,0,9,2.3).union(box(2.3,5,21,(15.35,0,0)))
horn=horn.cut(hole_x(13.9,0,0,2.2,4))

parts={
    'base':(base,(.20,.56,.57)),
    'middle_link':(link,(.26,.69,.66)),
    'paddle':(paddle,(.95,.64,.25)),
    'servo_1_envelope':(servo().translate((AXIAL_SHIFT,0,J1_Z)),(.17,.19,.22)),
    'servo_2_envelope':(to_upper(servo().translate((AXIAL_SHIFT,0,0))),(.17,.19,.22)),
    'horn_1_envelope':(horn.translate((AXIAL_SHIFT,0,J1_Z)),(.87,.87,.82)),
    'horn_2_envelope':(to_upper(horn.translate((AXIAL_SHIFT,0,0))),(.87,.87,.82)),
    'bearing_1_envelope':(bearing_x(J1_Z),(.70,.74,.78)),
    'bearing_2_envelope':(to_upper(bearing_x(0)),(.70,.74,.78)),
    'pin_1_envelope':(pin_x(J1_Z),(.83,.83,.87)),
    'pin_2_envelope':(to_upper(pin_x(0)),(.83,.83,.87)),
    'battery_envelope':(box(59.5,19,7.5,(0,0,7.25)),(.67,.70,.73)),
    'controller_envelope':(box(21,17.8,4,(0,22.5,5)),(.15,.33,.40)),
    'switch_envelope':(box(15.24,15.24,3,(0,-22.5,4.5)),(.65,.21,.24)),
}
assembly=cq.Assembly(name='self_righting_robot_concept')
summary={'status':'TWO-SIDED CAGED PTK 7465 MG PROVISIONAL: non-W servo dimensions, horn fit, battery tunnel, outboard pivot fit, full travel and physical righting unvalidated','units':'mm','servo_model':SERVO_MODEL,'nominal_servo_dimensions_mm':{'body_length':BODY_L,'body_width':BODY_W,'body_depth':BODY_DEPTH,'flange_span':FLANGE_SPAN,'mount_pitch':MOUNT_PITCH,'output_offset_from_body_midpoint':OUTPUT_OFFSET_Z,'servo_axial_shift':AXIAL_SHIFT,'horn_face_robot_coordinate':HORN_FACE},'servo_cages':{'front_and_rear_outer_width_mm':22,'rear_collar_outer_height_mm':30,'rail_count_per_servo':2,'rail_section_mm':[3.5,8],'body_clearance_per_side_mm':CLEARANCE,'rear_end':'open for servo lead'},'outboard_pivots':{'bearing':'MR83ZZ 3x8x3 mm','pin':'3x12 mm','bearing_axis_start_mm':BEARING_INNER_X,'moving_hub_outer_face_mm':HUB_OUTER_X},'base_footprint_mm':[BASE_X,BASE_Y],'deck_top_z_mm':DECK_Z+DECK_T,'battery_tunnel_inner_width_mm':21,'joint_origins_mm':[[0,0,J1_Z],[0,0,J2_Z]],'axes_upright':[[1,0,0],[0,1,0]],'parts':{}}
for name,(shape,color) in parts.items():
    solid=shape.val()
    assert solid.isValid(),f'Invalid CAD: {name}'
    if name in ('base','middle_link','paddle'):
        assert len(shape.solids().vals())==1,f'Disconnected print: {name}'
        cq.exporters.export(shape,str(OUT/f'{name}.step'))
        cq.exporters.export(shape,str(OUT/f'{name}.stl'),tolerance=.05,angularTolerance=.15)
    assembly.add(shape,name=name,color=cq.Color(*color))
    vertices,triangles=solid.tessellate(.3)
    summary['parts'][name]={'volume_mm3':solid.Volume(),'color':color,'vertices':[[v.x,v.y,v.z] for v in vertices],'triangles':triangles}

# Small, disposable fit prints let the received servo/horn settle uncertain
# dimensions before a full base or moving link is printed.
battery_tunnel_coupon=box(22,30,3,(0,0,1.5)).union(box(22,30,3,(0,0,14.5)))
for yy in (-12,12):
    battery_tunnel_coupon=battery_tunnel_coupon.union(box(22,3,10,(0,yy,8)))
fit_coupons={
    'servo_mount_fit_coupon':servo_cage_x(0),
    'horn_fit_coupon':cut_adapter(adapter_x(0),0),
    'pivot_fit_coupon':bearing_block_x(0).union(box(9,5,4,(5,0,-6))).union(outboard_hub_x(-12)),
    'battery_tunnel_fit_coupon':battery_tunnel_coupon,
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
