"""Create a self-contained, read-only assembly/joint review from imported STEP meshes."""
from pathlib import Path
import json
import argparse
import html as html_module
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--enclosure',action='store_true',help='Review fit-approved cup/lid with unchanged serial axes')
args=parser.parse_args()
geometry=json.loads((ROOT/'geometry.json').read_text())
if args.enclosure:
    pod=json.loads((ROOT.parent/'electronics_pod/geometry.json').read_text())
    original=geometry['parts']
    geometry['parts']={k:{**v,'group':original[k]['group'] if k in original else 'base'} for k,v in pod['parts'].items() if k!='existing_connectors_envelope'}
alignment=geometry['joint_alignment']['upper']
upper=geometry['candidate_joints'][1]['origin_mm']
shaft=geometry['candidate_joints'][2]['origin_mm']
note=f"Upper servo model remains {alignment['distance_mm']:.2f} mm off the confirmed structural axis (+{alignment['perpendicular_delta_mm'][0]:.2f} mm X, +{alignment['perpendicular_delta_mm'][2]:.2f} mm Z)."
html=r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Final Onshape assembly — joint review</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f6f8;color:#172b3b;font:15px system-ui}main{height:100dvh;display:flex;flex-direction:column}header{padding:14px 18px;background:white}h1{font-size:19px;margin:0 0 8px}p{margin:6px 0}.row{display:flex;flex-wrap:wrap;gap:14px;align-items:center}.note{color:#963e23;font-size:14px}canvas{flex:1;width:100%;min-height:220px;touch-action:none;cursor:grab}button{padding:6px 10px;background:#edf2f6;border:1px solid #acbac6;border-radius:5px}input[type=range]{width:120px;vertical-align:middle}footer{padding:8px 18px;background:white;font-size:12px;color:#4b6171}b.blue{color:#2876b8}b.orange{color:#b76a13}b.purple{color:#8255ad}
</style><main><header><h1>Final Onshape assembly · proposed rigid groups</h1><p class="row"><label><input type="checkbox" id="base" checked><b class="blue">Base</b></label><label><input type="checkbox" id="middle" checked><b class="orange">Middle</b></label><label><input type="checkbox" id="upper" checked><b class="purple">Upper</b></label><button id="reset">Reset</button><span>Drag to orbit · scroll to zoom</span></p><div class="row"><label>Lower preview <input id="q1" type="range" min="-35" max="35" value="0"><output id="a1">0°</output></label><label>Upper preview <input id="q2" type="range" min="-35" max="35" value="0"><output id="a2">0°</output></label></div><p class="note">Review only: axes, signs and travel limits are unconfirmed. Black: structural axes. Red: upper servo shaft. __ALIGNMENT_NOTE__</p></header><canvas id="view"></canvas><footer>Exact imported placements; no alignment correction applied. Lower pivot Z=24.40 mm; upper structural pivot Z=__STRUCT_Z__ mm; upper servo shaft Z=__SHAFT_Z__ mm. Coordinates are in the exported CAD frame.</footer></main><script>
const data=__DATA__;
const canvas=document.getElementById('view'),gl=canvas.getContext('webgl',{antialias:true});
if(!gl)throw Error('WebGL unavailable');
const vs=`attribute vec3 pos,normal,color;uniform float yaw,pitch,zoom,aspect,q1,q2,group;varying vec3 shade;
mat3 rx(float a){float c=cos(a),s=sin(a);return mat3(1.,0.,0.,0.,c,s,0.,-s,c);}mat3 ry(float a){float c=cos(a),s=sin(a);return mat3(c,0.,-s,0.,1.,0.,s,0.,c);}mat3 rz(float a){float c=cos(a),s=sin(a);return mat3(c,s,0.,-s,c,0.,0.,0.,1.);}
void main(){vec3 p=pos,n=normal;if(group>1.5){p=ry(q2)*(p-vec3(-2.35,0.,61.4))+vec3(-2.35,0.,61.4);n=ry(q2)*n;}if(group>.5){p=rx(q1)*(p-vec3(0.,0.,24.4))+vec3(0.,0.,24.4);n=rx(q1)*n;}p=(p-vec3(0.,0.,74.5))/80.;mat3 view=rx(pitch)*rz(yaw);p=view*p;n=view*n;float light=.58+.42*abs(dot(normalize(n),normalize(vec3(.3,-.6,.75))));shade=color*light;gl_Position=vec4(p.x/(zoom*aspect),p.z/zoom,-p.y/zoom,1.);}`;
const fs=`precision mediump float;varying vec3 shade;void main(){gl_FragColor=vec4(shade,1.);}`;
function shader(kind,src){let s=gl.createShader(kind);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
let program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vs));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);
const attrs={},uniforms={};for(let k of ['pos','normal','color'])attrs[k]=gl.getAttribLocation(program,k);for(let k of ['yaw','pitch','zoom','aspect','q1','q2','group'])uniforms[k]=gl.getUniformLocation(program,k);
const colors={base:[.21,.53,.78],middle:[.91,.57,.20],upper:[.61,.39,.79]},groups={base:0,middle:1,upper:2},meshes=[];
function add(flat,group,mode){let buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(flat),gl.STATIC_DRAW);meshes.push({buffer,group,mode,count:flat.length/9});}
for(let part of Object.values(data.parts)){let flat=[];for(let tri of part.triangles){let a=part.vertices[tri[0]],b=part.vertices[tri[1]],c=part.vertices[tri[2]],u=b.map((x,i)=>x-a[i]),v=c.map((x,i)=>x-a[i]);let n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],len=Math.hypot(...n)||1;n=n.map(x=>x/len);for(let i of tri)flat.push(...part.vertices[i],...n,...colors[part.group]);}add(flat,groups[part.group],gl.TRIANGLES);}
function axis(a,b,group,color){let flat=[];for(let p of [a,b])flat.push(...p,0,0,1,...color);add(flat,group,gl.LINES);}
axis([-30,0,24.4],[30,0,24.4],0,[.05,.05,.05]);axis([-2.35,-30,61.4],[-2.35,30,61.4],1,[.05,.05,.05]);axis([__SHAFT_X__,-30,__SHAFT_Z__],[__SHAFT_X__,30,__SHAFT_Z__],1,[.95,.10,.10]);
let yaw=-.73,pitch=.28,zoom=1.1,drag=false,lastX=0,lastY=0;
function render(){const dpr=Math.min(devicePixelRatio||1,2),w=Math.round(canvas.clientWidth*dpr),h=Math.round(canvas.clientHeight*dpr);canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);gl.clearColor(.957,.965,.973,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);for(let [k,v] of Object.entries({yaw,pitch,zoom,aspect:w/h,q1:+document.getElementById('q1').value*Math.PI/180,q2:+document.getElementById('q2').value*Math.PI/180}))gl.uniform1f(uniforms[k],v);for(let m of meshes){let name=['base','middle','upper'][m.group];if(!document.getElementById(name).checked)continue;if(m.mode===gl.LINES)gl.disable(gl.DEPTH_TEST);else gl.enable(gl.DEPTH_TEST);gl.uniform1f(uniforms.group,m.group);gl.bindBuffer(gl.ARRAY_BUFFER,m.buffer);for(let [k,offset] of [['pos',0],['normal',3],['color',6]]){gl.enableVertexAttribArray(attrs[k]);gl.vertexAttribPointer(attrs[k],3,gl.FLOAT,false,36,offset*4);}gl.drawArrays(m.mode,0,m.count);}}
canvas.addEventListener('pointerdown',e=>{drag=true;lastX=e.clientX;lastY=e.clientY;canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointermove',e=>{if(!drag)return;yaw+=(e.clientX-lastX)*.008;pitch=Math.max(-1.4,Math.min(1.4,pitch+(e.clientY-lastY)*.008));lastX=e.clientX;lastY=e.clientY;render();});canvas.addEventListener('pointerup',()=>drag=false);canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.5,Math.min(3,zoom*Math.exp(e.deltaY*.001)));render();},{passive:false});for(let k of ['base','middle','upper','q1','q2'])document.getElementById(k).addEventListener('input',()=>{for(let n of [1,2])document.getElementById('a'+n).value=document.getElementById('q'+n).value+'°';render();});document.getElementById('reset').onclick=()=>{yaw=-.73;pitch=.28;zoom=1.1;for(let n of [1,2]){document.getElementById('q'+n).value=0;document.getElementById('a'+n).value='0°';}render();};addEventListener('resize',render);render();
</script></html>'''
if args.enclosure:
    html=html.replace('Final Onshape assembly — joint review','Rev C2 enclosure — joint review').replace('Final Onshape assembly · proposed rigid groups','Fit-approved enclosure · training geometry review')
    html=html.replace('min="-35" max="35"','min="-80" max="80"')
    html=html.replace('vec3(0.,0.,74.5)','vec3(0.,0.,69.5)').replace('zoom=1.1','zoom=1.2').replace('pitch=.28','pitch=-.28')
    html=html.replace('Review only: axes, signs and travel limits are unconfirmed.','Kinematic preview only; sliders do not enforce contact or drive hardware. ±80° is the provisional simulation range.')
    html=html.replace('Exact imported placements; no alignment correction applied.','Revised cup/lid, relocated battery/XIAO and one Pololu; same joint axes as training. CAD bottom Z=-12 mm.')
output=(ROOT.parents[1]/'sim/enclosure/joints.html') if args.enclosure else ROOT/'review.html'
output.write_text(html.replace('__DATA__',json.dumps(geometry,separators=(',',':')).replace('</','<\\/')).replace('__ALIGNMENT_NOTE__',html_module.escape(note)).replace('__STRUCT_Z__',str(upper[2])).replace('__SHAFT_Z__',str(shaft[2])).replace('__SHAFT_X__',str(shaft[0])))
print('Wrote',output)
