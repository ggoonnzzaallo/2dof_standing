"""Assign slicer masses to STEP parts with explicitly approximate CAD distribution."""
from pathlib import Path
import json
import numpy as np

HERE = Path(__file__).resolve().parent
slicer = json.loads((HERE / 'slicer_masses.json').read_text())
cad = json.loads((HERE / 'cad_geometric_properties.json').read_text())
by_alias = {p['alias']: p for p in cad['parts']}
parts = []
for item in slicer['parts']:
    geom = by_alias[item['alias']]
    mass = item['model_mass_g'] / 1000
    inertia = np.array(geom['unit_density_inertia_about_centroid_mm5']) * mass / geom['cad_volume_mm3'] * 1e-6
    assert mass > 0 and np.allclose(inertia, inertia.T)
    eigenvalues = np.linalg.eigvalsh(inertia)
    assert eigenvalues[0] > 0 and eigenvalues[-1] <= sum(eigenvalues[:2]) + 1e-12
    parts.append({
        'alias': item['alias'], 'rigid_group': geom['rigid_group'], 'mass_kg': mass,
        'center_of_mass_cad_m': [v / 1000 for v in geom['uniform_solid_centroid_cad_mm']],
        'inertia_about_com_in_cad_axes_kg_m2': inertia.tolist(),
        'mass_source': 'slicer_masses.json, supports excluded',
        'distribution_assumption': 'Uniform CAD density scaled to sliced mass. Does not resolve shell/infill distribution or true print COM.',
    })
groups = []
for group in ('base', 'middle', 'upper'):
    members = [p for p in parts if p['rigid_group'] == group]
    mass = sum(p['mass_kg'] for p in members)
    center = sum(p['mass_kg'] * np.array(p['center_of_mass_cad_m']) for p in members) / mass
    inertia = np.zeros((3, 3))
    for p in members:
        offset = np.array(p['center_of_mass_cad_m']) - center
        inertia += np.array(p['inertia_about_com_in_cad_axes_kg_m2'])
        inertia += p['mass_kg'] * (np.dot(offset, offset) * np.eye(3) - np.outer(offset, offset))
    groups.append({'rigid_group': group, 'scope': 'PRINTED PARTS ONLY; hardware not included',
                   'mass_kg': mass, 'center_of_mass_cad_m': center.tolist(),
                   'inertia_about_com_in_cad_axes_kg_m2': inertia.tolist()})
result = {
    'status': 'Preliminary printed-part assignments; not installed in sim/robot.xml',
    'step_sha256': cad['source_sha256'], 'slicer_sha256': slicer['source_sha256'],
    'coordinate_frame': 'CAD assembly axes at exported upright pose, SI units. Rotate/translate into each MuJoCo body frame when building the new model.',
    'wiring_mass': 'Excluded by user; no future carrier PCB mass added',
    'parts': parts, 'printed_only_groups': groups,
    'remaining_hardware': [
        {'alias': 'battery', 'nominal_mass_g': 14.5, 'status': 'Nominal estimate, not measured',
         'source': 'https://manuals.plus/m/12c0389d1bad51442e0f2c69f8a2cd04fbcebbebf7741695b6755793b37fda09',
         'note': 'Manufacturer-authored E-flite catalog, EFLB5001S25 entry. Model internals/COM not supplied.'},
        {'alias': 'lower_servo', 'nominal_mass_g': 13.0, 'status': 'Related 7465 MG-D family proxy; confirm exact purchased non-W unit',
         'source': 'https://www.ptkhobby.com/en/sys-pd/234.html'},
        {'alias': 'upper_servo', 'nominal_mass_g': 13.0, 'status': 'Same family proxy as lower servo',
         'source': 'https://www.ptkhobby.com/en/sys-pd/234.html'},
        {'alias': 'controller_board', 'nominal_mass_g': None, 'status': 'Bare classic Sense board mass not verified from manufacturer; headers/solder affect installed mass'},
        {'alias': 'unmodeled_hardware', 'nominal_mass_g': None, 'status': 'Account for fitted OEM horns, screws and any other installed small hardware absent from STEP; avoid double counting'}
    ],
    'limitations': 'Slicer mass is estimated. Hardware COM and inertia cannot be inferred from datasheet mass alone. The two printed HORN copies share sliced mass but have slightly different STEP shapes. Wiring harness excluded; published assembly weights may already include factory leads/connectors, which have not been separately subtracted.',
}
(HERE / 'assigned_properties.json').write_text(json.dumps(result, indent=2) + '\n')
print(f"Assigned {len(parts)} printed components; {sum(p['mass_kg'] for p in parts)*1000:.3f} g. Hardware remains separate.")
