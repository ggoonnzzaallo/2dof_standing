"""Review concept: under-base electronics pod for the final Onshape robot.

All coordinates are the existing assembly frame, in mm. No firmware/model changes.
Header, connector, switch access and wire envelopes need physical fit checks.
"""
from pathlib import Path
import hashlib
import json
import math
import shutil
import sys

print('Loading CAD kernel...', flush=True)
import cadquery as cq
import numpy as np
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TopLoc import TopLoc_Location
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / 'cad/onshape_import'))
from import_assembly import name

SOURCE = ROOT / 'cad/onshape_import/source/robot_onshape_third.step'
POLOLU_SOURCE = OUT / 'source/pololu_2810.step'
P = dict(revision='Rev C3 USB and battery fit revision', width=70., corner_radius=5., ground_edge_radius=1., wall=1.2,
         roof_z=0., floor_z=-10.4, floor_thickness=1.6, lid_plate_thickness=2.,
         mount_centers=[[-29.5, -29.5], [29.5, 29.5]], m2_clearance=2.4,
         m2_pilot=2.0, m2_blind_depth=8.6, boss_diameter=7.6,
         locating_tab_height=.8, board_pad_height=.6, psa_allowance=.4,
         battery_size=[59.5, 19., 7.5], battery_center=[-3.65, 21.3, -6.15], battery_clearance=.3,
         board_translation=[-.84944, 8.01904, -11.4], headers_removed=True,
         usb_window_size=[8., 9.8, 4.1], usb_window_center=[-34., -15.50733, -6.545], usb_window_corner_radius=.6,
         pololu_translation=[16., -34.7, -9.4],
         switch_window_size=[10., 6., 2.6], switch_window_center=[23.62, -34.3, -7.734],
         pololu_edge_pocket_size=[16.2, 6., 1.4], pololu_edge_pocket_center=[23.62, -34.3, -8.892])


def box(size, center):
    return cq.Workplane('XY').box(*size).translate(center)


def rounded_xy(w, d, h, z, r):
    return cq.Workplane('XY').box(w, d, h, centered=(True, True, False)).edges('|Z').fillet(r).translate((0, 0, z))


def cylinder(x, y, z, diameter, height):
    return cq.Workplane('XY', origin=(x, y, z)).circle(diameter / 2).extrude(height)


def read_shapes():
    """Read only: never rewrite the authoritative imported-review artifacts."""
    doc = TDocStd_Document(TCollection_ExtendedString('pod'))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.ReadFile(str(SOURCE))
    if not reader.Transfer(doc):
        raise RuntimeError('STEP transfer failed')
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    roots = TDF_LabelSequence()
    tool.GetFreeShapes(roots)
    records = json.loads((ROOT / 'cad/onshape_import/assembly_inspection.json').read_text())['parts']
    result = {}

    def walk(label, world):
        if tool.IsReference_s(label):
            ref = TDF_Label()
            tool.GetReferredShape_s(label, ref)
            world = world.Multiplied(tool.GetLocation_s(label))
            label = ref
        children = TDF_LabelSequence()
        if tool.IsAssembly_s(label):
            tool.GetComponents_s(label, children)
            for i in range(1, children.Length() + 1):
                walk(children.Value(i), world)
            return
        shape = tool.GetShape_s(label).Moved(world)
        bounds = Bnd_Box()
        BRepBndLib.AddOptimal_s(shape, bounds, False, False)
        matches = [r for r in records if r['name'] == name(label) and
                   np.max(np.abs(np.array(r['bbox_mm']) - bounds.Get())) < .001]
        if len(matches) != 1:
            raise RuntimeError('Ambiguous imported instance: ' + name(label))
        result[matches[0]['alias']] = cq.Shape.cast(shape)

    for i in range(1, roots.Length() + 1):
        walk(roots.Value(i), TopLoc_Location())
    assert len(result) == 9
    return result


def mesh(shape):
    vertices, triangles = shape.tessellate(.16, .3)
    return {'vertices': [[round(p.x, 5), round(p.y, 5), round(p.z, 5)] for p in vertices],
            'triangles': [list(t) for t in triangles]}


