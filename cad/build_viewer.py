"""Write an offline, drag-to-orbit WebGL viewer of the exported CAD geometry."""
from pathlib import Path
import json

out = Path(__file__).resolve().parent
source = json.loads((out / 'geometry.json').read_text())
parts = {name: {key: item[key] for key in ('vertices','triangles','color')}
         for name, item in source['parts'].items()}
data = json.dumps(parts, separators=(',', ':'))
html = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Self-righting arm — 3D CAD viewer</title>
<style>
html,body{height:100%;margin:0;background:#f4f6f5;color:#223238;font:15px system-ui,sans-serif}
main{height:100%;display:flex;flex-direction:column}header{padding:14px 20px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
h1{font-size:18px;margin:0}small{color:#607178}label,button{cursor:pointer}button{background:white;border:1px solid #aebbc0;border-radius:6px;padding:5px 9px;color:#223238}
canvas{flex:1;width:100%;min-height:0;touch-action:none;cursor:grab}canvas:active{cursor:grabbing}
footer{padding:7px 20px;color:#607178;font-size:12px}
</style><main><header><h1>Self-righting arm · reference layout</h1>
<label><input type="checkbox" id="hardware" checked> Show purchased parts</label>
<button id="reset">Reset view</button><small>Drag to orbit · scroll to zoom</small></header>
<canvas id="view"></canvas><footer>Provisional PTK servo and horn outlines. Check physical fit before printing.</footer></main>
<script>
const parts = __PARTS__;
const canvas=document.getElementById('view'), gl=canvas.getContext('webgl',{antialias:true});
if(!gl){document.querySelector('footer').textContent='WebGL is unavailable in this browser.';throw Error('WebGL unavailable')}
const vs=`attribute vec3 pos;attribute vec3 normal;attribute vec3 color;
uniform float yaw,pitch,zoom,aspect;varying vec3 shade;
void main(){
 float cy=cos(yaw),sy=sin(yaw),cp=cos(pitch),sp=sin(pitch);
 vec3 p=vec3(cy*pos.x-sy*pos.y,sy*pos.x+cy*pos.y,pos.z);
 p=vec3(p.x,cp*p.y-sp*p.z,sp*p.y+cp*p.z);
 vec3 n=vec3(cy*normal.x-sy*normal.y,sy*normal.x+cy*normal.y,normal.z);
 n=vec3(n.x,cp*n.y-sp*n.z,sp*n.y+cp*n.z);
 float light=.55+.45*abs(dot(normalize(n),normalize(vec3(.3,-.6,.75))));
 shade=color*light;gl_Position=vec4(p.x/(zoom*aspect),p.z/zoom,-p.y/zoom,1.0);
}`;
const fs=`precision mediump float;varying vec3 shade;void main(){gl_FragColor=vec4(shade,1.0);}`;
function shader(type,src){let s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);
 if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s}
let program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vs));
gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(program);gl.useProgram(program);
const loc={};for(let k of ['pos','normal','color'])loc[k]=gl.getAttribLocation(program,k);
for(let k of ['yaw','pitch','zoom','aspect'])loc[k]=gl.getUniformLocation(program,k);
let meshes=[];
for(const [name,part] of Object.entries(parts)){
 let flat=[];const v=part.vertices,c=part.color;
 for(const tri of part.triangles){let a=v[tri[0]],b=v[tri[1]],d=v[tri[2]];
  let u=[b[0]-a[0],b[1]-a[1],b[2]-a[2]],w=[d[0]-a[0],d[1]-a[1],d[2]-a[2]];
  let n=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]];
  let length=Math.hypot(...n)||1;n=n.map(x=>x/length);
  for(let i of tri){let p=v[i];flat.push(p[0]/100,p[1]/100,(p[2]-85)/100,...n,...c)}
 }
 let buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
 gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(flat),gl.STATIC_DRAW);
 meshes.push({name,buffer,count:flat.length/9,printed:['base','middle_link','paddle'].includes(name)});
}
let yaw=-.7,pitch=.27,zoom=1.05,dirty=true,drag=false,lastX=0,lastY=0;
function render(){if(!dirty)return;dirty=false;
 let dpr=Math.min(devicePixelRatio||1,2),w=Math.round(canvas.clientWidth*dpr),h=Math.round(canvas.clientHeight*dpr);
 if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h}gl.viewport(0,0,w,h);
 gl.clearColor(.956,.965,.961,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
 gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.disable(gl.CULL_FACE);
 gl.uniform1f(loc.yaw,yaw);gl.uniform1f(loc.pitch,pitch);gl.uniform1f(loc.zoom,zoom);
 gl.uniform1f(loc.aspect,Math.max(w/h,.55));
 const showHardware=document.getElementById('hardware').checked;
 for(const m of meshes){if(!m.printed&&!showHardware)continue;
  gl.bindBuffer(gl.ARRAY_BUFFER,m.buffer);
  for(const [key,offset] of [['pos',0],['normal',3],['color',6]]){
   gl.enableVertexAttribArray(loc[key]);gl.vertexAttribPointer(loc[key],3,gl.FLOAT,false,36,offset*4)}
  gl.drawArrays(gl.TRIANGLES,0,m.count);
 }
}
function request(){dirty=true;requestAnimationFrame(render)}
canvas.addEventListener('pointerdown',e=>{drag=true;lastX=e.clientX;lastY=e.clientY;canvas.setPointerCapture(e.pointerId)});
canvas.addEventListener('pointermove',e=>{if(!drag)return;yaw+=(e.clientX-lastX)*.008;
 pitch=Math.max(-1.4,Math.min(1.4,pitch+(e.clientY-lastY)*.008));lastX=e.clientX;lastY=e.clientY;request()});
canvas.addEventListener('pointerup',()=>drag=false);
canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.65,Math.min(2.5,zoom*Math.exp(e.deltaY*.001)));request()},{passive:false});
document.getElementById('hardware').addEventListener('change',request);
document.getElementById('reset').addEventListener('click',()=>{yaw=-.7;pitch=.27;zoom=1.05;request()});
addEventListener('resize',request);request();
</script></html>'''
(out/'viewer.html').write_text(html.replace('__PARTS__', data))
print(f'Wrote {out / "viewer.html"}')
