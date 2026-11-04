"""Build an enclosure-model variant without changing the deployed policy's model.

Uses fit-approved Rev C2 CAD. No serial ports, uploads or hardware commands.
"""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import cadquery as cq
import coacd
import numpy as np
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'sim/onshape'))
from build_model import aggregate,numbers
from prepare_assets import write_obj,PARAMETERS
sys.path.insert(0,str(ROOT/'cad/electronics_pod'))
from build_pod import rounded_xy
POD=ROOT/'cad/electronics_pod'
POD_CAD=HERE/'source/fit_approved_c2'

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def properties(shape,mass_g,alias,status):
    p=GProp_GProps();BRepGProp.VolumeProperties_s(shape.wrapped,p)
    c=p.CentreOfMass();t=p.MatrixOfInertia();m=mass_g/1000
    return {'alias':alias,'group':'base','mass_kg':m,'com_cad_m':[c.X()/1000,c.Y()/1000,c.Z()/1000],
        'inertia_com_cad_kg_m2':(np.array([[t.Value(i,j) for j in range(1,4)] for i in range(1,4)])*m/p.Mass()*1e-6).tolist(),
        'source':status,'distribution':'Uniform CAD solid scaled to assigned mass; shell/infill unresolved'}

def mesh_arrays(part):
    v=np.asarray(part['vertices'],float)/1000;f=np.asarray(part['triangles'],np.int32)
    v,inv=np.unique(np.round(v,10),axis=0,return_inverse=True);f=inv[f]
    t=v[f];f=f[np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)>1e-18]
    return v,f

