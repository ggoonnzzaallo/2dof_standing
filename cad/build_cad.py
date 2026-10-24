"""Reference-layout, two-sided PTK 7465 MG concept. Dimensions in millimetres.

The source robot uses four simple printed shapes: a foot, a dogleg middle arm,
a long upper arm and a small horn plate. This is original parametric geometry
in that arrangement, expanded only for our battery and rear bearing supports.
The servo and horn interface are provisional until the delivered parts are measured.
"""
from pathlib import Path
import json
import cadquery as cq

OUT = Path(__file__).resolve().parent
BASE_X, BASE_Y, BASE_T = 70.0, 68.0, 3.0
DECK_Z, DECK_T = 13.0, 3.0
J1_Z, J2_Z, TIP_Z = 42.0, 87.0, 170.0
SERVO_MODEL = 'PTK 7465 MG, provisional 7465-family dimensions'
BODY_L, BODY_W, BODY_DEPTH = 23.9, 12.0, 22.0
FLANGE_SPAN, MOUNT_PITCH = 31.8, 27.8
OUTPUT_OFFSET_Z = 6.0
SERVO_BACK_X, FLANGE_FROM_BACK, FLANGE_T = -16.0, 18.4, 1.6
FLANGE_FRONT_X = SERVO_BACK_X + FLANGE_FROM_BACK
MOUNT_TOP_Z = -OUTPUT_OFFSET_Z + MOUNT_PITCH/2
MOUNT_BOTTOM_Z = -OUTPUT_OFFSET_Z - MOUNT_PITCH/2
AXIAL_SHIFT = 5.5  # places servo inside the reference-like 44 mm moving bridge
HORN_FACE = 16.5 + AXIAL_SHIFT
M2_CLEAR = 2.2
BEARING_OD, BEARING_ID, BEARING_W = 8.0, 3.0, 3.0
REAR_BEARING_X = -26.0
REAR_TAB_X = -19.5
FRONT_TAB_X = HORN_FACE

def box(x, y, z, center):
    return cq.Workplane('XY').box(x, y, z).translate(center)

def hole_x(x, y, z, diameter, length):
    return cq.Workplane('YZ', origin=(x,y,z)).circle(diameter/2).extrude(length)

def to_upper(shape):
    return shape.rotate((0,0,0),(0,0,1),90).translate((0,0,J2_Z))

def servo():
    """Visible purchased-part envelope; local output axis is +X."""
    s=box(BODY_DEPTH,BODY_W,BODY_L,
          (SERVO_BACK_X+BODY_DEPTH/2,0,-OUTPUT_OFFSET_Z))
    s=s.union(hole_x(SERVO_BACK_X+BODY_DEPTH,0,0,11,4.4))
    s=s.union(box(FLANGE_T,BODY_W,FLANGE_SPAN,
                  (FLANGE_FRONT_X-FLANGE_T/2,0,-OUTPUT_OFFSET_Z)))
    s=s.union(hole_x(SERVO_BACK_X+BODY_DEPTH+4.4,0,0,5,3.7))
    for z in (MOUNT_TOP_Z,MOUNT_BOTTOM_Z):
        s=s.cut(hole_x(FLANGE_FRONT_X-FLANGE_T-.5,0,z,2,FLANGE_T+1))
    return s

def servo_mount(z):
    """Open L bracket: two ears and one side post, not a closed motor cage."""
    # Tabs contact the two servo mounting ears. The open middle shows the case.
    x=FLANGE_FRONT_X+AXIAL_SHIFT
    mount=box(3.2,17,3.8,(x-3.2,0,z+MOUNT_TOP_Z))
    mount=mount.union(box(3.2,17,3.8,(x-3.2,0,z+MOUNT_BOTTOM_Z)))
    mount=mount.union(box(3.2,3.5, MOUNT_TOP_Z-MOUNT_BOTTOM_Z,
                          (x-3.2,8.5,z+(MOUNT_TOP_Z+MOUNT_BOTTOM_Z)/2)))
    for dz in (MOUNT_TOP_Z,MOUNT_BOTTOM_Z):
        mount=mount.cut(hole_x(x-4.9,0,z+dz,M2_CLEAR,3.4))
    return mount

def rounded_tab(x,z):
    """12.5 mm wide plate with a rounded lower end, as in source arm STLs."""
    return (cq.Workplane('YZ',origin=(x,0,0))
            .moveTo(-6.25,z+20).lineTo(6.25,z+20)
            .lineTo(6.25,z-9).threePointArc((0,z-15.25),(-6.25,z-9))
            .close().extrude(4))

