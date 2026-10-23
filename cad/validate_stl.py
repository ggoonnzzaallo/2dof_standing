"""Check the exported binary STLs for closed, connected triangle meshes."""

import json
import struct
from collections import defaultdict, deque
from pathlib import Path

OUT = Path(__file__).resolve().parent
NAMES = (
    'base.stl', 'middle_link.stl', 'paddle.stl',
    'servo_mount_fit_coupon.stl', 'horn_fit_coupon.stl',
    'pivot_fit_coupon.stl', 'battery_tunnel_fit_coupon.stl',
)


def inspect(path):
    data = path.read_bytes()
    count = struct.unpack_from('<I', data, 80)[0]
    if len(data) != 84 + 50 * count:
        raise ValueError(f'{path.name}: not a valid binary STL length')
    edges = defaultdict(list)
    signed_volume = 0.0
    for face in range(count):
        offset = 84 + 50 * face + 12
        points = [struct.unpack_from('<fff', data, offset + 12 * i) for i in range(3)]
        keys = [tuple(round(c, 4) for c in point) for point in points]
        if len(set(keys)) != 3:
            raise ValueError(f'{path.name}: degenerate triangle {face}')
        for i, j in ((0, 1), (1, 2), (2, 0)):
            edges[tuple(sorted((keys[i], keys[j])))].append(face)
        a, b, c = points
        signed_volume += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6
    watertight = all(len(faces) == 2 for faces in edges.values())
    adjacent = [[] for _ in range(count)]
    for faces in edges.values():
        if len(faces) == 2:
            a, b = faces
            adjacent[a].append(b)
            adjacent[b].append(a)
    unseen = set(range(count))
    components = 0
    while unseen:
        components += 1
        seed = unseen.pop()
        queue = deque([seed])
        while queue:
            for neighbor in adjacent[queue.popleft()]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
    return {
        'watertight': watertight,
        'components': components,
        'volume_mm3': round(abs(signed_volume), 1),
    }


results = {name: inspect(OUT / name) for name in NAMES}
assert all(item['watertight'] and item['components'] == 1 for item in results.values())
(OUT / 'stl_validation.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
