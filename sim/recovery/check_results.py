"""Verify saved experiment artifacts and their provenance without running training."""
from pathlib import Path
import hashlib
import json
import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS = HERE/'results'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    summary = json.loads((RESULTS/'summary.json').read_text())
    training = json.loads((RESULTS/'training_report.json').read_text())
    broad = json.loads((RESULTS/'broad_evaluation.json').read_text())
    exported = json.loads((RESULTS/'policy_simulation_only.json').read_text())
    demos = json.loads((RESULTS/'demonstrations.json').read_text())
    data = np.load(RESULTS/'demonstrations.npz')
    assert summary['robot_xml_sha256']==training['robot_xml_sha256']==broad['robot_xml_sha256']==sha(HERE.parent/'robot.xml')
    assert summary['model_sha256']==broad['model_sha256']==exported['model_sha256']==sha(RESULTS/'policy_simulation_only.zip')
    assert exported['actor_header_sha256']==sha(RESULTS/'policy_simulation_only.h')
    assert demos['dataset_sha256']==training['dataset_sha256']==sha(RESULTS/'demonstrations.npz')
    assert demos['source_report_sha256']==sha(RESULTS/'trajectory_search.json')
    assert data['observation'].shape==(demos['frames'],10) and data['action'].shape==(demos['frames'],2)
    assert len(np.unique(data['episode_id']))==demos['accepted_episodes']
    assert np.isfinite(data['observation']).all() and np.isfinite(data['action']).all()
    assert np.max(np.abs(data['observation']))<=1 and np.max(np.abs(data['action']))<=1
    assert sum(t['success'] for t in broad['trials'])==broad['successes']==summary['broad_randomized_successes']
    assert len(broad['trials'])==broad['episodes']==summary['broad_randomized_episodes']
    assert sum(t['success'] and t['adjacent_audit']['status']=='passed' for t in broad['trials'])==broad['successful_and_audit_passed']==summary['broad_successes_with_snapshot_audit_passed']
    times = [t['seconds'] for t in broad['trials'] if t['success']]
    assert np.isclose(np.median(times),summary['broad_median_control_time_s'])
    assert np.isclose(max(times),summary['broad_max_control_time_s'])
    held_out = training['held_out_test']
    assert sum(t['success'] for t in held_out['trials'])==held_out['successes']==summary['held_out_scripted_case_successes']
    assert len(held_out['trials'])==held_out['episodes']==summary['held_out_scripted_case_episodes']
    assert not any(t['mujoco_warning_count'] for t in broad['trials'])
    selected = next(s for s in training['stages'] if s['ppo_steps_actual']==training['selected_ppo_steps'])
    assert selected['nominal']['successes']==summary['nominal_successes']
    assert selected['development']['successes']==summary['development_successes']
    assert training['selected_ppo_steps']==summary['selected_checkpoint_ppo_steps']==0
    assert exported['host_C_max_absolute_error']<1e-5 and exported['actor_parameters']==4994
    assert not exported['firmware_uploaded'] and not summary['physical_robot_commands_sent']
    report = {'status':'passed','dataset_frames':demos['frames'],'dataset_episodes':demos['accepted_episodes'],
              'model_and_dataset_hashes':'matched','finite_bounded_observation_action_arrays':'passed',
              'metrics_recomputed_from_trial_records':'passed','no_mujoco_warnings_in_broad_test':True,
              'actor_export_host_parity':'passed','physical_robot_commands_sent':False}
    (RESULTS/'artifact_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
