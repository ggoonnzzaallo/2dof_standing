"""Replay saved C2 plans in C3 physics; never relabel old traces as new data."""
from pathlib import Path
import hashlib,json,os,sys
HERE=Path(__file__).resolve().parent
os.environ['ROBOT_MODEL_PATH']=str(HERE/'robot.xml')
sys.path.insert(0,str(HERE.parent/'recovery'))
import numpy as np
import search
from audit import AdjacentAudit

def main():
    source=HERE.parent/'enclosure/results/search/report.json'
    old=json.loads(source.read_text());out=HERE/'waypoint_checks';out.mkdir(exist_ok=True)
    search.initialize();audit=AdjacentAudit();rows=[]
    for item in old['results']:
        task=(item['case'],17,np.array(item['waypoints_rad']),old['config']['segment'],old['config']['hold'])
        result,trace=search.rollout(task,record=True)
        check=audit.check(np.vstack([trace['qpos'],trace['final_qpos']]))
        np.savez_compressed(out/f"{item['case']}.npz",**trace)
        rows.append({'case':item['case'],'requested_start':search.CASES[item['case']],
                     'result':result,'waypoints_rad':item['waypoints_rad'],
                     'adjacent_collision_audit':check,'trace_file':f"{item['case']}.npz"})
        print(item['case'],result['success'],check['status'],flush=True)
    r={'method':'C2 waypoint plans freshly replayed in C3 dynamics, no new search optimization',
       'source_report_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
       'robot_xml_sha256':hashlib.sha256((HERE/'robot.xml').read_bytes()).hexdigest(),
       'config':{**old['config'],'out':str(out)},'results':rows,'physical_robot_commands_sent':False}
    (out/'report.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