def main():
    config=json.loads((HERE/'configuration.json').read_text())
    geometry=json.loads((POD_CAD/'geometry.json').read_text())
    params=geometry['parameters']
    old=json.loads((ROOT/'sim/onshape/body_properties.json').read_text())
    tree=ET.parse(ROOT/'sim/robot.xml');xml=tree.getroot()
    xml.set('model','self_righting_enclosure_c2_provisional')
    xml.find('compiler').set('meshdir','..')
    assets=xml.find('asset');base=xml.find(".//body[@name='base']")
    for a in assets:
        if a.tag=='mesh': a.set('file','onshape/assets/'+a.get('file'))
    remove={'base','battery','controller_board'}
    for g in list(base.findall('geom')):
        if any(g.get('name').startswith(a+'_') for a in remove): base.remove(g)
    for m in list(assets):
        if any(m.get('name','').startswith(a+'_') for a in remove): assets.remove(m)
    components=[p for p in old['component_masses'] if p['alias'] not in remove]
    for alias in ('electronics_cup','base_modified'):
        shape=cq.importers.importStep(str(POD_CAD/(alias+'.step'))).val()
        mass=config['printed_mass_g'][alias]
        status=config.get('printed_mass_source','User mass') if mass is not None else 'PROVISIONAL full-solid PLA reference; replace with new slicer or scale mass'
        if mass is None:mass=shape.Volume()*.00132
        components.append(properties(shape,mass,alias,status))
    for alias,translation in [('battery',np.array(params['battery_center'])-[-.21532,20.71208,5.75]),
                              ('controller_board',params['board_translation'])]:
        item=dict(next(p for p in old['component_masses'] if p['alias']==alias))
        item['com_cad_m']=(np.array(item['com_cad_m'])+np.array(translation)/1000).tolist()
        item['source']+='; translated into fit-approved cup, orientation retained'
        components.append(item)
    pololu=cq.importers.importStep(str(POD/'source/pololu_2810.step')).val().translate(tuple(params['pololu_translation']))
    components.append(properties(pololu,.6,'pololu_2810_master_switch','Pololu 2810 manufacturer nominal 0.6 g; no extra wire mass'))
    groups={g:aggregate([p for p in components if p['group']==g]) for g in ('base','middle','upper')}
    for group,p in groups.items():
        body=xml.find(f".//body[@name='{group}']");inertial=body.find('inertial')
        origin=np.array(old['body_frame_origins_cad_mm'][group])/1000
        tensor=np.array(p['inertia_com_cad_kg_m2'])
        inertial.set('pos',numbers(np.array(p['com_cad_m'])-origin));inertial.set('mass',str(p['mass_kg']))
        inertial.set('fullinertia',numbers(tensor[([0,1,2,0,0,1],[0,1,2,1,2,2])]))
    height=.013 # bottom CAD Z=-12 mm, 1 mm initial clearance
    base.set('pos',numbers([0,0,height]));xml.find('.//keyframe/key').set('qpos',numbers([0,0,height,1,0,0,0,0,0]))
    board=next(p for p in components if p['alias']=='controller_board')
    base.find("site[@name='imu']").set('pos',numbers(board['com_cad_m']))
    provenance={'original_model_sha256':digest(ROOT/'sim/robot.xml'),'pod_geometry_sha256':digest(POD_CAD/'geometry.json'),
        'configuration_sha256':digest(HERE/'configuration.json'),'date':'2026-11-03',
        'fit_check':'User reports new cup and lid pass physical fit',
        'imu_mount':'CAD orientation retained; physical confirmation pending' if not config['imu_orientation_confirmed'] else 'User confirmed CAD orientation',
        'parts':{}}
    coacd.set_log_level('warn')
    for alias in ('base_modified','electronics_cup','battery','controller_board','pololu_2810_master_switch'):
        v,f=mesh_arrays(geometry['parts'][alias]);visual=alias+'_visual'
        write_obj(HERE/'assets'/(visual+'.obj'),v,f)
        ET.SubElement(assets,'mesh',name=visual,file='enclosure/assets/'+visual+'.obj')
        color=geometry['parts'][alias]['color']+[1]
        ET.SubElement(base,'geom',name=visual,type='mesh',mesh=visual,group='1',contype='0',conaffinity='0',mass='0',rgba=numbers(color))
        if alias=='base_modified':
            key=hashlib.sha256(v.tobytes()+f.tobytes()+json.dumps(PARAMETERS,sort_keys=True).encode()).hexdigest()
            cache=HERE/'assets/lid_hulls.json'
            if cache.exists() and json.loads(cache.read_text())['key']==key:
                hulls=json.loads(cache.read_text())['hulls']
            else:
                print('Decomposing revised lid / servo frame...',flush=True)
                hulls=[(a.tolist(),b.tolist()) for a,b in coacd.run_coacd(coacd.Mesh(v,f),**{**PARAMETERS,'preprocess_mode':'off'})]
                cache.write_text(json.dumps({'key':key,'hulls':hulls})+'\n')
            method='Separate convex pieces of revised lid and retained servo frame'
        elif alias=='electronics_cup':
            # Closed electronics volume has no moving parts. Its convex exterior
            # preserves the R5 side corners and R1 ground edge, avoids tiny internal
            # screw/PSA features in physics. USB/slider openings are filled here.
            outer=rounded_xy(70,70,12,-12,5).edges('<Z').fillet(params['ground_edge_radius']).val()
            vv,ff=outer.tessellate(.04,.15)
            hulls=[(np.array([[p.x,p.y,p.z] for p in vv])/1000,np.asarray(ff))]
            method='Closed convex external cup envelope, R1 bottom/R5 side corners; ports and internal cavities omitted'
        else:
            hulls=[];method='Internal fixed electronics: visual and inertia only, enclosed by cup/lid'
        names=[]
        for i,(a,b) in enumerate(hulls):
            name=f'{alias}_collision_{i:02d}';names.append(name)
            write_obj(HERE/'assets'/(name+'.obj'),a,b)
            ET.SubElement(assets,'mesh',name=name,file='enclosure/assets/'+name+'.obj')
            ET.SubElement(base,'geom',name=name,type='mesh',mesh=name,group='3',mass='0',rgba='.25 .49 .54 1')
        provenance['parts'][alias]={'collision_geoms':names,'collision_method':method,'bbox_cad_m':[v.min(axis=0).tolist(),v.max(axis=0).tolist()]}
    # Inspect full adjacent contacts before selecting any narrowly scoped mating
    # exclusions. Never inherit the old whole-body collision exclusions silently.
    contact=xml.find('contact')
    for exclusion in list(contact.findall('exclude')):contact.remove(exclusion)
    option=xml.find('option');flag=option.find('flag')
    if flag is None:flag=ET.SubElement(option,'flag')
    flag.set('filterparent','disable')
    ET.indent(tree,space='  ');tree.write(HERE/'robot.xml',encoding='unicode')
    from configure_contacts import configure
    policy=configure(HERE/'robot.xml')
    provenance['adjacent_contacts']='Enabled with per-convex-piece pivot sleeve masks; no whole-body exclusions'
    report={**provenance,'component_masses':components,'groups':groups,'whole_upright':aggregate(components),
        'body_frame_origins_cad_mm':old['body_frame_origins_cad_mm'],'imu_site_cad_m':board['com_cad_m'],
        'robot_xml_sha256':digest(HERE/'robot.xml'),'mass_status':config.get('printed_mass_source','Provisional printed masses until supplied'),
        'slicer_source_sha256':digest(HERE/'source/enclosure_print.gcode.3mf'),
        'pivot_sleeve_piece_count':len(policy['excluded_pieces']),
        'historical_model_preserved':True,'physical_robot_commands_sent':False}
    from asset_hashes import snapshot
    report.update(snapshot(HERE/'robot.xml'))
    (HERE/'model_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"Built {HERE/'robot.xml'}; mass {report['whole_upright']['mass_kg']*1000:.3f} g",flush=True)

if __name__=='__main__':main()
