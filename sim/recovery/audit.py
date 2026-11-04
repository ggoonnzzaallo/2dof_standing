"""Screen recorded trajectories for adjacent-link overlap hidden by body exclusions.

The audit enables adjacent contacts in a separate, static model. Shaft/bore
mating regions within 6 mm of each hinge line are ignored; outside those regions
overlap deeper than 1 mm is flagged. This is not a proof of physical clearance.
"""
from pathlib import Path
import argparse
import json
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from search import MODEL_PATH

HERE = Path(__file__).resolve().parent


class AdjacentAudit:
    def __init__(self):
        root = ET.parse(MODEL_PATH).getroot()
        compiler=root.find('compiler')
        compiler.set('meshdir',str((MODEL_PATH.parent/compiler.get('meshdir','.')).resolve()))
        contact = root.find('contact')
        for exclusion in list(contact.findall('exclude')):
            contact.remove(exclusion)
        option=root.find('option');flag=option.find('flag')
        if flag is None:flag=ET.SubElement(option,'flag')
        flag.set('filterparent','disable')
        self.model = mujoco.MjModel.from_xml_string(ET.tostring(root,encoding='unicode'))
        self.data = mujoco.MjData(self.model)
        self.pairs = {
            frozenset([self.model.body('base').id,self.model.body('middle').id]):self.model.joint('j1').id,
            frozenset([self.model.body('middle').id,self.model.body('upper').id]):self.model.joint('j2').id,
        }

    def check(self,qpositions):
        deepest = 0.
        flagged = 0
        pairs = {}
        for qpos in qpositions:
            self.data.qpos[:] = qpos
            mujoco.mj_forward(self.model,self.data)
            bad_frame = False
            for contact in self.data.contact:
                pair = frozenset(self.model.geom_bodyid[[contact.geom1,contact.geom2]])
                if pair not in self.pairs or contact.dist>=0:
                    continue
                joint = self.pairs[pair]
                offset = contact.pos-self.data.xanchor[joint]
                axis = self.data.xaxis[joint]
                radial = np.linalg.norm(offset-axis*(offset@axis))
                if radial < .006:
                    continue
                penetration = -float(contact.dist)
                deepest = max(deepest,penetration)
                if penetration>.001:
                    bad_frame = True
                    key = ' / '.join(sorted(self.model.geom(int(i)).name for i in [contact.geom1,contact.geom2]))
                    pairs[key] = max(pairs.get(key,0.),penetration*1000)
            flagged += bad_frame
        return {'status':'passed' if flagged==0 else 'flagged', 'sampled_frames':len(qpositions),
                'mating_region_radius_mm':6.,'overlap_flag_threshold_mm':1.,'flagged_frames':flagged,
                'max_nonmating_penetration_mm':deepest*1000,
                'worst_pairs_mm':dict(sorted(pairs.items(),key=lambda x:-x[1])[:10]),
                'limitation':'Static snapshots at policy rate; ignores pivot mating regions and does not replace calibrated mechanical stops or collision dynamics.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    audit = AdjacentAudit()
    for item in report['results']:
        trace = np.load(args.report.parent/item['trace_file'])
        item['adjacent_collision_audit'] = audit.check(np.vstack([trace['qpos'],trace['final_qpos']]))
        print(item['case'],json.dumps(item['adjacent_collision_audit']),flush=True)
    report['adjacent_collision_audit'] = 'Snapshot screening completed; physical calibration and dynamic contact validation remain pending'
    args.report.write_text(json.dumps(report,indent=2)+'\n')
