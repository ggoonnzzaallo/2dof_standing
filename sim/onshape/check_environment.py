"""Check Gymnasium and finite rollouts without Torch, SB3, training or hardware."""
from pathlib import Path
import hashlib
import json
import sys
import time
import numpy as np
import gymnasium
from gymnasium.utils.env_checker import check_env

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from environment import SelfRightingEnv


def main():
    start = time.monotonic()
    check_env(SelfRightingEnv(randomize=False),skip_render_check=True)
    trials = []
    for randomized in (False,True):
        env = SelfRightingEnv(randomize=randomized)
        env.reset(seed=4)
        env.action_space.seed(4)
        for _ in range(1500):
            observation,reward,terminated,truncated,_ = env.step(env.action_space.sample())
            assert env.observation_space.contains(observation) and np.isfinite(reward)
            assert not any(w.number for w in env.data.warning)
            if terminated or truncated:
                env.reset()
        assert np.isclose(env.physics_dt*env.frame_skip,.02)
        trials.append({'randomize':randomized,'finite_steps':1500})
        env.close()
    report = {
        'status':'passed', 'scope':'Final Onshape exploratory model; no RL training or physical tests',
        'robot_xml_sha256':hashlib.sha256((HERE.parent/'robot.xml').read_bytes()).hexdigest(),
        'gymnasium_version':gymnasium.__version__, 'gymnasium_check':'passed',
        'rollouts':trials, 'policy_period_s':.02, 'physics_timestep_s':env.physics_dt,
        'wall_seconds':time.monotonic()-start, 'rl_training_performed':False,
        'physical_robot_commands_sent':False, 'actor_C_parity':'Not rerun; historical pre-Onshape results preserved in archive/software_validation_before_onshape.json',
    }
    physics = json.loads((HERE/'validation.json').read_text())
    assert physics['status'] == 'passed' and physics['robot_xml_sha256'] == report['robot_xml_sha256'], 'Run check_model.py for this XML first.'
    report['model_validation'] = 'onshape/validation.json'
    (HERE/'environment_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (HERE.parent/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
