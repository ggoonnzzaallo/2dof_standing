"""Pin a verified actor to its training geometry and check it before compiling.

Generate selection only after simulation/export validation. This opens no serial
port. Hardware behavior is a separate observation, never inferred from hashes.
"""
import argparse,hashlib,json,os,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_selection(directory=ROOT/'firmware/policy_control'):
    directory=Path(directory)
    manifest=json.loads((directory/'PolicyManifest.json').read_text())
    for key in ('actor_header','actor_archive','model','training_report'):
        assert digest(ROOT/manifest[key+'_path'])==manifest[key+'_sha256'],f'{key} changed since selection'
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('model_assets',ROOT/'sim/enclosure/asset_hashes.py')
    module=module_from_spec(spec);spec.loader.exec_module(module)
    assert module.snapshot(ROOT/manifest['model_path'])['mesh_assets_sha256']==manifest['mesh_assets_sha256'],'Physics mesh bundle changed'
    expected=selection_header(manifest,directory)
    assert (directory/'PolicySelection.h').read_text()==expected,'Selection header and manifest differ'
    return manifest

def selection_header(manifest,directory):
    include=os.path.relpath(ROOT/manifest['actor_header_path'],directory).replace(os.sep,'/')
    return ('#pragma once\n#include "'+include+'"\n'
            +'static const char* const POLICY_GEOMETRY = '+json.dumps(manifest['geometry_id'])+';\n'
            +'static const char* const POLICY_ACTOR_SHA256 = '+json.dumps(manifest['actor_header_sha256'])+';\n')

def select(args):
    export=json.loads(args.export_metadata.read_text());training=json.loads(args.training_report.read_text())
    model_report=json.loads(args.model.with_name('model_report.json').read_text())
    assert re.fullmatch('[a-z0-9_]{1,48}',args.geometry_id),'Invalid geometry ID'
    assert export['status']=='passed' and export['host_C_max_absolute_error']<1e-5
    assert export['actor_parameters']==4994 and export['model_sha256']==digest(args.actor_archive)
    assert export['actor_header_sha256']==digest(args.actor_header)
    assert training['robot_xml_sha256']==model_report['robot_xml_sha256']==digest(args.model)
    assert training['config'].get('filtered',False),'Expected firmware-filter observations'
    manifest={'geometry_id':args.geometry_id,'mesh_assets_sha256':model_report['mesh_assets_sha256'],
              'observation_count':10,'action_count':2,'period_ms':20,'action_increment_rad':.06,
              'hardware_validation':'Separate deployment record; selection does not imply physical success'}
    for name,path in [('actor_header',args.actor_header),('actor_archive',args.actor_archive),('model',args.model),('training_report',args.training_report)]:
        manifest[name+'_path']=str(path.resolve().relative_to(ROOT));manifest[name+'_sha256']=digest(path)
    args.out_dir.mkdir(parents=True,exist_ok=True)
    (args.out_dir/'PolicyManifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (args.out_dir/'PolicySelection.h').write_text(selection_header(manifest,args.out_dir))
    verify_selection(args.out_dir)
    print('Selected',args.geometry_id,'actor',manifest['actor_header_sha256'][:12])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--actor-archive',type=Path,required=True);p.add_argument('--actor-header',type=Path,required=True)
    p.add_argument('--export-metadata',type=Path,required=True);p.add_argument('--model',type=Path,required=True)
    p.add_argument('--training-report',type=Path,required=True);p.add_argument('--geometry-id',required=True)
    p.add_argument('--out-dir',type=Path,default=ROOT/'firmware/policy_control')
    select(p.parse_args())
if __name__=='__main__':main()
