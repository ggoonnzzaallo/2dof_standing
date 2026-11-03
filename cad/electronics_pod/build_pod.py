"""Review concept: under-base electronics pod for the final Onshape robot.

All coordinates are the existing assembly frame, in mm. No firmware/model changes.
Header, connector, switch access and wire envelopes need physical fit checks.
"""
from pathlib import Path
import hashlib
import json
import math
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
P = dict(width=70., corner_radius=5., wall=1.8, roof_z=-2., floor_z=-20.,
         floor_thickness=2., mount_pitch=59., m2_clearance=2.4,
         battery_size=[59.5, 19., 7.5], battery_center=[0., 14., -15.65],
         board_translation=[-.84944, 8.01904, -19.5],
         header_bar_size=[17.8, 2.5, 2.5], header_pin_length=6.2,
         usb_window_size=[8., 14., 8.], usb_window_center=[-34., -15.5, -14.645],
         pololu_translation=[-7., -34.7, -17.],
         switch_window_size=[10., 6., 6.], switch_window_center=[.62, -34.3, -15.25],
         pololu_edge_pocket_size=[16.2, 6., 1.6], pololu_edge_pocket_center=[.62, -34.3, -16.49])


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
    print('Building one-piece cup with integral floor...', flush=True)
    roof, floor, wall = P['roof_z'], P['floor_z'], P['wall']
    mounts = [(x, y) for x in (-29.5, 29.5) for y in (-29.5, 29.5)]
    shell = rounded_xy(70, 70, roof - floor, floor, 5)
    shell = shell.cut(rounded_xy(70 - 2*wall, 70 - 2*wall, roof-floor+2, floor-1, 5-wall))
    for x, y in mounts:
        shell = shell.union(cylinder(x, y, floor, 9.6, roof-floor))
        shell = shell.cut(cylinder(x, y, floor-1, P['m2_clearance'], roof-floor+2))
        # One side-loaded M2 nut per corner; the existing base is the lid.
        for z in (-6.6,):
            pocket = cq.Workplane('XY', origin=(x, y, z)).polygon(6, 4.95).extrude(2.)
            sign = -1 if x > 0 else 1
            pocket = pocket.union(box((7., 4.3, 2.), (x + sign*3.5, y, z+1)))
            shell = shell.cut(pocket)

    shell = shell.cut(box(P['usb_window_size'], P['usb_window_center']))
    # Close the former connector-access notch. Only the existing slider is
    # exposed; connector servicing is by lifting the original base off the cup.
    shell = shell.cut(box(P['switch_window_size'], P['switch_window_center']))
    shell = shell.cut(box(P['pololu_edge_pocket_size'], P['pololu_edge_pocket_center']))

    lid = rounded_xy(70, 70, P['floor_thickness'], floor-P['floor_thickness'], 5)
    # Smooth, low battery stops: clearance rather than a compression clamp.
    for x in (-31.45, 31.45):
        lid = lid.union(box((1.4, 15., 4.), (x, 14., floor+2)))
    for y in (2.8, 25.2):
        lid = lid.union(box((42., 1.4, 4.), (0., y, floor+2)))
    # Board support pads lie between header rows. Retention uses thin insulating
    # foam tape; installed backside components and solder must be checked first.
    for x in (-30.2, -13.7):
        lid = lid.union(box((1.6, 8., 2.3), (x, -15.5, floor+1.15)))
    # One Pololu 2810 only: PCB horizontal, components up, slider toward -Y.
    # Two insulated support rails leave 3 mm below the PCB for solder/lead bends.
    # Thin foam tape fills the 0.4 mm rail-to-PCB gap; no screws through pads.
    for y in (-31.2, -23.2):
        lid = lid.union(box((12., 1.4, 2.6), (.62, y, floor+1.3)))
    for x in (-7.85, 9.09):
        lid = lid.union(box((1.1, 6., 4.5), (x, -25., floor+2.25)))
    lid = lid.union(box((12., 1.2, 4.5), (.62, -18.56, floor+2.25)))
    # Two wire-lacing rails keep the harness in its bay, clear of the battery.
    for x in (4., 21.):
        rail = box((2., 12., 3.5), (x, -13., floor+1.75))
        rail = rail.cut(box((4., 6., 1.6), (x, -13., floor+1.8)))
        lid = lid.union(rail)
    cup = shell.union(lid)

    base = cq.Workplane(obj=source['base'])
    for x, y in mounts:
        base = base.cut(cylinder(x, y, -3, P['m2_clearance'], 6))
    slot = rounded_xy(12., 10., 6., -3., 2.).translate((15., -14., 0))
    base = base.cut(slot)
    expected_removed = (4*math.pi*1.2**2 + 12*10 - (4-math.pi)*2**2)*4
    removed = source['base'].Volume() - base.val().Volume()
    assert abs(removed-expected_removed) < .1, ('mount/cable cuts must affect only 4 mm plate', removed, expected_removed)
    battery_old = np.array([-0.21532, 20.71208, 5.75])
    battery_delta = np.array(P['battery_center']) - battery_old
    battery = source['battery'].translate(tuple(battery_delta))
    board = source['controller_board'].translate(tuple(P['board_translation']))
    pololu_original = cq.importers.importStep(str(POLOLU_SOURCE)).val()
    assert pololu_original.isValid() and len(pololu_original.Solids()) == 1
    pololu = pololu_original.translate(tuple(P['pololu_translation']))
    # Header representation is a measured-fit placeholder, pins UP as confirmed.
    headers = []
    for y in (-23.12, -7.88):
        headers.append(box(P['header_bar_size'], (-22.2, y, -15.)).val())
        for x in np.linspace(-29.82, -14.58, 7):
            headers.append(box((.65, .65, 6.2), (float(x), y, -10.65)).val())
    header_shape = cq.Compound.makeCompound(headers)
    # Existing connectors stay inside, away from the one exposed switch.
    connectors = cq.Compound.makeCompound([
        box((13., 7., 6.), (18., -5., -13.5)).val(),  # Existing battery RCY pair.
        box((9., 5., 9.), (17., -16., -12.)).val(),
        box((9., 5., 9.), (27., -16., -12.)).val(),
    ])

    pieces = {
        'base_modified': (base.val(), 'original', [0.29, .53, .67]),
        'electronics_cup': (cup.val(), 'cup', [.25, .49, .54]),
        'battery': (battery, 'electronics', [.83, .68, .31]),
        'controller_board': (board, 'electronics', [.21, .42, .31]),
        'headers_pins_up': (header_shape, 'electronics', [.23, .25, .27]),
        'pololu_2810_master_switch': (pololu, 'electronics', [.22, .52, .29]),
        'existing_connectors_envelope': (connectors, 'electronics', [.63, .29, .26]),
    }
    for alias, shape in source.items():
        if alias not in ('base', 'battery', 'controller_board'):
            pieces[alias] = (shape, 'arm', [.64, .66, .69])

    assembly = cq.Assembly(name='under_base_pod_review')
    geometry = {'units': 'mm', 'parameters': P, 'parts': {}}
    for alias, (shape, group, color) in pieces.items():
        assembly.add(shape, name=alias, color=cq.Color(*color))
        geometry['parts'][alias] = dict(name=alias.replace('_', ' '), group=group, color=color, **mesh(shape))
    print('Exporting STEP assembly and printable parts...', flush=True)
    assembly.save(str(OUT/'assembly_review.step'))
    printable = {'electronics_cup': cup.val(), 'base_modified': base.val()}
    checks = {}
    for alias, shape in printable.items():
        cq.exporters.export(shape, str(OUT/(alias+'.step')))
        exact_bounds = Bnd_Box()
        BRepBndLib.AddOptimal_s(shape.wrapped, exact_bounds, False, False)
        print_shape = shape.translate((0, 0, -exact_bounds.Get()[2]))
        cq.exporters.export(print_shape, str(OUT/(alias+'.stl')), tolerance=.08, angularTolerance=.2)
        checks[alias] = {'valid_brep': shape.isValid(), 'solids': len(shape.Solids()), 'volume_mm3': shape.Volume(),
                         'solid_reference_PLA_g_at_1_32': shape.Volume() * .00132}
        assert shape.isValid() and len(shape.Solids()) == 1, alias
    # Real solid overlap checks for the new housing, existing base and battery.
    pairs = [('electronics_cup', 'base_modified'), ('electronics_cup', 'battery')]
    overlaps = {}
    for a, b in pairs:
        volume = pieces[a][0].intersect(pieces[b][0]).Volume()
        overlaps[a+' / '+b] = volume
        assert volume < 1e-4, (a, b, volume)
    # Detailed board is invalid in source; validate a conservative CAD envelope
    # separately, rather than claiming valid BRep clearance for that component.
    # PCB is 21 mm long; only the narrower USB socket overhangs into its window.
    board_envelope = box((21., 17.78, 4.46), (-22.21802, -15.5, -15.27))
    board_envelope = board_envelope.union(box((3., 9.1, 4.46), (-32.7, -15.5, -15.27))).val()
    vertices = np.array(json.loads((ROOT/'cad/onshape_import/geometry.json').read_text())['parts']['controller_board']['vertices'])
    vertices += np.array(P['board_translation'])
    in_pcb = np.all(np.abs(vertices-np.array([-22.21802,-15.5,-15.27])) <= np.array([10.5,8.89,2.23])+.002, axis=1)
    in_usb = np.all(np.abs(vertices-np.array([-32.7,-15.5,-15.27])) <= np.array([1.5,4.55,2.23])+.002, axis=1)
    assert np.all(in_pcb|in_usb), 'Envelope must contain every imported board mesh vertex'
    for alias in ('electronics_cup', 'battery', 'base_modified'):
        volume = board_envelope.intersect(pieces[alias][0]).Volume()
        overlaps[alias+' / board_CAD_envelope'] = volume
        assert volume < 1e-4, (alias, volume)
    for alias in ('electronics_cup', 'battery', 'base_modified'):
        volume = header_shape.intersect(pieces[alias][0]).Volume()
        overlaps[alias+' / provisional_headers'] = volume
        assert volume < 1e-4, (alias, volume)
    for alias in ('electronics_cup', 'battery', 'base_modified'):
        volume = connectors.intersect(pieces[alias][0]).Volume()
        overlaps[alias+' / provisional_connectors'] = volume
        assert volume < 1e-4, (alias, volume)
    assert board_envelope.intersect(connectors).Volume() < 1e-4
    for i, a in enumerate(connectors.Solids()):
        for b in connectors.Solids()[i+1:]:
            assert a.intersect(b).Volume() < 1e-4
    for alias, shape in [('electronics_cup', cup.val()), ('base_modified', base.val()),
                         ('battery', battery), ('controller_envelope', board_envelope),
                         ('headers', header_shape), ('connectors', connectors)]:
        volume = pololu.intersect(shape).Volume()
        overlaps['pololu_2810 / '+alias] = volume
        assert volume < 1e-4, ('pololu_2810', alias, volume)
    switch_bounds = Bnd_Box()
    BRepBndLib.AddOptimal_s(pololu.wrapped, switch_bounds, False, False)
    assert sum(alias.startswith('pololu_2810') for alias in pieces) == 1
    # The supplier STEP depicts one slider position. Check an extra +/-2 mm
    # lateral allowance on its externally projecting lever, not the entire PCB.
    lever = pololu_original.intersect(box((6., 2., 2.), (7.62, -1., 1.8)).val())
    assert lever.Volume() > .1
    for dx in (-2., 2.):
        pose = lever.translate(tuple(np.array(P['pololu_translation']) + [dx, 0., 0.]))
        assert pose.intersect(cup.val()).Volume() < 1e-4, ('slider opening allowance', dx)
    report = {'status': 'CAD review concept; not physical-fit or recovery validated', 'parameters': P,
              'base_confirmed_unchanged_by_user': True, 'header_direction_confirmed_by_user': 'long pins on USB/component side, upward',
              'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'pololu_source_sha256': hashlib.sha256(POLOLU_SOURCE.read_bytes()).hexdigest(),
              'pololu_count': 1, 'pololu_bounds_mm': list(switch_bounds.Get()),
              'pololu_retention': 'Insulated foam tape on two rails; side/rear locating stops, no pad screws.',
              'slider_protrusion_beyond_front_mm': -35.-switch_bounds.Get()[1],
              'slider_access_extra_lateral_allowance_mm': 2.,
              'printed_parts': checks, 'rigid_overlap_volume_mm3': overlaps,
              'construction': 'One printed cup with integral floor; no service panel or connector window. One Pololu slider window. Existing base is the lid.',
              'mounting_hardware': 'Four M2x10 screws and four M2 nuts; no bottom-cover fasteners.',
              'added_height_mm': 20., 'new_ground_z_mm': -22., 'new_overall_height_mm': 173.,
              'board_rotation_changed': False,
              'existing_base_removed_volume_mm3': removed,
              'unverified': ['Actual header/wire stack and backside solder clearance', 'USB cable overmold and reset access',
                             'Connector sizes and installed wire bend/strain-relief clearance', 'Screw/nut fit',
                             'Pololu slider full travel/fingernail access and underside solder clearance',
                             'Changed contact geometry, mass/inertia and recovery behavior'],
              'note': 'Rev C packaging proposal; source Onshape geometry and simulator unchanged. Wiring and firmware require separate installation/verification.'}
    (OUT/'geometry.json').write_text(json.dumps(geometry, separators=(',', ':'))+'\n')
    (OUT/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(checks, indent=2))
    print('PASS: printable BReps, single-solid exports, selected rigid overlaps and provisional header clearance.')


if __name__ == '__main__':
    main()
