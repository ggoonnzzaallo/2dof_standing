"""Use the existing binary STL checker; no scientific/visualization imports."""
from pathlib import Path
import json
import struct
import sys

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent))
from validate_stl import inspect

cad = json.loads((OUT/'validation.json').read_text())
result = {}
for name in ('electronics_cup', 'base_modified'):
    path = OUT/(name+'.stl')
    check = inspect(path)
    data = path.read_bytes()
    count = struct.unpack_from('<I', data, 80)[0]
    points = [struct.unpack_from('<fff', data, 84+50*i+12+12*j)
              for i in range(count) for j in range(3)]
    bounds = [[min(p[a] for p in points) for a in range(3)],
              [max(p[a] for p in points) for a in range(3)]]
    check.update(triangles=count, bounds_mm=bounds)
    assert check['watertight'] and check['components'] == 1, (name, check)
    assert abs(bounds[0][2]) < .001, (name, 'not on print bed')
    assert abs(check['volume_mm3']/cad['printed_parts'][name]['volume_mm3']-1) < .002, (name, 'mesh/solid volume differs')
    result[name] = check
(OUT/'stl_validation.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
