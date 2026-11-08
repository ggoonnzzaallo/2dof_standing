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
    if 'runtime_validation_path' in manifest:
        assert digest(ROOT/manifest['runtime_validation_path'])==manifest['runtime_validation_sha256'],'Runtime validation changed'
    for entry in manifest.get('runtime_sources',[]):
        assert digest(ROOT/entry['path'])==entry['sha256'],'Recovery runtime source changed'
    expected=selection_header(manifest,directory)
    assert (directory/'PolicySelection.h').read_text()==expected,'Selection header and manifest differ'
    return manifest

def selection_header(manifest,directory):
    include=os.path.relpath(ROOT/manifest['actor_header_path'],directory).replace(os.sep,'/')
    return ('#pragma once\n#include "'+include+'"\n'
            +'static const char* const POLICY_GEOMETRY = '+json.dumps(manifest['geometry_id'])+';\n'
            +'static const char* const POLICY_ACTOR_SHA256 = '+json.dumps(manifest['actor_header_sha256'])+';\n'
            +'static const char* const POLICY_RUNTIME_SHA256 = '+json.dumps(manifest.get('retry_strategy_sha256','none'))+';\n'
            +'static constexpr float POLICY_ACTION_INCREMENT_RAD = '+str(manifest.get('action_increment_rad',.06))+'f;\n'
            +'static constexpr bool POLICY_RETRIES = '+str(manifest.get('retry_supervisor',False)).lower()+';\n')

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
              'observation_count':10,'action_count':2,'period_ms':20,'action_increment_rad':training['config'].get('action_increment_rad',.06),
              'retry_supervisor':training['config'].get('retry_supervisor',False),
              'hardware_validation':'Separate deployment record; selection does not imply physical success'}
    for name,path in [('actor_header',args.actor_header),('actor_archive',args.actor_archive),('model',args.model),('training_report',args.training_report)]:
        manifest[name+'_path']=str(path.resolve().relative_to(ROOT));manifest[name+'_sha256']=digest(path)
    if manifest['retry_supervisor']:
        source=ROOT/'firmware/policy_control/RecoveryStrategy.h'
        runtime_sha=training['strategy_sha256']
        if args.runtime_validation:
            validation=json.loads(args.runtime_validation.read_text())
            assert validation['status']=='passed' and validation['actor_archive_sha256']==digest(args.actor_archive)
            assert validation['robot_xml_sha256']==digest(args.model)
            runtime_sha=validation['strategy_sha256']
            manifest['runtime_validation_path']=str(args.runtime_validation.resolve().relative_to(ROOT))
            manifest['runtime_validation_sha256']=digest(args.runtime_validation)
        assert digest(source)==runtime_sha,'Retry code differs from training/validated runtime'
        manifest['retry_strategy_sha256']=runtime_sha
        manifest['runtime_sources']=[{'path':str(source.relative_to(ROOT)),'sha256':digest(source)}]
        environment=(args.model.parent/'robust_env.py').resolve()
        assert digest(environment)==training['environment_sha256'],'Environment differs from selected training'
        manifest['runtime_sources'].append({'path':str(environment.relative_to(ROOT)),'sha256':digest(environment)})
        for path in (ROOT/'sim/environment.py',args.model.parent/'strategy.py'):
            path=path.resolve()
            manifest['runtime_sources'].append({'path':str(path.relative_to(ROOT)),'sha256':digest(path)})
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
    p.add_argument('--runtime-validation',type=Path,help='Explicit actor/model-matched validation for a later portable retry guard adjustment')
    p.add_argument('--out-dir',type=Path,default=ROOT/'firmware/policy_control')
    select(p.parse_args())
if __name__=='__main__':main()
