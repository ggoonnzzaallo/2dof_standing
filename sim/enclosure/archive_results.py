"""Preserve enclosure experiments, select by development metrics, never upload."""
from pathlib import Path
import hashlib
import json
import shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'results'
OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
experiments=[]
for tag,folder in [('clone','enclosure_c2_policy_seed17'),('warm','enclosure_c2_warm_seed17'),('normalized','enclosure_c2_normalized_seed17')]:
    source=ROOT/'runs'/folder
    report=json.loads((source/'training_report.json').read_text())
    assert 'held_out_test' in report,'Experiment still running'
    assert report['robot_xml_sha256']==sha(HERE/'robot.xml')
    selected=next(s for s in report['stages'] if s['ppo_steps_actual']==report['selected_ppo_steps'])
    score=selected['nominal']['successes']+selected['development']['successes']
    experiments.append((score,tag,source,report,selected))
    shutil.copyfile(source/'training_report.json',OUT/(tag+'_training_report.json'))
    checkpoints=OUT/'checkpoints';checkpoints.mkdir(exist_ok=True)
    for p in source.glob('checkpoint_*.zip'):shutil.copyfile(p,checkpoints/(tag+'_'+p.name))
    for p in source.glob('normalization_*.pkl'):shutil.copyfile(p,checkpoints/(tag+'_'+p.name))
_,tag,source,report,selected=max(experiments,key=lambda e:e[0])
for n in ('training_report.json','best.zip'):shutil.copyfile(source/n,OUT/n)
for n,new in [('dataset.npz','demonstrations.npz'),('dataset.json','demonstrations.json')]:
    shutil.copyfile(ROOT/'runs/enclosure_c2_demos_seed17'/n,OUT/new)
search=OUT/'search';search.mkdir(exist_ok=True)
for p in (ROOT/'runs/enclosure_c2_search_seed17').iterdir():
    if p.suffix in ('.json','.npz'):shutil.copyfile(p,search/p.name)
contract=json.loads((ROOT/'sim/recovery/results/policy_contract.json').read_text())
contract.update({'status':'Enclosure candidate, offline only; not uploaded or physically validated',
    'IMU_estimator_integrated':True,'new_mount_orientation_confirmed_by_user':True,
    'robot_xml_sha256':sha(HERE/'robot.xml'),'actor_sha256':sha(OUT/'best.zip')})
(OUT/'policy_contract.json').write_text(json.dumps(contract,indent=2)+'\n')
summary={'status':'Offline enclosure experiments complete; hardware deployment not approved by offline metrics alone',
    'date':'2026-11-03','selected_experiment':tag,'selected_ppo_steps':report['selected_ppo_steps'],
    'selection':'Most successes on ten nominal plus ten development trials; ties prefer first experiment. Held-out trials excluded from selection.',
    'nominal_successes':selected['nominal']['successes'],'development_successes':selected['development']['successes'],
    'held_out_scripted_successes':report['held_out_test']['successes'],'held_out_scripted_episodes':report['held_out_test']['episodes'],
    'demonstrations':json.loads((OUT/'demonstrations.json').read_text())['accepted_episodes'],
    'robot_xml_sha256':sha(HERE/'robot.xml'),'actor_sha256':sha(OUT/'best.zip'),
    'experiments':[{'name':t,'selected_steps':r['selected_ppo_steps'],'actual_ppo_steps':r['stages'][-1]['ppo_steps_actual'],
        'nominal_successes':s['nominal']['successes'],'development_successes':s['development']['successes'],
        'success_bonus':r.get('reward_success_bonus',20),'normalized_rewards':r['config'].get('normalize_rewards',False)} for _,t,_,r,s in experiments],
    'ready_for_hardware_deployment':False,'firmware_uploaded':False,'physical_robot_commands_sent':False,
    'mesh_assets_sha256':json.loads((HERE/'model_report.json').read_text())['mesh_assets_sha256'],
    'total_ppo_transitions_across_experiments':sum(r['stages'][-1]['ppo_steps_actual'] for _,_,_,r,_ in experiments),
    'selected_policy_ancestry':'3000 BC updates, selected after 16896 PPO steps in clone run; actor-only transfer then 67584 additional PPO steps with normalized rewards and fresh critic.' if tag=='normalized' else 'See selected training report and warm-start hashes.',
    'next_training_focus':'Persistent recovery through failed attempts and post-recovery disturbances; trapped-start and varied-joint-state coverage; stable base recovery primary, neutral arm a soft preference; retain historical strict metrics.'}
if (OUT/'randomized_evaluation.json').exists() and (OUT/'old_actor_paired.json').exists():
    new=json.loads((OUT/'randomized_evaluation.json').read_text());old=json.loads((OUT/'old_actor_paired.json').read_text())
    if new['actor_sha256']==summary['actor_sha256'] and new['robot_xml_sha256']==summary['robot_xml_sha256']:
        assert [(t['seed'],t['requested_pose']) for t in new['trials']]==[(t['seed'],t['requested_pose']) for t in old['trials']]
        summary['fresh_randomized_comparison']={'episodes':new['episodes'],'first_seed':new['first_seed'],
            'candidate_successes':new['successes'],'old_actor_successes':old['successes'],'selection_used_these_trials':False}
if (OUT/'persistence_evaluation.json').exists():
    p=json.loads((OUT/'persistence_evaluation.json').read_text())
    if p['actor_sha256']==summary['actor_sha256'] and p['robot_xml_sha256']==summary['robot_xml_sha256']:
        summary['persistence_diagnostic']={'episodes':p['episodes'],'horizon_seconds':p['horizon_seconds'],
            'base_only_stable_at_10_30_60s':[p['metrics_at_seconds'][t]['base_only_stable'] for t in ('10','30','60')],
            'strict_success_at_10_30_60s':[p['metrics_at_seconds'][t]['strict_success'] for t in ('10','30','60')],
            'weights_or_reward_changed':False,'source':'persistence_evaluation.json'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
