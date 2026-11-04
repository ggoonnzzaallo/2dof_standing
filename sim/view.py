"""Interactive offline MuJoCo review. On macOS run with mjpython, not python."""
from pathlib import Path
import argparse
import queue
import time
import mujoco
import mujoco.viewer
import numpy as np
from model_geometry import place_neutral_robot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wiggle', action='store_true', help='Slow ±25-degree target motion in simulation')
    parser.add_argument('--collisions', action='store_true', help='Show collision shapes instead of detailed visuals')
    parser.add_argument('--tilt', type=float, default=0, help='Initial base tilt, degrees')
    parser.add_argument('--azimuth', type=float, default=0, help='Horizontal tilt-axis angle, degrees')
    parser.add_argument('--model', type=Path, default=Path(__file__).with_name('robot.xml'), help='MJCF model to review')
    parser.add_argument('--manual', action='store_true', help='Arrow keys adjust joint targets by 5 degrees; Enter centers both')
    args = parser.parse_args()
    model = mujoco.MjModel.from_xml_path(str(args.model))
    data = mujoco.MjData(model)
    place_neutral_robot(model,data,np.deg2rad(args.tilt),np.deg2rad(args.azimuth))
    commands=queue.SimpleQueue()
    def on_key(key):
        if args.manual: commands.put(key)
    target=np.zeros(2)
    if args.manual:
        print('Simulation only. Left/right: lower joint; down/up: upper joint; Enter: center. Each press is 5 degrees.',flush=True)
    with mujoco.viewer.launch_passive(model,data,key_callback=on_key) as viewer:
        viewer.cam.lookat[:] = [0,0,.07]
        viewer.cam.distance = .36
        viewer.cam.azimuth = 135
        viewer.cam.elevation = -20
        viewer.opt.geomgroup[1] = not args.collisions
        viewer.opt.geomgroup[3] = args.collisions
        while viewer.is_running():
            start = time.monotonic()
            while not commands.empty():
                key=commands.get()
                if key in (262,263): target[0]+=np.deg2rad(5)*(1 if key==262 else -1)
                elif key in (264,265): target[1]+=np.deg2rad(5)*(1 if key==265 else -1)
                elif key==257: target[:]=0
                target[:]=np.clip(target,model.jnt_range[-2:,0],model.jnt_range[-2:,1])
                print('Joint targets (deg):',np.round(np.rad2deg(target),1),flush=True)
            for _ in range(round(.02/model.opt.timestep)):
                phase = 2*np.pi*.2*data.time
                if not args.manual:
                    target = np.deg2rad(25)*np.array([np.sin(phase),.5*np.sin(2*phase)]) if args.wiggle else np.zeros(2)
                data.ctrl[:] = np.clip(.5*(target-data.qpos[-2:])-.012*data.qvel[-2:],-.07,.07)
                mujoco.mj_step(model,data)
            viewer.sync()
            time.sleep(max(0,.02-(time.monotonic()-start)))


if __name__ == '__main__':
    main()
