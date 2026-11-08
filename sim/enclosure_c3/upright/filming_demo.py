"""Repeatable force-driven C3 recovery demonstration. Simulation only.

macOS live: .venv-sim/bin/mjpython sim/enclosure_c3/upright/filming_demo.py
Export:    .venv-sim/bin/python sim/enclosure_c3/upright/filming_demo.py --record build/filming/demo.mp4
"""
from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import queue
import shutil
import subprocess
import sys
import time

import mujoco
import mujoco.viewer
import numpy as np

from robust_env import RobustEnv, HERE
import play as playground

ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from policy_artifact import verify_selection

DT = .02
DURATION_S = 22


@dataclass(frozen=True)
class Push:
    start_s: float
    duration_s: float
    force_n: tuple


# World-frame Newtons, applied at the upper rigid body's center of mass.
# Only these external disturbances are scripted; recovery stays with the policy.
PUSHES = (
    Push(3., .3, (.4, 0., 0.)),
    Push(9., .3, (-.4, 0., 0.)),
    Push(15., .3, (0., .4, 0.)),
)


class ForceDemo:
    def __init__(self):
        manifest = verify_selection()
        if manifest['geometry_id'] != 'installed_c3_upright90':
            raise ValueError('This demo requires the selected C3 upright-90 controller.')
        playground.FilteredEnv = RobustEnv
        self.play = playground.Playground(HERE / 'results/best.zip', filtered=True)
        self.env = self.play.env
        self.body_id = self.env.model.body('upper').id
        self.manifest = manifest
        self.reset()

    def reset(self):
        # Reset the physical state, actor history, IMU/filter, retry memory and RNG.
        self.play.reset()
        self.env.data.xfrc_applied[:] = 0
        self.env.data.qfrc_applied[:] = 0
        self.frame = 0
        self.active_push = None
        self.metrics = [dict(force_world_n=list(p.force_n), start_s=p.start_s,
                             duration_s=p.duration_s, peak_base_tilt_deg=0.,
                             recovery_after_push_s=None) for p in PUSHES]

    @property
    def elapsed(self):
        return self.frame * DT

    @property
    def finished(self):
        return self.frame >= round(DURATION_S / DT)

    def step(self):
        if self.finished:
            return
        self.env.data.xfrc_applied[:] = 0
        self.active_push = None
        for i, push in enumerate(PUSHES):
            first = round(push.start_s / DT)
            if first <= self.frame < first + round(push.duration_s / DT):
                self.env.data.xfrc_applied[self.body_id, :3] = push.force_n
                self.active_push = i
        if not self.play.step():
            self.env.data.xfrc_applied[:] = 0
            raise RuntimeError('Simulation sensor/numerical fault; restart the sequence.')
        self.frame += 1
        tilt = float(np.rad2deg(np.arccos(np.clip(
            self.env.data.xmat[self.env.base_id].reshape(3, 3)[2, 2], -1, 1))))
        for i, push in enumerate(PUSHES):
            end = PUSHES[i + 1].start_s if i + 1 < len(PUSHES) else DURATION_S
            if push.start_s < self.elapsed <= end:
                metric = self.metrics[i]
                metric['peak_base_tilt_deg'] = max(metric['peak_base_tilt_deg'], tilt)
                # Require a genuine fall before recognizing a subsequent recovery.
                if (metric['peak_base_tilt_deg'] > 60 and self.play.recovered
                        and metric['recovery_after_push_s'] is None):
                    metric['recovery_after_push_s'] = self.elapsed - push.start_s
        if self.finished:
            self.env.data.xfrc_applied[:] = 0
            self.active_push = None

    def close(self):
        self.env.data.xfrc_applied[:] = 0
        self.env.close()

    def report(self):
        return dict(duration_s=DURATION_S, controller='0.9', seed=17,
                    randomized_mechanics=False, force_body='upper',
                    force_application='upper body center of mass; world coordinates',
                    pushes=self.metrics, final_upright_and_straight=self.play.recovered,
                    actor_sha256=self.manifest['actor_archive_sha256'],
                    model_sha256=self.manifest['model_sha256'],
                    physical_robot_commands_sent=False)


def arrow(scene, demo, enabled=True):
    """Draw the applied force toward its application point; no physics changes."""
    if demo.active_push is None or not enabled:
        return
    force = np.asarray(PUSHES[demo.active_push].force_n)
    end = demo.env.data.xipos[demo.body_id].copy()
    start = end - .08 * force / np.linalg.norm(force)
    geom = scene.geoms[scene.ngeom]
    mujoco.mjv_initGeom(geom, mujoco.mjtGeom.mjGEOM_ARROW, np.zeros(3),
                       np.zeros(3), np.eye(3).ravel(),
                       np.array([1., .3, .04, 1.], dtype=np.float32))
    mujoco.mjv_connector(geom, mujoco.mjtGeom.mjGEOM_ARROW, .003, start, end)
    scene.ngeom += 1


def configure_camera(camera, demo):
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.distance = .40
    camera.azimuth = 135
    camera.elevation = -18
    follow_base(camera, demo)


def follow_base(camera, demo):
    # Follow translation, retaining the user's orbit/zoom across restarts.
    camera.lookat[:] = demo.env.data.xpos[demo.env.base_id] + np.array([0., 0., .06])


def configure_visuals(option):
    option.geomgroup[1] = 1
    option.geomgroup[3] = 0
    option.flags[mujoco.mjtVisFlag.mjVIS_PERTFORCE] = 0


