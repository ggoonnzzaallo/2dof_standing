"""Extract only deposited model mass from user-provided sliced enclosure job."""
from pathlib import Path
import json
import sys
import zipfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'mass_properties'))
from parse_slicer import parse

source=HERE/'source/enclosure_print.gcode.3mf'
result=parse(source,{'157':'base_modified','197':'electronics_cup'})
assert {p['slicer_name'] for p in result['parts']}=={'base_modified.stl','electronics_cup.stl'}
for part in result['parts']:
    expected=35. if part['alias']=='base_modified' else 12.8
    assert abs(part['model_top_z_mm']-expected)<.01
result.update({'source':'source/enclosure_print.gcode.3mf','original_filename':'Untitled.gcode.3mf',
    'mapping_note':'Objects 157=base_modified.stl (35 mm tall) and 197=electronics_cup.stl (12.8 mm tall), confirmed by names, plate image and toolpath heights.',
    'audit_note':'Header remainder is unassigned; use deposited model material only. Support/interface removed from assigned mass.'})
(HERE/'slicer_masses.json').write_text(json.dumps(result,indent=2)+'\n')
with zipfile.ZipFile(source) as z:(HERE/'slicer_plate.png').write_bytes(z.read('Metadata/plate_1.png'))
c=json.loads((HERE/'configuration.json').read_text())
c['printed_mass_g']={p['alias']:p['model_mass_g'] for p in result['parts']}
c['printed_mass_source']='slicer_masses.json; user-provided Untitled.gcode.3mf, support material excluded'
c['imu_orientation_confirmed']=True
(HERE/'configuration.json').write_text(json.dumps(c,indent=2)+'\n')
for p in result['parts']:print(p['alias'],round(p['model_mass_g'],3),'g model;',round(p['removable_mass_g'],3),'g removable')
print('Header',result['slicer_header_total_g'],'g; unassigned',result['header_minus_labeled_mass_g'],'g')
