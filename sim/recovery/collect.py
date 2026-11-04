"""Replay searched motions under perturbations and retain successful audited demos."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import search
from audit import AdjacentAudit
from evaluate_filter import FilteredEnv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--repeats',type=int,default=8,help='One nominal and remaining randomized attempts per case')
    parser.add_argument('--out',type=Path,default=Path('runs/recovery_demos'))
    parser.add_argument('--filtered',action='store_true',help='Record observations from the firmware gravity filter')
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    model_hash = hashlib.sha256(search.MODEL_PATH.read_bytes()).hexdigest()
    assert report['robot_xml_sha256']==model_hash
    audit = AdjacentAudit()
    observations,actions,ids,case_ids = [],[],[],[]
    attempts = []
    episode_id = 0
    entries = report['results'] + [{'case':'upright','waypoints_rad':np.zeros((report['config']['knots'],2)).tolist()}]
    for case_index,item in enumerate(entries):
        if item['case']!='upright':
            assert item['adjacent_collision_audit']['status']=='passed', 'Audit searched trajectory first.'
        for repeat in range(args.repeats):
            seed = 1000+case_index*100+repeat
            rng = np.random.default_rng(seed)
            options = dict(search.CASES[item['case']])
            if repeat:
                options['tilt'] += np.deg2rad(rng.uniform(-8,8))
                options['azimuth'] += np.deg2rad(rng.uniform(-8,8))
            env = (FilteredEnv if args.filtered else search.SelfRightingEnv)(randomize=repeat!=0)
            env.reset(seed=seed,options=options)
            search.ENV = env
            result,trace = search.rollout((item['case'],seed,np.array(item['waypoints_rad']),report['config']['segment'],report['config']['hold']),record=True,reset=False)
            check = audit.check(np.vstack([trace['qpos'],trace['final_qpos']])) if result['success'] else None
            accepted = result['success'] and check['status']=='passed'
            if accepted:
                observations.extend(trace['observation']);actions.extend(trace['action'])
                ids.extend([episode_id]*len(trace['action']));case_ids.extend([case_index]*len(trace['action']))
                episode_id += 1
            attempts.append({'case':item['case'],'seed':seed,'randomized':repeat!=0,'requested_start':options,
                             'result':result,'adjacent_audit':check,'accepted':accepted})
            env.close()
        print(item['case'],sum(x['accepted'] for x in attempts if x['case']==item['case']),'/',args.repeats,'accepted',flush=True)
    assert episode_id>=10, 'Insufficient successful demonstrations.'
    args.out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(args.out/'dataset.npz',observation=np.array(observations,dtype=np.float32),
                        action=np.array(actions,dtype=np.float32),episode_id=np.array(ids),case_index=np.array(case_ids))
    meta = {'robot_xml_sha256':model_hash,'source_report_sha256':hashlib.sha256(args.report.read_bytes()).hexdigest(),
            'filtered_observations':args.filtered,
            'filtered_environment_sha256':hashlib.sha256((search.HERE/'evaluate_filter.py').read_bytes()).hexdigest() if args.filtered else None,
            'filter_header_sha256':hashlib.sha256((search.HERE.parents[1]/'firmware/policy_shadow/GravityFilter.h').read_bytes()).hexdigest() if args.filtered else None,
            'accepted_episodes':episode_id,'frames':len(actions),'attempts':attempts,
            'dataset_sha256':hashlib.sha256((args.out/'dataset.npz').read_bytes()).hexdigest(),
            'status':'Exploratory simulated demonstrations, including uncalibrated parameter randomization; not physical demonstrations',
            'physical_robot_commands_sent':False}
    (args.out/'dataset.json').write_text(json.dumps(meta,indent=2)+'\n')
    print('Dataset:',args.out,'episodes',episode_id,'frames',len(actions),flush=True)


if __name__=='__main__':
    main()