def main():
    OUT.mkdir(exist_ok=True)
    print('Reading authoritative Onshape assembly...', flush=True)
    source = read_shapes()
    hole_records=json.loads((ROOT/'cad/onshape_import/assembly_inspection.json').read_text())['parts']
    bracket=next(p for p in hole_records if p['alias']=='top_link_servo_horn_bracket')
    baseline_diameters={round(2*r[0],5) for r in bracket['cylinders_radius_origin_axis_mm'] if .8<=r[0]<=1.2}
    assert baseline_diameters=={P['m2_pilot']}, ('Existing proven screw bore',baseline_diameters)

    roof, floor, wall = P['roof_z'], P['floor_z'], P['wall']
    bottom = floor-P['floor_thickness']
    mounts = [tuple(v) for v in P['mount_centers']]
    print('Building lower cup, PSA lands and two blind screw bosses...', flush=True)
    outer = rounded_xy(70, 70, roof-bottom, bottom, 5).edges('<Z').fillet(P['ground_edge_radius'])
    cup = outer.cut(rounded_xy(70-2*wall, 70-2*wall, roof-floor+1, floor, 5-wall))
    battery_keepout=box((P['battery_size'][0]+2*P['battery_clearance'],
                         P['battery_size'][1]+2*P['battery_clearance'],roof-floor+2),
                        (*P['battery_center'][:2],(roof+floor)/2))
    boss_relief=[]
    for x, y in mounts:
        boss=cylinder(x, y, floor, P['boss_diameter'], roof-floor)
        if x>0:
            removed=boss.val().intersect(battery_keepout.val()).Volume()
            boss=boss.cut(battery_keepout)
            boss_relief.append({'center_mm':[x,y], 'removed_volume_mm3':removed,
                'minimum_pilot_wall_mm':x-(P['battery_center'][0]+P['battery_size'][0]/2+P['battery_clearance'])-P['m2_pilot']/2})
            assert boss_relief[-1]['minimum_pilot_wall_mm']>=2., 'Retain screw boss wall'
        cup = cup.union(boss)
        # Small webs connect each boss to its two adjacent walls.
        sx, sy = (1 if x>0 else -1), (1 if y>0 else -1)
        cup = cup.union(box((5.5, 1.2, roof-floor), (sx*32.25, y, (roof+floor)/2)))
        cup = cup.union(box((1.2, 5.5, roof-floor), (x, sy*32.25, (roof+floor)/2)))
    usb_cut=box(P['usb_window_size'],P['usb_window_center']).edges('|X').fillet(P['usb_window_corner_radius'])
    cup = cup.cut(usb_cut)
    cup = cup.cut(box(P['switch_window_size'], P['switch_window_center']))
    cup = cup.cut(box(P['pololu_edge_pocket_size'], P['pololu_edge_pocket_center']))
    # Move the battery rearward and left. The existing left side wall replaces
    # the left end stop; do not squeeze the pouch against the rounded corner.
    bx,by,_=P['battery_center'];gap=P['battery_clearance']
    right_stop=bx+P['battery_size'][0]/2+gap+.7
    front_stop=by-P['battery_size'][1]/2-gap-.7
    rear_face=by+P['battery_size'][1]/2+gap
    cup=cup.union(box((1.4,15.,3.),(right_stop,by,floor+1.5)))
    cup=cup.union(box((42.,1.4,3.),(bx,front_stop,floor+1.5)))
    # Rear rail is integrated into the rear wall instead of floating inboard.
    rear_end=35-wall+.2
    cup=cup.union(box((42.,rear_end-rear_face,3.),(bx,(rear_face+rear_end)/2,floor+1.5)))
    # Broad, low PSA lands replace narrow/tall standoffs. Open space between
    # them provides a relief route for underside BAT solder and direct wires.
    for x in (-30.2, -14.2):
        cup = cup.union(box((4., 8., .6), (x, -15.5, floor+.3)))
    # XIAO stops engage the bottom of the PCB edge; short tabs avoid blocking
    # the long castellated pad rows, USB socket and top-side solder routing.
    xiao_stops=[]
    for x in (-31.6, -12.6):
        for y in (-25.14, -5.86):
            xiao_stops.append(box((2., .9, 1.8), (x, y, floor+.9)).val())
    xiao_stops.append(box((.9, 8., 1.8), (-10.96802, -15.5, floor+.9)).val())
    for y in (-22.4, -8.6):
        xiao_stops.append(box((.9, 2., 1.8), (-33.46802, y, floor+.9)).val())
    for shape in xiao_stops:
        cup=cup.union(cq.Workplane(obj=shape))
    # One Pololu moved to the opposite front corner; solder leads from above.
    for y in (-31.2, -23.2):
        cup = cup.union(box((12., 3., .6), (23.62, y, floor+.3)))
    for x in (15.15, 32.09):
        cup = cup.union(box((1.1, 6., 1.8), (x, -26.5, floor+.9)))
    cup = cup.union(box((12., 1.2, 1.8), (23.62, -18.56, floor+.9)))
    # Clip webs at the rounded exterior; leave the central bay unobstructed.
    cup=cup.intersect(outer)
    tab_records=[]
    for x,y,sx,sy in [(0.,-34.4,3.6,.8),(34.4,0.,.8,3.6),
                      (0.,34.4,3.6,.8),(-34.4,0.,.8,3.6)]:
        cup=cup.union(box((sx,sy,.8),(x,y,.4)))
        tab_records.append((x,y,sx,sy))
    for x,y in mounts:
        cup=cup.cut(cylinder(x,y,-P['m2_blind_depth'],P['m2_pilot'],P['m2_blind_depth']+.2))
        lead=cq.Solid.makeCone(P['m2_pilot']/2,1.1,.4,cq.Vector(x,y,-.4))
        cup=cup.cut(cq.Workplane(obj=lead))
    print('Thinning the original plate and retaining the servo frame...', flush=True)
    # Keep the original top face and servo frame at their exact Z coordinates.
    # A flat underside at Z=0 makes the lighter lid straightforward to print.
    base=cq.Workplane(obj=source['base']).cut(box((80.,80.,4.),(0.,0.,-2.)))
    thinning_removed=source['base'].Volume()-base.val().Volume()
    assert base.val().BoundingBox().zmin > -1e-5
    # Four short top-side gussets stiffen the plate at the frame's side walls,
    # outside the lower servo's +/-5.95 mm Y envelope. No hanging bottom ribs.
    original_frame=source['base'].intersect(box((100.,100.,50.),(0.,0.,27.01)).val())
    gussets=[]
    gusset_checks=[]
    for x in (-5.,6.5):
        for sign in (-1.,1.):
            rib=(cq.Workplane('YZ',origin=(x,0,0))
                 .polyline([(sign*6.5,2.),(sign*18.,2.),(sign*6.5,5.)])
                 .close().extrude(1.2).val())
            # Test attachment above the plate: a shared lid alone does not
            # establish that a gusset actually reaches the servo frame.
            contact=rib.intersect(original_frame).Volume()
            assert contact>1., ('Disconnected frame gusset',x,sign,contact)
            gusset_checks.append({'x_mm':x,'side':sign,'frame_overlap_mm3':contact})
            gussets.append(rib);base=base.union(cq.Workplane(obj=rib))
    gusset_shape=cq.Compound.makeCompound(gussets)
    for x,y in mounts:
        base=base.cut(cylinder(x,y,-.1,P['m2_clearance'],2.3))
    for x,y,sx,sy in tab_records:
        base=base.cut(box((sx+.5,sy+.5,1.),(x,y,.5)))
    base=base.cut(rounded_xy(12.,10.,4.,-.1,2.).translate((15.,-14.,0)))
    assert original_frame.cut(base.val()).Volume()<1e-4, 'Original servo frame must remain intact'
    for rib,check in zip(gussets,gusset_checks):
        removed=rib.cut(base.val()).Volume()
        assert removed<1e-4, ('Lid cut truncates gusset',check,removed)
        check['removed_by_lid_cuts_mm3']=removed
    # Relocate existing hardware, preserving the XIAO's orientation.
    battery_old=np.array([-.21532,20.71208,5.75])
    battery=source['battery'].translate(tuple(np.array(P['battery_center'])-battery_old))
    board=source['controller_board'].translate(tuple(P['board_translation']))
    pololu_original=cq.importers.importStep(str(POLOLU_SOURCE)).val()
    assert pololu_original.isValid() and len(pololu_original.Solids())==1
    pololu=pololu_original.translate(tuple(P['pololu_translation']))
    # Existing connector pairs laid flat; envelopes still need wired fit checking.
    connectors=cq.Compound.makeCompound([
        box((13.,7.,6.),(10.,-4.5,-6.3)).val(),
        box((9.,12.,5.),(0.,-21.,-6.4)).val(),
        box((9.,12.,5.),(10.,-21.,-6.4)).val(),
    ])
    pieces={
        'base_modified':(base.val(),'original',[.29,.53,.67]),
        'electronics_cup':(cup.val(),'cup',[.25,.49,.54]),
        'battery':(battery,'electronics',[.83,.68,.31]),
        'controller_board':(board,'electronics',[.21,.42,.31]),
        'pololu_2810_master_switch':(pololu,'electronics',[.22,.52,.29]),
        'existing_connectors_envelope':(connectors,'electronics',[.63,.29,.26]),
    }
    for alias,shape in source.items():
        if alias not in ('base','battery','controller_board'):
            pieces[alias]=(shape,'arm',[.64,.66,.69])
    # Source board BRep is invalid; keep a conservative, vertex-checked envelope.
    board_envelope=box((21.,17.78,4.46),(-22.21802,-15.5,-7.17))
    board_envelope=board_envelope.union(box((3.,9.1,3.21),(-32.7,-15.50733,-6.545))).val()
    vertices=np.array(json.loads((ROOT/'cad/onshape_import/geometry.json').read_text())['parts']['controller_board']['vertices'])
    vertices+=np.array(P['board_translation'])
    in_pcb=np.all(np.abs(vertices-np.array([-22.21802,-15.5,-7.17]))<=np.array([10.5,8.89,2.23])+.002,axis=1)
    in_usb=np.all(np.abs(vertices-np.array([-32.7,-15.50733,-6.545]))<=np.array([1.5,4.55,1.605])+.002,axis=1)
    assert np.all(in_pcb|in_usb), 'Envelope must contain source board vertices'
    overlaps={}
    checks=[('cup',cup.val()),('lid',base.val()),('battery',battery),
            ('xiao_envelope',board_envelope),('pololu',pololu),('connectors',connectors)]
    for i,(a,sa) in enumerate(checks):
        for b,sb in checks[i+1:]:
            volume=sa.intersect(sb).Volume();overlaps[a+' / '+b]=volume
            assert volume<1e-4,(a,b,volume)
    for i,a in enumerate(connectors.Solids()):
        for b in connectors.Solids()[i+1:]:
            assert a.intersect(b).Volume()<1e-4
    for alias,shape in source.items():
        if alias not in ('base','battery','controller_board'):
            volume=gusset_shape.intersect(shape).Volume()
            overlaps['new_lid_gussets / '+alias]=volume
            assert volume<1e-4,('gusset / '+alias,volume)
    # New window must clear both model actuator and extra lateral travel allowance.
    lever=pololu_original.intersect(box((6.,2.,2.),(7.62,-1.,1.8)).val())
    assert lever.Volume()>.1
    for dx in (-2.,2.):
        pose=lever.translate(tuple(np.array(P['pololu_translation'])+[dx,0.,0.]))
        assert pose.intersect(cup.val()).Volume()<1e-4,('slider access',dx)
    # Independently verify a full-height collar still surrounds the screw bore,
    # including the larger entry lead-in, after the battery-side relief.
    collar=cylinder(29.5,29.5,-P['m2_blind_depth'],6.0,P['m2_blind_depth'])
    collar=collar.cut(cylinder(29.5,29.5,-P['m2_blind_depth']-.1,2.2,P['m2_blind_depth']+.2)).val()
    assert collar.cut(cup.val()).Volume()<1e-4, 'Battery relief compromises screw collar'
    # A 0.3 mm rounded footprint envelope clears the curved enclosure corner.
    battery_clearance=box((P['battery_size'][0],P['battery_size'][1],7.5),P['battery_center']).edges('|Z').fillet(.01)
    for dx,dy in ((-.25,0),(.25,0),(0,-.25),(0,.25)):
        assert battery_clearance.translate((dx,dy,0)).val().intersect(cup.val()).Volume()<1e-4, ('Battery allowance',dx,dy)
    assembly=cq.Assembly(name='under_base_pod_C3_review')
    geometry={'units':'mm','parameters':P,'parts':{}}
    for alias,(shape,group,color) in pieces.items():
        assembly.add(shape,name=alias,color=cq.Color(*color))
        geometry['parts'][alias]=dict(name=alias.replace('_',' '),group=group,color=color,**mesh(shape))
    assert sum(n.startswith('pololu_2810') for n in pieces)==1
    print('Exporting revised cup, thin lid and review...',flush=True)
    assembly.save(str(OUT/'assembly_review.step'))
    # Keep the obvious top-level download synchronized with the full current robot.
    shutil.copyfile(OUT/'assembly_review.step', ROOT/'cad/assembly.step')
    printable={'electronics_cup':cup.val(),'base_modified':base.val()}
    print_checks={}
    for alias,shape in printable.items():
        assert shape.isValid() and len(shape.Solids())==1,alias
        cq.exporters.export(shape,str(OUT/(alias+'.step')))
        bb=Bnd_Box();BRepBndLib.AddOptimal_s(shape.wrapped,bb,False,False)
        cq.exporters.export(shape.translate((0,0,-bb.Get()[2])),str(OUT/(alias+'.stl')),tolerance=.08,angularTolerance=.2)
        print_checks[alias]={'valid_brep':True,'solids':1,'volume_mm3':shape.Volume(),
                             'solid_reference_PLA_g_at_1_32':shape.Volume()*.00132,
                             'cad_bounds_mm':list(bb.Get())}
    reference=json.loads((OUT/'fit_revision_1_reference.json').read_text())
    before=sum(reference['printed_parts'][n]['volume_mm3'] for n in ('electronics_cup','base_modified'))
    after=sum(print_checks[n]['volume_mm3'] for n in ('electronics_cup','base_modified'))
    report={'status':'Rev C3 cup-only revision; C2 lid retained; new USB/battery fit pending',
            'date':'2026-11-03','parameters':P,'pololu_count':1,'headers_removed_confirmed_by_user':True,
            'fastener_confirmed_by_user':'M2 x 10 mm, reuse proven printed-model screw fit, no nuts, no coupon',
            'fastener_bore_baseline':{'source_part':'top_link_servo_horn_bracket','diameter_mm':P['m2_pilot'],'source':'cad/onshape_import/assembly_inspection.json'},
            'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'pololu_source_sha256':hashlib.sha256(POLOLU_SOURCE.read_bytes()).hexdigest(),
            'printed_parts':print_checks,'rigid_overlap_volume_mm3':overlaps,
            'mounting_hardware':'TWO M2x10 screws; 2.0 mm blind holes copied from proven model screw-bore diameter, 8.6 mm deep. No nuts.',
            'cup_body_depth_mm':12.,'cup_with_register_tabs_height_mm':12.8,
            'closed_electronics_package_height_mm':14.,'previous_closed_package_height_mm':24.,
            'new_ground_z_mm':-12.,'new_overall_height_mm':163.,
            'psa_mounting':'0.6 mm broad lands + nominal 0.4 mm insulating PSA; open underside lead relief between lands',
            'xiao_locating_clearance_each_side_mm':.3,'slider_extra_lateral_allowance_mm':2.,
            'slider_protrusion_mm':.595,'original_servo_frame_preserved':True,
            'gusset_frame_connections':gusset_checks,
            'usb_opening_mm':[9.8,4.1], 'usb_previous_opening_mm':[14.,7.],
            'usb_shell_face_bounds_mm':[-19.97733,-11.03733,-8.15,-4.94],
            'usb_shell_nominal_clearance_each_side_mm':[.43,.445],
            'battery_shift_from_C2_mm':[-3.65,7.3,0.],
            'battery_left_wall_gap_mm':.4,
            'battery_locating':'Left cup wall is the end stop; relocated right/front stops; rear rail joins rear wall',
            'battery_side_boss_relief':boss_relief,
            'retained_screw_collar_outer_diameter_mm':6.,
            'C2_lid_compatible':True,
            'ground_contact_edge':'R1 mm fillet around outside bottom perimeter; central bottom remains flat',
            'base_plate_thinning_removed_volume_mm3':thinning_removed,
            'comparison_to_first_fit':{'cup_and_lid_before_mm3':before,'cup_and_lid_after_mm3':after,
                'solid_volume_reduction_percent':100*(1-after/before)},
            'unverified':['Wired header-free XIAO, underside BAT solder and PSA seating',
                'Real slider travel and smaller window','Two-screw enclosure retention in the new geometry',
                'Lid stiffness and retention in falls; no structural load test or FEA',
                'Actual connector/wire bends in the lower package','USB cable fit and print tolerance',
                'Changed mass/inertia, floor contacts and IMU height in recovery'],
            'note':'Only mechanical packaging revised; source Onshape, firmware, wiring and training are unchanged.'}
    (OUT/'geometry.json').write_text(json.dumps(geometry,separators=(',',':'))+'\n')
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(print_checks,indent=2))
    print(json.dumps(report['comparison_to_first_fit'],indent=2))
    print('PASS: valid single solids, hardware/connector/lid fit envelopes, neutral gusset clearance, slider access allowance.')


if __name__=='__main__':
    main()
