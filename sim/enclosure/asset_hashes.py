"""Fingerprint MJCF plus referenced mesh files; XML hashes alone miss mesh edits."""
from pathlib import Path
import hashlib,json
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
def snapshot(path):
    path=Path(path);xml=ET.parse(path).getroot()
    directory=path.parent/xml.find('compiler').get('meshdir','.')
    files={str((directory/m.get('file')).resolve().relative_to(ROOT)):hashlib.sha256((directory/m.get('file')).read_bytes()).hexdigest() for m in xml.findall('./asset/mesh')}
    bundle=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
    return {'mesh_assets':files,'mesh_assets_sha256':bundle}
if __name__=='__main__':
    here=Path(__file__).resolve().parent;p=here/'model_report.json'
    r=json.loads(p.read_text());r.update(snapshot(here/'robot.xml'));p.write_text(json.dumps(r,indent=2)+'\n')
    print('Recorded',len(r['mesh_assets']),'referenced mesh hashes')