def horn_tab(z):
    tab=rounded_tab(FRONT_TAB_X,z)
    tab=tab.cut(hole_x(FRONT_TAB_X-.1,0,z,7.0,4.2))
    # The two side holes mate to a drilled OEM two-arm horn. Their radius is
    # provisional; the fit coupon exists so the real horn can set this value.
    for yy in (-3.3,3.3):
        tab=tab.cut(hole_x(FRONT_TAB_X-.1,yy,z+7.8,M2_CLEAR,4.2))
    return tab

def rear_tab(z):
    # A short inner boss gives the 12 mm pin more than 4 mm of retention while
    # retaining a nominal 2 mm gap to the back of the motor case.
    tab=rounded_tab(REAR_TAB_X,z)
    tab=tab.union(hole_x(-15.7,0,z,7,3.2))
    return tab.cut(hole_x(REAR_TAB_X-.1,0,z,3.05,7.2))

def moving_bridge(z):
    """Reference silhouette: two end straps joined only over the servo."""
    bridge=box(FRONT_TAB_X+4-REAR_TAB_X,12.5,5,
               ((FRONT_TAB_X+4+REAR_TAB_X)/2,0,z+17.5))
    return bridge.union(horn_tab(z)).union(rear_tab(z))

def rear_bearing(z):
    block=(cq.Workplane('YZ',origin=(REAR_BEARING_X,0,0))
           .moveTo(-7,z-9).lineTo(7,z-9).lineTo(7,z+2)
           .threePointArc((0,z+9),(-7,z+2)).close().extrude(3.5))
    block=block.cut(hole_x(REAR_BEARING_X-.1,0,z,8.05,3.2))
    return block.cut(hole_x(REAR_BEARING_X+3,0,z,6.2,.7))

def bearing(z):
    return hole_x(REAR_BEARING_X,0,z,BEARING_OD,BEARING_W).cut(
        hole_x(REAR_BEARING_X-.1,0,z,BEARING_ID,BEARING_W+.2))

def pin(z):
    return hole_x(-27.0,0,z,3.0,12.0)

# Battery box remains centered. It is visibly a low plinth rather than part
# of the arm, matching the source's flat platform while housing our larger cell.
base=(cq.Workplane('XY').box(BASE_X,BASE_Y,BASE_T,
      centered=(True,True,False)).edges('|Z').fillet(1.5))
deck=(cq.Workplane('XY').box(BASE_X,27,DECK_T,
      centered=(True,True,False)).translate((0,0,DECK_Z)).edges('|Z').fillet(1.5))
base=base.union(deck)
for yy in (-12,12):
    base=base.union(box(68,3,10,(0,yy,8)))
base=base.union(box(2,21,10,(-33,0,8)))
for yy in (-12,12):
    base=base.cut(box(3.5,6,3.2,(32,yy,8)))

# Fixed front post holds the exposed lower servo by its two original ears.
base=base.union(box(5,5,J1_Z-19,(FLANGE_FRONT_X+AXIAL_SHIFT-3.2,8.5,(16+J1_Z-3)/2)))
base=base.union(servo_mount(J1_Z))
# Slender rear post carries only the outer ring of the extra bearing.
base=base.union(box(4,12,J1_Z-8-16,(REAR_BEARING_X+1.75,0,(16+J1_Z-8)/2)))
base=base.union(rear_bearing(J1_Z))
# Low side shelves carry the purchased board and Pololu switch.
for x in (-12,12):
    for y in (-24,24):
        base=base.cut(box(3.2,3,5,(x,y,1.5)))

# Lower moving U transitions through a narrow dogleg into the upper motor's
# fixed open mount. This creates the characteristic two perpendicular steps.
link=moving_bridge(J1_Z)
link=link.union(box(12.5,30,4,(0,-14,J1_Z+20)))
link=link.union(box(13.5,5,20,(0,-26,J1_Z+30)))
link=link.union(to_upper(servo_mount(0)))
link=link.union(to_upper(rear_bearing(0)))
# A single slim edge rail joins the fixed bearing to the opposite servo ear.
# It sits outside the servo's 12 mm case and leaves its broad faces exposed.
link=link.union(box(5,34,3,(-9,-8,J2_Z-17)))

# Upper moving bridge is the same construction rotated 90 degrees. Its long
# constant-section shaft starts at the bridge centre, as in arm2P.stl.
paddle=to_upper(moving_bridge(0))
paddle=paddle.union(box(12.5,12.5,TIP_Z-(J2_Z+20),
                       (0,0,(TIP_Z+J2_Z+20)/2)))

# Nominal horn visualization only. Do not print a 25T spline substitute.
horn=hole_x(14.2,0,0,9,2.3).union(box(2.3,5,21,(15.35,0,0)))
horn=horn.cut(hole_x(13.9,0,0,2.2,4))

