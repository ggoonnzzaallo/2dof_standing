"""Exact CAD volume moments, not infill-aware printed masses or measured hardware inertia."""
from pathlib import Path
import json,sys
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
ROOT=Path(__file__).resolve().parents[2]
DENSITY=json.loads((ROOT/'sim/mass_properties/slicer_masses.json').read_text())['filament_density_g_per_cm3']
sys.path.insert(0,str(ROOT/'cad/onshape_import'))
from import_assembly import inspect
parts,shapes=inspect()
records=[]
for part,shape in zip(parts,shapes):
    printed=part['alias'] in ('base','middle_link_main_body','middle_link_servo_horn_bracket','top_link_main_body','top_link_servo_horn_bracket')
    record={'alias':part['alias'],'rigid_group':part['rigid_group'],'printed':printed,'cad_brep_valid':part['valid_brep']}
    if part['valid_brep']:
        props=GProp_GProps();BRepGProp.VolumeProperties_s(shape,props)
        volume=props.Mass();center=props.CentreOfMass();tensor=props.MatrixOfInertia()
        record.update({'cad_volume_mm3':volume,'uniform_solid_centroid_cad_mm':[center.X(),center.Y(),center.Z()],
          'unit_density_inertia_about_centroid_mm5':[[tensor.Value(i,j) for j in range(1,4)] for i in range(1,4)]})
        if printed:record['solid_reference_mass_g']=volume/1000*DENSITY
    else:
        record['note']='Detailed controller BRep invalid; use a simple board envelope for inertia, not this CAD solid.'
    records.append(record)
result={'source_sha256':__import__('hashlib').sha256((ROOT/'cad/onshape_import/source/robot_onshape_third.step').read_bytes()).hexdigest(),
 'coordinate_frame':'exported assembly, mm','wiring_mass':'excluded by user','reference_filament_density_g_per_cm3':DENSITY,
 'density_source':'slicer_masses.json: user-supplied print job filament profile',
 'warning':'Solid PLA figures are reference values, NOT infill-aware print predictions. Use slicer_masses.json for the supplied print job, which specifies PLA Matte at 1.32 g/cm3 and 12 percent infill.',
 'uniform_density_conversion':'For assigned mass m_kg and CAD V_mm3, I_kg_m2 = unit_density_inertia_mm5 * (m_kg/V_mm3) * 1e-6. This preserves uniform-density CAD distribution, which may differ from shell/infill distribution.',
 'parts':records}
(ROOT/'sim/mass_properties/cad_geometric_properties.json').write_text(json.dumps(result,indent=2)+'\n')
for p in records:
 if p['printed']:print(p['alias'],round(p['cad_volume_mm3']/1000,3),'cm3;',round(p['solid_reference_mass_g'],2),'g if solid',flush=True)
