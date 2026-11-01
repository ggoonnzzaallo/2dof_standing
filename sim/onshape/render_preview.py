"""Render native MuJoCo images and a short simulated joint-motion GIF."""
from pathlib import Path
import sys
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from model_geometry import place_neutral_robot


def main():
    model = mujoco.MjModel.from_xml_path(str(HERE.parent/'robot.xml'))
    data = mujoco.MjData(model)
    place_neutral_robot(model,data,0.,0.)
    option = mujoco.MjvOption()
    font = ImageFont.load_default(size=22)
    panels = []
    frames = []
    with mujoco.Renderer(model,height=720,width=960) as renderer:
        for collision in (False,True):
            option.geomgroup[1] = not collision
            option.geomgroup[3] = collision
            renderer.update_scene(data,camera='overview',scene_option=option)
            panel = Image.fromarray(renderer.render()).resize((640,480))
            panels.append(panel)
        preview = Image.new('RGB',(1280,545),'#f3f5f7')
        draw = ImageDraw.Draw(preview)
        for i,panel in enumerate(panels):
            preview.paste(panel,(i*640,0))
            draw.text((i*640+20,490),'Detailed CAD visuals' if i==0 else 'Convex collision pieces / hardware boxes',font=font,fill='#142c3d')
        draw.text((20,520),'Exploratory model: masses, joint limits and servo dynamics still require physical calibration.',font=ImageFont.load_default(size=17),fill='#455764')
        preview.save(HERE/'preview.png')
        option.geomgroup[1] = 1
        option.geomgroup[3] = 0
        for frame in range(80):
            for _ in range(round(.05/model.opt.timestep)):
                phase = 2*np.pi*.25*data.time
                target = np.deg2rad(25)*np.array([np.sin(phase),.5*np.sin(2*phase)])
                data.ctrl[:] = np.clip(.5*(target-data.qpos[-2:])-.012*data.qvel[-2:],-.07,.07)
                mujoco.mj_step(model,data)
            renderer.update_scene(data,camera='overview',scene_option=option)
            image = Image.fromarray(renderer.render()).resize((640,480))
            draw = ImageDraw.Draw(image)
            draw.rectangle((0,0,640,32),fill='#f3f5f7')
            draw.text((12,6),'MuJoCo joint-motion check (simulation only)',font=ImageFont.load_default(size=17),fill='#142c3d')
            frames.append(image)
        frames[0].save(HERE/'joint_motion.gif',save_all=True,append_images=frames[1:],duration=50,loop=0,optimize=True)
        frames[12].save(HERE/'motion_frame.png')
    print('Rendered preview.png, joint_motion.gif and motion_frame.png',flush=True)


if __name__ == '__main__':
    main()
