"""Generate visual meshes and separate convex collision meshes from placed CAD.

Run once after a new Onshape import. This never opens a serial port.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import time
import coacd
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRINTED = {'base', 'middle_link_main_body', 'middle_link_servo_horn_bracket',
           'top_link_main_body', 'top_link_servo_horn_bracket'}
DECOMPOSED = PRINTED | {'lower_servo', 'upper_servo'}
PARAMETERS = dict(threshold=.0006, real_metric=True, preprocess_mode='auto',
                  resolution=2000, mcts_nodes=15, mcts_iterations=100,
                  mcts_max_depth=3, decimate=True, max_ch_vertex=64, seed=17)


def write_obj(path, vertices, faces):
    with path.open('w') as output:
        output.write('# CAD assembly coordinates, meters. Generated; see manifest.json.\n')
        for v in vertices:
            output.write('v ' + ' '.join(f'{x:.10g}' for x in v) + '\n')
        for f in faces:
            output.write('f ' + ' '.join(str(int(i) + 1) for i in f) + '\n')


def volume(vertices, faces):
    triangles = np.asarray(vertices)[np.asarray(faces, dtype=int)]
    return abs(np.einsum('ij,ij->i', triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum() / 6)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild', action='store_true')
    args = parser.parse_args()
    source = ROOT / 'cad/onshape_import/geometry.json'
    geometry = json.loads(source.read_text())
    asset_dir = HERE / 'assets'
    asset_dir.mkdir(exist_ok=True)
    coacd.set_log_level('warn')
    manifest = {'step_sha256': geometry['source_sha256'],
                'geometry_json_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'coordinates': 'Exported CAD assembly frame, meters',
                'coacd_version': importlib.metadata.version('coacd'),
                'coacd_parameters': PARAMETERS, 'parts': {}}
    for alias, part in geometry['parts'].items():
        vertices = np.asarray(part['vertices'], dtype=float) / 1000
        faces = np.asarray(part['triangles'], dtype=np.int32)
        # Weld duplicated CAD face seams without importing a general scene stack.
        vertices, inverse = np.unique(np.round(vertices, 10), axis=0, return_inverse=True)
        faces = inverse[faces]
        triangles = vertices[faces]
        nondegenerate = np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0], triangles[:,2]-triangles[:,0]), axis=1) > 1e-18
        removed = int(np.sum(~nondegenerate))
        faces = faces[nondegenerate]
        edges = np.sort(np.concatenate([faces[:, [0,1]], faces[:, [1,2]], faces[:, [2,0]]]), axis=1)
        _, counts = np.unique(edges, axis=0, return_counts=True)
        watertight = bool(np.all(counts == 2))
        parameters = {**PARAMETERS, 'preprocess_mode': 'off' if watertight else 'auto'}
        visual = f'{alias}_visual.obj'
        write_obj(asset_dir / visual, vertices, faces)
        hull_path = asset_dir / f'{alias}_hulls.json'
        # Cache is source- and parameter-specific, not filename-specific.
        key = hashlib.sha256(json.dumps({'vertices': vertices.tolist(), 'faces': faces.tolist(),
                                        'parameters': parameters, 'version': manifest['coacd_version']},
                                       sort_keys=True).encode()).hexdigest()
        start = time.monotonic()
        if alias not in DECOMPOSED:
            hulls = []
            method = 'CAD bounding box hardware envelope; internal geometry not modeled'
        elif hull_path.exists() and not args.rebuild and json.loads(hull_path.read_text())['key'] == key:
            hulls = json.loads(hull_path.read_text())['hulls']
            method = 'CoACD, separate mesh asset for each convex piece'
        else:
            print(f'Decomposing {alias}: {len(faces)} triangles, watertight={watertight}', flush=True)
            hulls = coacd.run_coacd(coacd.Mesh(vertices, faces), **parameters)
            hulls = [(v.tolist(), f.tolist()) for v, f in hulls]
            hull_path.write_text(json.dumps({'key': key, 'hulls': hulls}, separators=(',', ':')) + '\n')
            method = 'CoACD, separate mesh asset for each convex piece'
        files = []
        for old in asset_dir.glob(f'{alias}_collision_*.obj'):
            old.unlink()
        for i, (v, f) in enumerate(hulls):
            filename = f'{alias}_collision_{i:02d}.obj'
            write_obj(asset_dir / filename, v, f)
            files.append(filename)
        manifest['parts'][alias] = {
            'group': part['group'], 'visual': visual, 'collision_meshes': files,
            'collision_method': method, 'input_watertight_after_welding': watertight,
            'removed_degenerate_triangles': removed, 'parameters': parameters if alias in DECOMPOSED else None,
            'bbox_cad_m': [vertices.min(axis=0).tolist(), vertices.max(axis=0).tolist()],
            'cad_mesh_volume_m3': float(volume(vertices, faces)),
            'sum_collision_hull_volume_m3': float(sum(volume(v, f) for v, f in hulls)),
        }
        print(f'{alias}: {len(hulls)} collision pieces ({time.monotonic()-start:.1f}s)', flush=True)
        (HERE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
