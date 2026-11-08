"""Freeze corrected C3 robust run; never archive the invalid reset experiment."""
from pathlib import Path
import argparse,csv,hashlib,json,shutil
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--checkpoint',type=int);a=p.parse_args()
    report=json.loads((a.run/'training_report.json').read_text());out=HERE/'results';out.mkdir(exist_ok=True)
    assert report['environment_sha256']==sha(HERE/'robust_env.py')
    assert report['strategy_sha256']==sha(HERE.parents[2]/'firmware/policy_control/RecoveryStrategy.h')
    assert report['robot_xml_sha256']==sha(HERE/'robot.xml')
    selected=a.checkpoint if a.checkpoint is not None else report['selected_actual_steps']
    report['selected_actual_steps']=selected
    report['archival_note']='Corrected-pose training only; source/runtime reports supersede the explicitly invalid seed83 mass-reset stage.'
    report['base_environment_sha256']=sha(HERE.parents[1]/'environment.py')
    (out/'training_report.json').write_text(json.dumps(report,indent=2)+'\n')
    shutil.copyfile(a.run/f'checkpoint_{selected:06d}.zip',out/'best.zip')
    for folder,pattern in [('checkpoints','checkpoint_*.zip'),('return_normalization','return_normalization_*.pkl'),('episodes','episodes/*.monitor.csv')]:
        (out/folder).mkdir(exist_ok=True)
        for f in a.run.glob(pattern):shutil.copyfile(f,out/folder/f.name)
    (out/'source').mkdir(exist_ok=True)
    for f in ['train.py','robust_env.py','strategy.py']:shutil.copyfile(HERE/f,out/'source'/f)
    print('Archived corrected robust checkpoint',selected,sha(out/'best.zip'))
if __name__=='__main__':main()
