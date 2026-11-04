"""Render recorded simulator trajectories; no physical motion or serial access."""
from pathlib import Path
import argparse
import json
import hashlib
import mujoco
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from search import MODEL_PATH

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--cases',nargs='+',default=['side_000','inverted'])
    parser.add_argument('--out',type=Path,default=Path('sim/recovery/results/searched_recovery.gif'))
    parser.add_argument('--title',default='Searched recovery motions / simulation only; starts shown after settling')
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    assert report['robot_xml_sha256']==hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest(), 'Replay and geometry differ'
    traces = [np.load(args.report.parent/next(x['trace_file'] for x in report['results'] if x['case']==case)) for case in args.cases]
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    camera = mujoco.MjvCamera();camera.type=mujoco.mjtCamera.mjCAMERA_FREE
    camera.distance=.40;camera.elevation=-22;camera.azimuth=135
    frames = []
    with mujoco.Renderer(model,height=480,width=640) as renderer:
        for step in range(0,max(len(t['qpos']) for t in traces)+15,3):
            frame = Image.new('RGB',(480*len(traces),395),'#f3f5f7')
            draw = ImageDraw.Draw(frame)
            for panel,(case,trace) in enumerate(zip(args.cases,traces)):
                data.qpos[:] = trace['qpos'][step] if step<len(trace['qpos']) else trace['final_qpos']
                mujoco.mj_forward(model,data)
                camera.lookat[:] = [*np.median(trace['qpos'][:,:2],axis=0),.065]
                renderer.update_scene(data,camera=camera)
                image = Image.fromarray(renderer.render()).resize((480,360))
                frame.paste(image,(480*panel,0))
                draw.text((480*panel+10,365),f"{case}: {min(step,len(trace['qpos']))*.02:.1f} s",font=ImageFont.load_default(size=16),fill='#142c3d')
            draw.rectangle((0,0,frame.width,29),fill='#f3f5f7')
            draw.text((10,5),args.title,font=ImageFont.load_default(size=17),fill='#142c3d')
            frames.append(frame)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    frames[0].save(args.out,save_all=True,append_images=frames[1:],duration=60,loop=0,optimize=True)
    frames[min(10,len(frames)-1)].save(args.out.with_suffix('.png'))
    print('Rendered',args.out,flush=True)


if __name__=='__main__':
    main()
