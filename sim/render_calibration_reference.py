"""Kinematic +/-45-degree reference images; no hardware access or dynamics."""
from pathlib import Path
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
model = mujoco.MjModel.from_xml_path(str(ROOT / 'sim/robot.xml'))
data = mujoco.MjData(model)
option = mujoco.MjvOption()
option.geomgroup[1] = 1
option.geomgroup[3] = 0
camera = mujoco.MjvCamera()
camera.type = mujoco.mjtCamera.mjCAMERA_FREE
camera.distance = .29
camera.elevation = -8
camera.lookat[:] = [0, 0, .07]
font = ImageFont.load_default(size=18)
small = ImageFont.load_default(size=15)
canvas = Image.new('RGB', (1260, 835), '#f3f5f7')
draw = ImageDraw.Draw(canvas)
draw.text((18, 10), 'Joint angle references: CAD signs, not calibrated PWM signs', font=font, fill='#152c3b')
with mujoco.Renderer(model, height=360, width=420) as renderer:
    for row, joint in enumerate(['lower', 'upper']):
        for column, angle in enumerate([-45, 0, 45]):
            mujoco.mj_resetData(model, data)
            data.qpos[:3] = [0, 0, .004]
            data.qpos[-2 + row] = np.deg2rad(angle)
            mujoco.mj_forward(model, data)
            camera.azimuth = 180 if joint == 'lower' else 90
            renderer.update_scene(data, camera=camera, scene_option=option)
            canvas.paste(Image.fromarray(renderer.render()), (column * 420, 40 + row * 385))
            draw.text((column * 420 + 12, 378 + row * 385), f'{joint}: {angle:+d} deg' if angle else f'{joint}: straight / 0 deg', font=font, fill='#152c3b')
draw.text((18, 813), 'Angle is relative to the parent link. Match the viewing side; opposite-side views reverse left/right.', font=small, fill='#405361')
out = ROOT / 'firmware/servo_calibration/angle_reference.png'
canvas.save(out)
print(out)
