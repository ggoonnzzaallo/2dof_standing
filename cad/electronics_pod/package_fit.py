"""Bundle the one-piece fit print and its exact review references."""
from pathlib import Path
import hashlib
import json
import zipfile

OUT = Path(__file__).resolve().parent
FILES = ['electronics_cup.stl', 'electronics_cup.step', 'assembly_review.step',
         'base_modified.step', 'base_modified.stl', 'PRINT_FIT_CHECK.md',
         'preview.png', 'layout.svg', 'viewer.html', 'geometry.json',
         'validation.json', 'stl_validation.json']
cad = json.loads((OUT/'validation.json').read_text())
stl = json.loads((OUT/'stl_validation.json').read_text())
assert cad['pololu_count'] == 1
assert stl['electronics_cup']['watertight'] and stl['electronics_cup']['components'] == 1
manifest = {
    'revision': 'Rev C, one Pololu, fit-print package',
    'prepared_date': '2026-11-03',
    'print_first': 'electronics_cup.stl',
    'units': 'mm', 'print_orientation': 'floor down, open side up, Z=0 already',
    'physical_fit_verified': False, 'electrical_commissioning_verified': False,
    'sha256': {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in FILES},
}
(OUT/'fit_package_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
with zipfile.ZipFile(OUT/'rev_c_print_fit.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in [*FILES, 'fit_package_manifest.json']:
        archive.write(OUT/name, name)
with zipfile.ZipFile(OUT/'rev_c_print_fit.zip') as archive:
    assert archive.testzip() is None
print('Ready: rev_c_print_fit.zip; print electronics_cup.stl first. ONE Pololu; physical fit pending.')
