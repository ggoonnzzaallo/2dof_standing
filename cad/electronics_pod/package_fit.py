"""Bundle the one-piece fit print and its exact review references."""
from pathlib import Path
import hashlib
import json
import zipfile

OUT = Path(__file__).resolve().parent
assert (OUT/'assembly_review.step').read_bytes() == (OUT.parent/'assembly.step').read_bytes(), 'Top-level assembly must match the current C3 robot'
FILES = ['electronics_cup.stl', 'electronics_cup.step', 'assembly_review.step',
         'base_modified.step', 'base_modified.stl', 'PRINT_FIT_CHECK.md',
         'preview.png', 'layout.svg', 'viewer.html', 'geometry.json',
         'validation.json', 'stl_validation.json']
FILES += ['fit_revision_1_reference.json', 'fit_revision_2_reference.json']
cad = json.loads((OUT/'validation.json').read_text())
stl = json.loads((OUT/'stl_validation.json').read_text())
assert cad['pololu_count'] == 1
assert len(cad['parameters']['mount_centers']) == 2 and cad['parameters']['headers_removed']
assert stl['electronics_cup']['watertight'] and stl['electronics_cup']['components'] == 1
manifest = {
    'revision': 'Rev C3, tighter USB opening and outward battery; existing C2 lid compatible',
    'prepared_date': '2026-11-10',
    'geometry_revision_date': '2026-11-03',
    'installed_confirmed_date': '2026-11-07',
    'print_first': 'electronics_cup.stl',
    'required_parts': ['electronics_cup.stl', 'base_modified.stl'],
    'upgrade_from_c2_required_parts': ['electronics_cup.stl'],
    'compatible_existing_lid': 'Rev C2 base_modified.stl; supplied again for new builds, no reprint needed',
    'fasteners': 'Two M2 x 10 mm screws; 2.0 mm bores matching the user-proven printed bracket; no nuts or coupon',
    'units': 'mm', 'print_orientation': 'floor down, open side up, Z=0 already',
    'installed_confirmed_by_user': True,
    'physical_fit_verified': False, 'electrical_commissioning_verified': False,
    'verification_note': 'C3 installation confirmed by user; no complete formal fit or electrical commissioning record.',
    'sha256': {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in FILES},
}
(OUT/'fit_package_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
assert hashlib.sha256((OUT/'base_modified.stl').read_bytes()).hexdigest()==json.loads((OUT/'fit_revision_2_reference.json').read_text())['base_modified_stl_sha256'], 'C2 lid must remain byte-identical'
with zipfile.ZipFile(OUT/'rev_c3_print_fit.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in [*FILES, 'fit_package_manifest.json']:
        archive.write(OUT/name, name)
with zipfile.ZipFile(OUT/'rev_c3_print_fit.zip') as archive:
    assert archive.testzip() is None
print('Ready: rev_c3_print_fit.zip. Complete current robot: cad/assembly.step. Existing C2 lid unchanged.')
