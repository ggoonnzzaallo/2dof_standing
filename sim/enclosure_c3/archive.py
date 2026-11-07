"""Preserve a completed C3 run without overwriting original/C2 experiments."""
from pathlib import Path
import argparse,csv,hashlib,json,shutil
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);a=p.parse_args()
    r=json.loads((a.run/'training_report.json').read_text());out=HERE/'results';out.mkdir(exist_ok=True)
    assert r['training_source_sha256']==sha(HERE/'train.py')
    assert r['robot_xml_sha256']==sha(HERE/'robot.xml')
    shutil.copyfile(a.run/'training_report.json',out/'training_report_original.json')
    r['config']['filtered']=True
    r['metadata_note']='filtered=true explicitly records the always-filtered PersistentEnv; source report remains preserved separately.'
    (out/'training_report.json').write_text(json.dumps(r,indent=2)+'\n')
    shutil.copyfile(HERE/'train.py',out/'training_source.py')
    shutil.copyfile(a.run/'best.zip',out/'best.zip')
    for folder,pattern in [('checkpoints','checkpoint_*.zip'),('return_normalization','return_normalization_*.pkl'),('episodes','episodes/*.monitor.csv')]:
        (out/folder).mkdir(exist_ok=True)
        for f in a.run.glob(pattern):shutil.copyfile(f,out/folder/f.name)
    selected=r['selected_actual_steps'];stage=next(s for s in r['stages'] if s['actual_steps']==selected)
    selected_episodes=0
    for f in (out/'episodes').glob('*.monitor.csv'):
        cursor=0
        with f.open() as stream:
            next(stream)
            for row in csv.DictReader(stream):
                cursor+=int(row['l'])
                if cursor<=selected/r['config']['envs']:selected_episodes+=1
    summary={'date':'2026-11-07','status':'C3-trained actor selected; physical validation separate',
             'algorithm':'PPO, actor warm-start from C2; new critic; training-return normalization only',
             'additional_ppo_steps_run':r['stages'][-1]['actual_steps'],'selected_additional_ppo_steps':selected,
             'completed_training_episodes':r['completed_training_episodes'],'completed_episodes_at_selected_checkpoint':selected_episodes,
             'episodes_recovered_at_least_once':r['episodes_recovered_at_least_once'],
             'episodes_ending_with_control_fault':r['episodes_ending_with_control_fault'],
             'selection_criteria':r['selection'],'standard_development_evaluation':stage['evaluation'],
             'checkpoints_saved':len(list((out/'checkpoints').glob('*.zip'))),
             'robot_xml_sha256':sha(HERE/'robot.xml'),'mesh_assets_sha256':json.loads((HERE/'model_report.json').read_text())['mesh_assets_sha256'],
             'actor_archive_sha256':sha(out/'best.zip'),'warm_start_actor_sha256':r['warm_start_sha256'],
             'source_training_report_sha256':sha(out/'training_report_original.json'),'training_source_sha256':sha(out/'training_source.py'),
             'firmware_uploaded':False,'physical_recovery_confirmed':False,
             'limitation':'Base-only recovery is primary. Preserve strict-posture scores and bent final pose; do not call base-only successes straight-arm recoveries.'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='standard_development_evaluation'},indent=2))
if __name__=='__main__':main()
