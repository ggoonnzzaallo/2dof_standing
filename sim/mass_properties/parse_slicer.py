"""Read the supplied Bambu sliced 3MF as data; never execute printer commands.

Attribute deposited filament using start/stop object labels, not OBJECT_ID,
which changes before the preceding object's wipe/retraction has finished.
Retractions and their subsequent recovery are not new deposited material.
"""
from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
MODEL_FEATURES = {
    'Inner wall', 'Outer wall', 'Overhang wall', 'Bottom surface',
    'Top surface', 'Internal solid infill', 'Sparse infill',
    'Floating vertical shell', 'Bridge', 'Gap infill',
}
REMOVABLE_FEATURES = {'Support', 'Support interface', 'Skirt', 'Brim', 'Prime tower', 'Custom'}
# Horn copies have identical feature totals and are interchangeable for this estimate.
ALIAS = {
    '201': 'base', '245': 'middle_link_main_body', '267': 'top_link_main_body',
    '223': 'middle_link_servo_horn_bracket', '311': 'top_link_servo_horn_bracket',
}


def parse(source):
    with zipfile.ZipFile(source) as archive:
        settings = json.loads(archive.read('Metadata/project_settings.config'))
        info = ET.fromstring(archive.read('Metadata/slice_info.config'))
        names = {o.attrib['identify_id']: o.attrib['name'] for o in info.iter('object')}
        gcode = archive.read('Metadata/plate_1.gcode').decode('utf-8')
    assert set(names) == set(ALIAS), 'Review object-to-CAD mapping for a different print job.'
    density = float(settings['filament_density'][0])
    diameter = float(settings['filament_diameter'][0])
    grams_per_mm = math.pi * (diameter / 2) ** 2 * density / 1000
    header_g = float(re.search(r'^; total filament weight \[g\] : ([\d.]+)', gcode, re.M)[1])
    header_mm = float(re.search(r'^; total filament length \[mm\] : ([\d.]+)', gcode, re.M)[1])
    feature, obj, relative, active = 'Custom', None, None, False
    debt, e_position, net_extrusion = 0., 0., 0.
    position = dict.fromkeys('XYZ', 0.)
    bounds = {}
    lengths = defaultdict(lambda: defaultdict(float))
    outside = defaultdict(float)
    for line in gcode.splitlines():
        if line == '; MACHINE_END_GCODE_START':
            break
        if line == '; CHANGE_LAYER':
            active = True
        code = line.split(';', 1)[0].strip()
        if code == 'M83':
            relative = True
        elif code == 'M82':
            relative = False
        elif code == 'G20':
            raise ValueError('Inch mode is not supported.')
        if not active:
            continue
        if match := re.fullmatch(r'; start printing object, unique label id: (\d+)', line):
            assert obj is None
            obj = match[1]
        elif match := re.fullmatch(r'; stop printing object, unique label id: (\d+)', line):
            assert obj == match[1]
            obj = None
        elif line.startswith('; FEATURE: '):
            feature = line[len('; FEATURE: '):]
        words = code.split()
        if not words:
            continue
        params = {k: float(v) for k, v in re.findall(r'([A-Z])(-?(?:\d*\.)?\d+)', code)}
        if words[0] == 'G92' and 'E' in params:
            e_position = params['E']
            continue
        if words[0] not in {'G0', 'G1', 'G2', 'G3'}:
            continue
        previous = position.copy()
        position.update({k: v for k, v in params.items() if k in position})
        if 'E' not in params:
            continue
        assert relative is not None, 'Unknown extrusion coordinate mode.'
        delta = params['E'] if relative else params['E'] - e_position
        e_position = e_position + delta if relative else params['E']
        net_extrusion += delta
        if delta < 0:
            debt -= delta
            continue
        deposited = max(0., delta - debt)
        debt = max(0., debt - delta)
        if deposited == 0:
            continue
        if obj is None:
            outside[feature] += deposited
        else:
            assert feature in MODEL_FEATURES | REMOVABLE_FEATURES, feature
            lengths[obj][feature] += deposited
            if feature in MODEL_FEATURES and ('X' in params or 'Y' in params):
                box = bounds.setdefault(obj, [[math.inf] * 3, [-math.inf] * 3])
                for axis, key in enumerate('XYZ'):
                    box[0][axis] = min(box[0][axis], previous[key], position[key])
                    box[1][axis] = max(box[1][axis], previous[key], position[key])

    assert obj is None, 'Unclosed object label.'
    parts = []
    for label, alias in ALIAS.items():
        features = {f: v * grams_per_mm for f, v in sorted(lengths[label].items())}
        parts.append({
            'alias': alias, 'gcode_object_label': label, 'slicer_name': names[label],
            'model_mass_g': sum(v for f, v in features.items() if f in MODEL_FEATURES),
            'removable_mass_g': sum(v for f, v in features.items() if f in REMOVABLE_FEATURES),
            'feature_mass_g': features,
            'model_toolpath_endpoint_bbox_mm': bounds[label],
            'model_toolpath_xy_span_mm': [bounds[label][1][i] - bounds[label][0][i] for i in (0, 1)],
            'model_top_z_mm': bounds[label][1][2],
        })
    labeled_mm = sum(sum(v.values()) for v in lengths.values())
    labeled_g = labeled_mm * grams_per_mm
    assert math.isclose(labeled_mm + sum(outside.values()), net_extrusion + debt, abs_tol=1e-6), 'Extrusion balance does not close.'
    assert abs(labeled_g - header_g) / header_g < .01, 'Mass audit differs by more than 1%.'
    return {
        'source': 'source/robot_print.gcode.3mf',
        'original_filename': 'Ipad_Tablet_Stand_by_Pork_3D(2).gcode.3mf',
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'method': 'G0/G1/G2/G3 extrusion after retract recovery, grouped by object start/stop and FEATURE comments. Filament flow ratio is already encoded; do not apply it again.',
        'settings': {k: settings[k] for k in [
            'layer_height', 'wall_loops', 'top_shell_layers', 'bottom_shell_layers',
            'sparse_infill_density', 'sparse_infill_pattern']},
        'filament_profile': settings['filament_settings_id'][0],
        'filament_density_g_per_cm3': density,
        'filament_diameter_mm': diameter,
        'slicer_header_total_g': header_g,
        'slicer_header_total_filament_mm': header_mm,
        'labeled_deposited_filament_mm': labeled_mm,
        'labeled_deposited_mass_g': labeled_g,
        'model_mass_g': sum(p['model_mass_g'] for p in parts),
        'removable_mass_g': sum(p['removable_mass_g'] for p in parts),
        'header_minus_labeled_mass_g': header_g - labeled_g,
        'net_extrusion_plus_remaining_retraction_mm': net_extrusion + debt,
        'outside_labels_after_machine_start_g': {f: v * grams_per_mm for f, v in outside.items()},
        'audit_note': 'The approximately 0.10 g header remainder is not assigned to the robot. Header accounting includes material outside labeled objects; machine-start purge/prime commands are deliberately excluded from part masses. Do not treat the header as the net assembled plastic mass.',
        'mapping_note': 'BASE/LINK/TIP map by name and plate image to base/middle/top. The two HORN copies have identical feature masses; assignment of copy 223 to middle and 311 to upper is interchangeable. STEP bracket shapes differ slightly, so using the same sliced mass is approximate.',
        'bounds_note': 'Model extrusion path endpoint bounds, excluding supports. XY omits bead width and intermediate arc extrema; Z starts at the first layer, not zero. These are mapping sanity checks, not exact solid bounds.',
        'limitations': 'Slicer predictions, not scale measurements. Assumes the supplied job describes the installed parts and the configured filament density/diameter match the material. Supports removed. Wires excluded by user.',
        'parts': parts,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', type=Path, default=HERE / 'source/robot_print.gcode.3mf')
    args = parser.parse_args()
    result = parse(args.source)
    (HERE / 'slicer_masses.json').write_text(json.dumps(result, indent=2) + '\n')
    for part in result['parts']:
        print(f"{part['alias']}: {part['model_mass_g']:.3f} g model, {part['removable_mass_g']:.3f} g removable")
    print(f"Model total: {result['model_mass_g']:.3f} g; supports/etc: {result['removable_mass_g']:.3f} g; header: {result['slicer_header_total_g']:.2f} g")
