"""Inspect final assembly instances with OpenCascade; preserve Onshape placements."""
from pathlib import Path
import json
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence,TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.TopLoc import TopLoc_Location
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRepCheck import BRepCheck_Analyzer
import hashlib
import math

OUT=Path(__file__).resolve().parent

def name(label):
    attr=TDataStd_Name()
    return attr.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(),attr) else ''

def inspect(source=None):
    source=Path(source) if source else OUT/'source/robot_onshape_corrected.step'
    doc=TDocStd_Document(TCollection_ExtendedString('robot'))
    reader=STEPCAFControl_Reader();reader.SetNameMode(True)
    status=reader.ReadFile(str(source))
    print('Read status',status,flush=True)
    if not reader.Transfer(doc):raise RuntimeError('STEP transfer failed')
    tool=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    roots=TDF_LabelSequence();tool.GetFreeShapes(roots)
    parts=[];shapes=[]
    def walk(label,world,path):
        instance_name=name(label)
        if tool.IsReference_s(label):
            ref=TDF_Label();tool.GetReferredShape_s(label,ref)
            world=world.Multiplied(tool.GetLocation_s(label))
            label=ref
        title=name(label) or instance_name
        components=TDF_LabelSequence()
        if tool.IsAssembly_s(label):
            tool.GetComponents_s(label,components)
            for i in range(1,components.Length()+1):walk(components.Value(i),world,path+[title])
            return
        shape=tool.GetShape_s(label).Moved(world)
        box=Bnd_Box();BRepBndLib.AddOptimal_s(shape,box,False,False)
        cylinders=[];faces=TopExp_Explorer(shape,TopAbs_FACE)
        while faces.More():
            surface=BRepAdaptor_Surface(TopoDS.Face_s(faces.Current()))
            if surface.GetType()==GeomAbs_Cylinder:
                cylinder=surface.Cylinder();point=cylinder.Location();direction=cylinder.Axis().Direction()
                values=[round(v,5) for v in (cylinder.Radius(),point.X(),point.Y(),point.Z(),direction.X(),direction.Y(),direction.Z())]
                if values not in cylinders:cylinders.append(values)
            faces.Next()
        tr=world.Transformation()
        item={'name':title,'instance_name':instance_name,'path':path,'bbox_mm':[round(v,5) for v in box.Get()],
              'transform':[[tr.Value(r,c) for c in range(1,5)] for r in range(1,4)],'cylinders_radius_origin_axis_mm':cylinders,'valid_brep':BRepCheck_Analyzer(shape).IsValid()}
        parts.append(item);shapes.append(shape)
        print(title,item['bbox_mm'],flush=True)
    for i in range(1,roots.Length()+1):walk(roots.Value(i),TopLoc_Location(),[])
    servo_indices=[i for i,p in enumerate(parts) if p['name']=='LOWER SERVO']
    servo_indices.sort(key=lambda i:parts[i]['bbox_mm'][2])
    for i,p in enumerate(parts):
        if i in servo_indices:
            p['alias']='lower_servo' if i==servo_indices[0] else 'upper_servo'
        else:p['alias']=p['name'].lower().replace(',','').replace(' ','_')
        p['rigid_group']='base' if p['name'] in ('BASE','BATTERY','CONTROLLER BOARD') or p['alias']=='lower_servo' else ('upper' if p['name'].startswith('TOP LINK') else 'middle')
    geometry={'units':'mm','grouping_status':'proposed; user review required','parts':{}}
    for p,shape in zip(parts,shapes):
        BRepMesh_IncrementalMesh(shape,0.15,False,0.25,True)
        vertices=[];triangles=[];faces=TopExp_Explorer(shape,TopAbs_FACE)
        while faces.More():
            face=TopoDS.Face_s(faces.Current());location=TopLoc_Location()
            mesh=BRep_Tool.Triangulation_s(face,location)
            if mesh is not None:
                offset=len(vertices);tr=location.Transformation()
                for i in range(1,mesh.NbNodes()+1):
                    point=mesh.Node(i).Transformed(tr)
                    vertices.append([round(point.X(),5),round(point.Y(),5),round(point.Z(),5)])
                for i in range(1,mesh.NbTriangles()+1):
                    indices=list(mesh.Triangle(i).Get())
                    if face.Orientation()==TopAbs_REVERSED:indices[1],indices[2]=indices[2],indices[1]
                    triangles.append([offset+j-1 for j in indices])
            faces.Next()
        geometry['parts'][p['alias']]={'name':p['name'],'group':p['rigid_group'],'vertices':vertices,'triangles':triangles}
        print(p['alias'],len(triangles),'triangles',flush=True)
    by_alias={p['alias']:p for p in parts}
    def unique_cylinder(alias,radius,axis_index):
        matches=[c for c in by_alias[alias]['cylinders_radius_origin_axis_mm']
                 if abs(c[0]-radius)<1e-4 and abs(c[4+axis_index])>0.9999]
        if len(matches)!=1:raise RuntimeError(f'Ambiguous cylinder: {alias}, radius {radius}, {matches}')
        return matches[0]
    lower_structure=unique_cylinder('base',2.5,0)
    upper_structure=unique_cylinder('middle_link_main_body',2.5,1)
    upper_rear=unique_cylinder('top_link_main_body',2.6,1)
    lower_shaft=unique_cylinder('lower_servo',3.,0)
    upper_shaft=unique_cylinder('upper_servo',3.,1)
    geometry['candidate_joints']=[
      {'name':'lower','origin_mm':[0,lower_structure[2],lower_structure[3]],'axis':[1,0,0]},
      {'name':'upper_structural','origin_mm':[upper_structure[1],0,upper_structure[3]],'axis':[0,1,0]},
      {'name':'upper_servo','origin_mm':[upper_shaft[1],0,upper_shaft[3]],'axis':[0,1,0]}]
    def alignment(structure,shaft,axis):
        delta=[shaft[i+1]-structure[i+1] for i in range(3)]
        perpendicular=[0 if i==axis else delta[i] for i in range(3)]
        return {'perpendicular_delta_mm':perpendicular,'distance_mm':math.sqrt(sum(v*v for v in perpendicular))}
    geometry['joint_alignment']={
      'lower':alignment(lower_structure,lower_shaft,0),
      'upper':alignment(upper_structure,upper_shaft,1),
      'upper_structural_pair':alignment(upper_structure,upper_rear,1)}
    geometry['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    (OUT/'geometry.json').write_text(json.dumps(geometry,separators=(',',':'))+'\n')
    (OUT/'assembly_inspection.json').write_text(json.dumps({'units':'mm','source':source.name,'source_sha256':geometry['source_sha256'],'parts':parts},indent=2)+'\n')
    return parts,shapes

if __name__=='__main__':inspect()