def run_live(demo, show_arrows):
    commands = queue.SimpleQueue()

    def on_key(key):
        if key in (82, 257, 259):  # R, Enter, Backspace
            commands.put('restart')
        elif key == 32:
            commands.put('pause')

    print('FILMING DEMO — C3 / controller 0.9 — simulation only', flush=True)
    print('READY / PAUSED. Frame the camera, start your recording, then press R.', flush=True)
    print('R / Enter / Backspace: restart and play all 22 seconds. Space: pause/resume.', flush=True)
    print('Pushes at 3, 9 and 15 seconds. Ends paused; never secretly resets between pushes.', flush=True)
    paused = True
    with mujoco.viewer.launch_passive(demo.env.model, demo.env.data,
                                     key_callback=on_key, show_left_ui=False,
                                     show_right_ui=False) as viewer:
        with viewer.lock():
            configure_camera(viewer.cam, demo)
            configure_visuals(viewer.opt)
        while viewer.is_running():
            start = time.monotonic()
            while not commands.empty():
                command = commands.get()
                if command == 'restart':
                    with viewer.lock():
                        viewer.perturb.active = 0
                        demo.reset()
                    paused = False
                    print('Restarted: upright, 3-second lead-in, then three pushes.', flush=True)
                elif not demo.finished:
                    paused = not paused
                    print('Paused.' if paused else 'Playing.', flush=True)
            viewer.sync()
            if not paused:
                try:
                    with viewer.lock():
                        demo.step()
                    if demo.finished:
                        paused = True
                        print('Sequence complete. R replays from the start.', flush=True)
                except RuntimeError as error:
                    paused = True
                    print(str(error), flush=True)
            with viewer.lock():
                viewer.perturb.active = 0
                follow_base(viewer.cam, demo)
                viewer.user_scn.ngeom = 0
                arrow(viewer.user_scn, demo, show_arrows)
            viewer.sync()
            time.sleep(max(0., DT - (time.monotonic() - start)))


def check_repeatability(demo, output):
    traces = []
    reports = []
    for repeat in range(2):
        if repeat:
            demo.reset()
            for _ in range(round(PUSHES[0].start_s / DT) + 4):
                demo.step()
            assert np.any(demo.env.data.xfrc_applied), 'Expected an active push before reset'
        demo.reset()
        assert not np.any(demo.env.data.xfrc_applied), 'Reset retained an external force'
        trace = []
        while not demo.finished:
            demo.step()
            trace.append(np.r_[demo.env.data.qpos, demo.env.data.qvel, demo.env.command,
                               demo.env.runtime.down, demo.env.strategy.retries])
        assert all(p['peak_base_tilt_deg'] > 60 and p['recovery_after_push_s'] is not None
                   for p in demo.metrics), demo.metrics
        assert demo.play.recovered, 'Not upright and straight at the end'
        assert not np.any(demo.env.data.xfrc_applied), 'Force left on after completion'
        traces.append(np.array(trace))
        reports.append(demo.report())
    difference = float(np.max(np.abs(traces[0] - traces[1])))
    assert difference < 1e-10, difference
    result = dict(status='passed', maximum_restart_trace_difference=difference,
                  restart_during_active_push_checked=True, repeats=reports)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


def record(demo, output, width, height, show_arrows):
    if not shutil.which('ffmpeg'):
        raise ValueError('MP4 export requires ffmpeg on PATH.')
    if output.exists():
        raise ValueError(f'Refusing to overwrite {output}; choose a new filename.')
    output.parent.mkdir(parents=True, exist_ok=True)
    command = ['ffmpeg', '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', f'{width}x{height}', '-r', '50', '-i', '-', '-an',
               '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
               '-movflags', '+faststart', str(output)]
    demo.env.model.vis.global_.offwidth = max(width, demo.env.model.vis.global_.offwidth)
    demo.env.model.vis.global_.offheight = max(height, demo.env.model.vis.global_.offheight)
    camera = mujoco.MjvCamera()
    configure_camera(camera, demo)
    option = mujoco.MjvOption()
    configure_visuals(option)
    demo.reset()
    renderer = mujoco.Renderer(demo.env.model, width=width, height=height)
    try:
        with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
            try:
                while not demo.finished:
                    demo.step()
                    follow_base(camera, demo)
                    renderer.update_scene(demo.env.data, camera=camera, scene_option=option)
                    arrow(renderer.scene, demo, show_arrows)
                    encoder.stdin.write(renderer.render().tobytes())
                    if demo.frame % 250 == 0:
                        print(f'Rendered {demo.elapsed:.0f}/{DURATION_S} seconds.', flush=True)
            finally:
                encoder.stdin.close()
            if encoder.wait() != 0:
                raise RuntimeError('Video encoder failed.')
    finally:
        renderer.close()
    output.with_suffix('.json').write_text(json.dumps(demo.report(), indent=2) + '\n')
    print(f'Saved {output}: {width} × {height}, 50 fps, {DURATION_S} seconds.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Headless two-replay physics check')
    mode.add_argument('--record', type=Path, help='Export a portrait MP4 without screen recording')
    parser.add_argument('--report', type=Path, default=ROOT / 'build/filming/demo_validation.json')
    parser.add_argument('--width', type=int, default=1080)
    parser.add_argument('--height', type=int, default=1920)
    parser.add_argument('--no-arrows', action='store_true')
    args = parser.parse_args()
    if min(args.width, args.height) <= 0 or args.width % 2 or args.height % 2:
        parser.error('Video dimensions must be positive even integers.')
    demo = ForceDemo()
    try:
        if args.check:
            check_repeatability(demo, args.report)
        elif args.record:
            record(demo, args.record, args.width, args.height, not args.no_arrows)
        else:
            run_live(demo, not args.no_arrows)
    finally:
        demo.close()


if __name__ == '__main__':
    main()
