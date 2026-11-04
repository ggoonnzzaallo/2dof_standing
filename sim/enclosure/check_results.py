"""Verify saved enclosure experiment metrics, sources, weights and mesh provenance."""
from pathlib import Path
import hashlib,json,zipfile
import numpy as np
from asset_hashes import snapshot
HERE=Path(__file__).resolve().parent
R=HERE/'results'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    s=json.loads((R/'summary.json').read_text());m=json.loads((HERE/'model_report.json').read_text())
    assert s['robot_xml_sha256']==m['robot_xml_sha256']==sha(HERE/'robot.xml')
    assert snapshot(HERE/'robot.xml')['mesh_assets_sha256']==s['mesh_assets_sha256']==m['mesh_assets_sha256']
    assert s['actor_sha256']==sha(R/'best.zip')
    c=json.loads((R/'policy_enclosure.json').read_text())
    assert c['model_sha256']==s['actor_sha256'] and c['actor_header_sha256']==sha(R/'policy_enclosure.h')
    assert c['host_C_max_absolute_error']<1e-5 and c['host_C_test_vectors']==2000
    meta=json.loads((R/'demonstrations.json').read_text());data=np.load(R/'demonstrations.npz')
    assert meta['dataset_sha256']==sha(R/'demonstrations.npz')
    assert meta['source_report_sha256']==sha(R/'search/report.json')
    assert data['observation'].shape==(meta['frames'],10) and data['action'].shape==(meta['frames'],2)
    assert np.isfinite(data['observation']).all() and np.isfinite(data['action']).all()
    assert len(np.unique(data['episode_id']))==meta['accepted_episodes']==52
    assert meta['filtered_observations']
    for name in ('clone','warm','normalized'):
        r=json.loads((R/(name+'_training_report.json')).read_text())
        assert r['robot_xml_sha256']==s['robot_xml_sha256'] and r['dataset_sha256']==meta['dataset_sha256']
        for stage in r['stages']:
            for mode in ('nominal','development'):
                e=stage[mode];assert sum(t['success'] for t in e['trials'])==e['successes']
        assert sum(t['success'] for t in r['held_out_test']['trials'])==r['held_out_test']['successes']
    new=json.loads((R/'randomized_evaluation.json').read_text());old=json.loads((R/'old_actor_paired.json').read_text())
    assert [(t['seed'],t['requested_pose']) for t in new['trials']]==[(t['seed'],t['requested_pose']) for t in old['trials']]
    assert sum(t['success'] for t in new['trials'])==new['successes']==18
    assert sum(t['success'] for t in old['trials'])==old['successes']==8
    assert not any(t['mujoco_warnings'] for t in new['trials']+old['trials'])
    p=json.loads((R/'persistence_evaluation.json').read_text())
    assert p['actor_sha256']==s['actor_sha256'] and p['robot_xml_sha256']==s['robot_xml_sha256']
    assert p['episodes']==len(p['trials'])==20 and p['horizon_seconds']==60
    assert not any(t['mujoco_warnings'] or t['termination'].endswith('fault') for t in p['trials'])
    for seconds,counts in p['metrics_at_seconds'].items():
        for metric,key in [('base_only_stable','first_base_only_stable_s'),('strict_success','first_strict_success_s')]:
            assert sum(t[key] is not None and t[key]<=float(seconds) for t in p['trials'])==counts[metric]==16
    normalized=json.loads((R/'normalized_training_report.json').read_text())
    selected=next(stage for stage in normalized['stages'] if stage['ppo_steps_actual']==s['selected_ppo_steps'])
    historical={(mode,t['case']):t for mode in ('nominal','development') for t in selected[mode]['trials']}
    for trial in p['trials']:
        t=trial['first_strict_success_s']
        old_trial=historical[trial['mode'],trial['case']]
        assert (t is not None and t<=10)==old_trial['success']
        if t is not None and t<=10:assert abs(t-old_trial['seconds'])<1e-9
    for z in (R/'checkpoints').glob('*.zip'):
        with zipfile.ZipFile(z) as f:assert f.testzip() is None
    assert len(list((R/'checkpoints').glob('*.zip')))==15
    assert not s['firmware_uploaded'] and not s['physical_robot_commands_sent'] and not s['ready_for_hardware_deployment']
    files={str(p.relative_to(HERE)):sha(p) for p in R.rglob('*') if p.is_file() and p.name!='artifact_validation.json'}
    out={'status':'passed','model_and_mesh_bundle':'matched','dataset_frames':meta['frames'],'dataset_episodes':meta['accepted_episodes'],
        'checkpoints':15,'paired_random_successes':{'candidate':18,'old_actor':8,'episodes_each':30},
        'host_C_parity':'passed','persistence_goal_successes_at_10_30_60s':[16,16,16],
        'firmware_uploaded':False,'artifact_sha256':files}
    (R/'artifact_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print('PASS: models/meshes, dataset, all experiment metrics, 15 checkpoint ZIPs, paired trials and C export')
if __name__=='__main__':main()
