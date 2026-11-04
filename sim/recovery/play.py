"""Run the saved neural actor continuously in MuJoCo, with mouse perturbations.

macOS: .venv-sim/bin/mjpython sim/recovery/play.py
Simulation only: no serial ports, firmware uploads or hardware commands.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import queue
import time

os.environ.setdefault('MPLCONFIGDIR', '/tmp/2dof-mpl-cache')
import mujoco
import mujoco.viewer
import numpy as np
import torch
from stable_baselines3 import PPO
import search
from evaluate_filter import FilteredEnv


class Playground:
    """Use the training observation, action integration and servo physics unchanged."""

    def __init__(self, model_path, tilt=0., azimuth=0., randomize=False, filtered=False):
        torch.set_num_threads(1)
        self.actor = PPO.load(model_path, device='cpu')
        self.env = (FilteredEnv if filtered else search.SelfRightingEnv)(randomize=randomize)
        self.start = {'tilt': np.deg2rad(tilt), 'azimuth': np.deg2rad(azimuth)}
        self.reset()

    def reset(self):
        self.observation, _ = self.env.reset(seed=17, options=self.start)
        self.previous_time = self.env.data.time
        self.recovered = False

    def step(self):
        # A GUI reset can change MuJoCo time without resetting command history.
        # Restore the complete environment so policy inputs stay consistent.
        if self.env.data.time < self.previous_time:
            self.reset()
        # Read after viewer.sync: paused mouse manipulation may have changed pose.
        self.observation = self.env._obs()
        action = self.actor.predict(self.observation, deterministic=True)[0]
        self.observation, _, _, _, info = self.env.step(action)
        self.previous_time = self.env.data.time
        if info.get('filter_fault',False):return False
        # Episode success/10 s timeout must not stop control or reset the robot.
        # User perturbations can happen at any time, including after recovery.
        recovered = bool(info['is_success'])
        if recovered and not self.recovered:
            print(f'Upright and stable at simulation t={self.env.data.time:.2f} s; controller stays active.', flush=True)
        self.recovered = recovered
        valid = np.isfinite(self.env.data.qpos).all() and np.isfinite(self.env.data.qvel).all()
        return bool(valid and not any(w.number for w in self.env.data.warning))


def verify_saved_model(path,filtered=False):
    """Reject stale default assets rather than silently playing a different model."""
    report = json.loads((search.HERE/'results/summary.json').read_text())
    if path.resolve() == (search.HERE/'results/policy_simulation_only.zip').resolve():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == report['model_sha256']
        assert hashlib.sha256(search.MODEL_PATH.read_bytes()).hexdigest() == report['robot_xml_sha256']
    elif (path.parent/'training_report.json').exists():
        training=json.loads((path.parent/'training_report.json').read_text())
        assert hashlib.sha256(search.MODEL_PATH.read_bytes()).hexdigest()==training['robot_xml_sha256'], 'Actor and geometry differ'
        assert filtered==training['config'].get('filtered',False), 'Actor and observation pipeline differ'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=search.HERE/'results/policy_simulation_only.zip')
    parser.add_argument('--tilt', type=float, default=0., help='Requested starting tilt in degrees, before 0.8 s settling')
    parser.add_argument('--azimuth', type=float, default=0., help='Horizontal starting rotation-axis angle, degrees')
    parser.add_argument('--randomize', action='store_true', help='Use exploratory parameter/noise randomization')
    parser.add_argument('--filtered', action='store_true', help='Use the firmware gravity filter rather than truth orientation')
    parser.add_argument('--smoke-test', action='store_true', help='Headless continuous-control and applied-force check')
    args = parser.parse_args()
    verify_saved_model(args.model,args.filtered)
    play = Playground(args.model, args.tilt, args.azimuth, args.randomize,args.filtered)
    env = play.env
    if args.smoke_test:
        # Continue past both success and the original 500-frame episode timeout.
        # A brief external lateral force exercises the same xfrc_applied channel
        # as native mouse perturbations, without claiming arbitrary push recovery.
        before = None
        for frame in range(700):
            if frame == 550:
                before = env.data.qpos.copy()
            env.data.xfrc_applied[env.base_id, 0] = .15 if 550 <= frame < 555 else 0.
            assert play.step(), 'Nonfinite state or MuJoCo warning'
            if frame == 554:
                assert np.linalg.norm(env.data.qpos[:3]-before[:3]) > 1e-6, 'Applied force had no effect'
        assert env.steps == 700
        print(json.dumps({'status': 'passed', 'continuous_control_frames': env.steps,
                          'external_force_changed_pose': True,
                          'final_upright_dwell_reached': play.recovered,
                          'mujoco_warning_count': sum(int(w.number) for w in env.data.warning),
                          'physical_robot_commands_sent': False}), flush=True)
        env.close()
        return

    commands = queue.SimpleQueue()
    def on_key(key):
        # The viewer invokes this from its UI thread; mutate physics only below.
        if key in (257, 259):  # GLFW Enter, Backspace
            commands.put('reset')
        elif key == 32:
            commands.put('pause')

    print('NEURAL RECOVERY PLAYGROUND - simulation only', flush=True)
    print('Double-click a robot part, then hold Control + RIGHT-drag to pull it. Release to let it recover.', flush=True)
    print('Control + LEFT-drag applies torque; add Shift to change the drag plane.', flush=True)
    print('Enter/Backspace: reset full robot + controller. Space: pause/resume. Close window: quit.', flush=True)
    print('No automatic episode resets; large disturbances may exceed the current controller\'s capabilities.', flush=True)
    paused = False
    with mujoco.viewer.launch_passive(env.model, env.data, key_callback=on_key,
                                     show_left_ui=False, show_right_ui=False) as viewer:
        with viewer.lock():
            viewer.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
            viewer.cam.trackbodyid = env.base_id
            viewer.cam.distance = .44
            viewer.cam.azimuth = 135
            viewer.cam.elevation = -20
            viewer.opt.geomgroup[1] = 1
            viewer.opt.geomgroup[3] = 0
            viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_PERTFORCE] = 1
        while viewer.is_running():
            start = time.monotonic()
            while not commands.empty():
                command = commands.get()
                if command == 'reset':
                    with viewer.lock():
                        viewer.perturb.active = 0
                    play.reset()
                    print('Reset robot and policy command history.', flush=True)
                elif command == 'pause':
                    paused = not paused
                    print('Paused.' if paused else 'Running.', flush=True)
            # Native viewer sync transfers mouse perturbation forces to mjData.
            # Do not clear xfrc_applied here or inside the servo physics loop.
            viewer.sync()
            if not paused and not play.step():
                paused = True
                print('Sensor or numerical fault: paused. Press Enter to reset, Space to resume.', flush=True)
            time.sleep(max(0., .02-(time.monotonic()-start)))
    env.close()


if __name__ == '__main__':
    main()
