"""Bundle the one-piece fit print and its exact review references."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

OUT = Path(__file__).resolve().parent
FILES = ['electronics_cup.stl', 'electronics_cup.step', 'assembly_review.step',
         'base_modified.step', 'base_modified.stl', 'PRINT_FIT_CHECK.md',
         'preview.png', 'layout.svg', 'viewer.html', 'geometry.json',
         'validation.json', 'stl_validation.json']
FILES += ['fit_revision_1_reference.json']
cad = json.loads((OUT/'validation.json').read_text())
stl = json.loads((OUT/'stl_validation.json').read_text())
assert cad['pololu_count'] == 1
assert len(cad['parameters']['mount_centers']) == 2 and cad['parameters']['headers_removed']
assert stl['electronics_cup']['watertight'] and stl['electronics_cup']['components'] == 1
manifest = {
    'revision': 'Rev C2, lower enclosure and thin lid, two M2x10 screws into plastic',
    'prepared_date': '2026-11-03',
    'print_first': 'electronics_cup.stl',
    'required_parts': ['electronics_cup.stl', 'base_modified.stl'],
    'fasteners': 'Two M2 x 10 mm screws; 2.0 mm bores matching the user-proven printed bracket; no nuts or coupon',
    'units': 'mm', 'print_orientation': 'floor down, open side up, Z=0 already',
    'physical_fit_verified': False, 'electrical_commissioning_verified': False,
    'sha256': {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in FILES},
}
(OUT/'fit_package_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
with zipfile.ZipFile(OUT/'rev_c2_print_fit.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in [*FILES, 'fit_package_manifest.json']:
        archive.write(OUT/name, name)
with zipfile.ZipFile(OUT/'rev_c2_print_fit.zip') as archive:
    assert archive.testzip() is None
shutil.copyfile(OUT/'rev_c2_print_fit.zip', OUT/'rev_c_print_fit.zip')
print('Ready: rev_c2_print_fit.zip (and compatible rev_c alias). New cup + new thin lid; existing proven screw-hole size, no coupon. ONE Pololu; new physical fit pending.')
