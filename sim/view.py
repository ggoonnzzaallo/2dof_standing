"""Interactive offline MuJoCo review. On macOS run with mjpython, not python."""
from pathlib import Path
import argparse
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
    args = parser.parse_args()
    model = mujoco.MjModel.from_xml_path(str(Path(__file__).with_name('robot.xml')))
    data = mujoco.MjData(model)
    place_neutral_robot(model,data,np.deg2rad(args.tilt),np.deg2rad(args.azimuth))
    with mujoco.viewer.launch_passive(model,data) as viewer:
        viewer.cam.lookat[:] = [0,0,.07]
        viewer.cam.distance = .36
        viewer.cam.azimuth = 135
        viewer.cam.elevation = -20
        viewer.opt.geomgroup[1] = not args.collisions
        viewer.opt.geomgroup[3] = args.collisions
        while viewer.is_running():
            start = time.monotonic()
            for _ in range(round(.02/model.opt.timestep)):
                phase = 2*np.pi*.2*data.time
                target = np.deg2rad(25)*np.array([np.sin(phase),.5*np.sin(2*phase)]) if args.wiggle else np.zeros(2)
                data.ctrl[:] = np.clip(.5*(target-data.qpos[-2:])-.012*data.qvel[-2:],-.07,.07)
                mujoco.mj_step(model,data)
            viewer.sync()
            time.sleep(max(0,.02-(time.monotonic()-start)))


if __name__ == '__main__':
    main()