parts={
    'base':(base,(.27,.47,.61)),
    'middle_link':(link,(.30,.53,.67)),
    'paddle':(paddle,(.34,.59,.72)),
    'servo_1_envelope':(servo().translate((AXIAL_SHIFT,0,J1_Z)),(.17,.19,.22)),
    'servo_2_envelope':(to_upper(servo().translate((AXIAL_SHIFT,0,0))),(.17,.19,.22)),
    'horn_1_envelope':(horn.translate((AXIAL_SHIFT,0,J1_Z)),(.87,.87,.82)),
    'horn_2_envelope':(to_upper(horn.translate((AXIAL_SHIFT,0,0))),(.87,.87,.82)),
    'bearing_1_envelope':(bearing(J1_Z),(.70,.74,.78)),
    'bearing_2_envelope':(to_upper(bearing(0)),(.70,.74,.78)),
    'pin_1_envelope':(pin(J1_Z),(.83,.83,.87)),
    'pin_2_envelope':(to_upper(pin(0)),(.83,.83,.87)),
    'battery_envelope':(box(59.5,19,7.5,(0,0,7.25)),(.67,.70,.73)),
    'controller_envelope':(box(21,17.8,4,(0,23,5)),(.15,.33,.40)),
    'switch_envelope':(box(15.24,15.24,3,(0,-23,4.5)),(.65,.21,.24)),
}
assembly=cq.Assembly(name='reference_layout_self_righting_robot')
summary={'status':'REFERENCE-LAYOUT PROVISIONAL: received servo, OEM horn, bearing and battery fit unverified',
         'units':'mm','servo_model':SERVO_MODEL,
         'reference':'https://github.com/homemadegarbage/SelfRisingRobot/tree/main/3Dmodel',
         'design':'open motor mounts, moving two-sided bridges, stepped middle link, long straight upper pole',
         'base_footprint_mm':[BASE_X,BASE_Y], 'joint_origins_mm':[[0,0,J1_Z],[0,0,J2_Z]],
         'axes_upright':[[1,0,0],[0,1,0]],'tip_z_mm':TIP_Z,
         'servo_axial_shift_mm':AXIAL_SHIFT,'horn_face_x_mm':HORN_FACE,
         'rear_bearing_x_mm':REAR_BEARING_X,'parts':{}}
for name,(shape,color) in parts.items():
    solid=shape.val()
    assert solid.isValid(),f'Invalid CAD: {name}'
    if name in ('base','middle_link','paddle'):
        assert len(shape.solids().vals())==1,f'Disconnected print: {name}: {[(s.BoundingBox().xmin,s.BoundingBox().xmax,s.BoundingBox().ymin,s.BoundingBox().ymax,s.BoundingBox().zmin,s.BoundingBox().zmax) for s in shape.solids().vals()]}'
        cq.exporters.export(shape,str(OUT/f'{name}.step'))
        cq.exporters.export(shape,str(OUT/f'{name}.stl'),tolerance=.05,angularTolerance=.15)
    assembly.add(shape,name=name,color=cq.Color(*color))
    verts,triangles=solid.tessellate(.3)
    summary['parts'][name]={'volume_mm3':solid.Volume(),'color':color,
                             'vertices':[[v.x,v.y,v.z] for v in verts], 'triangles':triangles}

fit_coupons={
    'servo_mount_fit_coupon':servo_mount(0),
    'horn_fit_coupon':horn_tab(0),
    'pivot_fit_coupon':rear_bearing(0).union(box(8,4,4,(-20,0,-7))),
    'battery_tunnel_fit_coupon':box(22,30,3,(0,0,1.5)).union(
        box(22,30,3,(0,0,14.5))).union(box(22,3,10,(0,-12,8))).union(box(22,3,10,(0,12,8)))
}
for name,shape in fit_coupons.items():
    assert shape.val().isValid() and len(shape.solids().vals())==1,name
    cq.exporters.export(shape,str(OUT/f'{name}.step'))
    cq.exporters.export(shape,str(OUT/f'{name}.stl'),tolerance=.05,angularTolerance=.15)
summary['fit_coupons']=list(fit_coupons)
assembly.save(str(OUT/'assembly.step'))
(OUT/'geometry.json').write_text(json.dumps(summary))
clashes=[]
names=list(parts)
for i,n in enumerate(names):
    for m in names[i+1:]:
        volume=parts[n][0].intersect(parts[m][0]).val().Volume()
        if volume>.1: clashes.append({'parts':[n,m],'overlap_mm3':round(volume,2)})
(OUT/'nominal_clashes.json').write_text(json.dumps(clashes,indent=2))
print(json.dumps({'printed_volumes_mm3':{n:round(parts[n][0].val().Volume(),1) for n in ('base','middle_link','paddle')},'nominal_overlaps':clashes},indent=2))
