"""Self-contained orbit viewer, CAD render and dimensioned packaging layout."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
data = json.loads((OUT/'geometry.json').read_text())
params=data['parameters']
bx,by,_=params['battery_center']
template = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lower electronics pod · fit revision 3</title><style>
*{box-sizing:border-box}body{margin:0;font:15px system-ui;color:#183644;background:#f3f6f8}main{height:100dvh;display:flex;flex-direction:column}header{padding:14px 18px;background:white}h1{font-size:20px;margin:0 0 8px}.row{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin:8px 0}button{padding:7px 12px;border:1px solid #afc0c7;border-radius:5px;background:#f1f5f6;color:#183644}canvas{flex:1;width:100%;min-height:240px;touch-action:none;cursor:grab}footer{padding:9px 18px;background:white;font-size:13px}a{color:#166f91}.note{color:#96512a;font-size:13px}input[type=range]{width:110px;vertical-align:middle}
</style><main><header><h1>Lower electronics pod · fit revision 3</h1><div class="row"><button id="pod">Focus enclosure</button><button id="robot">Whole robot</button><button id="top">Top layout</button><button id="usb">USB opening</button><button id="front">Front switch</button><button id="lid">Thin lid</button><button id="cutaway">Open enclosure</button><label>Explode <input id="explode" type="range" min="0" max="35" value="0"></label></div><div class="row" id="toggles"></div><div class="note">USB window 9.8 × 4.1 mm · battery 7.3 mm rearward / 3.65 mm left · left wall replaces end stop · rear rail joins wall · relieved screw boss retains 2.1 mm pilot wall. Cup-only reprint; existing C2 lid fits. New USB/battery fit pending.</div></header><canvas id="view"></canvas><footer>Drag to orbit · scroll to zoom · use visibility checkboxes to see the internals. <a href="layout.svg">Dimensioned layout</a> · <a href="PRINT_FIT_CHECK.md">Fit instructions</a> · <a href="assembly_review.step">STEP assembly</a>. No robot commands are sent by this viewer.</footer></main><script>
const data=__DATA__,canvas=document.getElementById('view'),gl=canvas.getContext('webgl',{antialias:true});if(!gl)throw Error('WebGL unavailable');
const vs=`attribute vec3 pos,normal,color;uniform float yaw,pitch,zoom,aspect;uniform vec3 center,offset;varying vec3 shade;
mat3 rx(float a){float c=cos(a),s=sin(a);return mat3(1.,0.,0.,0.,c,s,0.,-s,c);}mat3 rz(float a){float c=cos(a),s=sin(a);return mat3(c,s,0.,-s,c,0.,0.,0.,1.);}
void main(){vec3 p=pos+offset-center;mat3 v=rx(pitch)*rz(yaw);p=v*p;vec3 n=v*normal;shade=color*(.55+.45*abs(dot(normalize(n),normalize(vec3(.3,-.6,.75)))));gl_Position=vec4(p.x/(zoom*aspect),p.z/zoom,p.y/500.,1.);}`;
const fs=`precision mediump float;varying vec3 shade;void main(){gl_FragColor=vec4(shade,1.);}`;
function shader(kind,source){let s=gl.createShader(kind);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
let program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vs));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);
const attrs={},uni={},meshes=[];for(let k of ['pos','normal','color'])attrs[k]=gl.getAttribLocation(program,k);for(let k of ['yaw','pitch','zoom','aspect','center','offset'])uni[k]=gl.getUniformLocation(program,k);
for(let [id,p] of Object.entries(data.parts)){let flat=[];for(let t of p.triangles){let [a,b,c]=t.map(i=>p.vertices[i]),u=b.map((v,i)=>v-a[i]),v=c.map((v,i)=>v-a[i]),n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],l=Math.hypot(...n)||1;n=n.map(x=>x/l);for(let i of t)flat.push(...p.vertices[i],...n,...p.color);}let buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(flat),gl.STATIC_DRAW);meshes.push({id,group:p.group,buffer,count:flat.length/9});}
const groups={original:'Thin lid / servo mount',arm:'Arm',cup:'One-piece cup',electronics:'Electronics (no headers)'};
for(let [key,label] of Object.entries(groups)){let l=document.createElement('label'),i=document.createElement('input');i.type='checkbox';i.id=key;i.checked=!(key==='arm'||key==='original');i.onchange=render;l.append(i,' '+label);document.getElementById('toggles').append(l);}
let yaw=-.65,pitch=.6,zoom=53,center=[0,0,-6],drag=false,lastX=0,lastY=0;
function render(){let dpr=Math.min(devicePixelRatio||1,2),w=Math.round(canvas.clientWidth*dpr),h=Math.round(canvas.clientHeight*dpr);canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);gl.clearColor(.953,.965,.973,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);for(let [k,v] of Object.entries({yaw,pitch,zoom,aspect:w/h}))gl.uniform1f(uni[k],v);gl.uniform3fv(uni.center,center);let e=+document.getElementById('explode').value;for(let m of meshes){if(!document.getElementById(m.group).checked)continue;let offset=m.group==='cup'?[0,0,-e]:m.group==='arm'||m.group==='original'?[0,0,e]:[0,0,0];gl.uniform3fv(uni.offset,offset);gl.bindBuffer(gl.ARRAY_BUFFER,m.buffer);for(let [k,o] of [['pos',0],['normal',3],['color',6]]){gl.enableVertexAttribArray(attrs[k]);gl.vertexAttribPointer(attrs[k],3,gl.FLOAT,false,36,o*4);}gl.drawArrays(gl.TRIANGLES,0,m.count);}}
function visibility(values){for(let [k,v] of Object.entries(values))document.getElementById(k).checked=v;}
document.getElementById('pod').onclick=()=>{visibility({arm:false,original:false,cup:true,electronics:true});document.getElementById('explode').value=0;center=[0,0,-6];zoom=53;yaw=-.65;pitch=.6;render();};
document.getElementById('robot').onclick=()=>{visibility({arm:true,original:true,cup:true,electronics:true});center=[0,0,65];zoom=106;pitch=.25;document.getElementById('explode').value=0;render();};
document.getElementById('top').onclick=()=>{visibility({arm:false,original:false,cup:true,electronics:true});center=[0,0,-6];zoom=43;yaw=0;pitch=Math.PI/2;document.getElementById('explode').value=0;render();};
document.getElementById('front').onclick=()=>{visibility({arm:false,original:false,cup:true,electronics:true});center=[0,0,-6];zoom=43;yaw=0;pitch=0;document.getElementById('explode').value=0;render();};
document.getElementById('usb').onclick=()=>{visibility({arm:false,original:false,cup:true,electronics:true});center=[-33.8,-15.5,-6.545];zoom=15;yaw=Math.PI/2;pitch=0;document.getElementById('explode').value=0;render();};
document.getElementById('lid').onclick=()=>{visibility({arm:false,original:true,cup:false,electronics:false});center=[0,0,12];zoom=48;yaw=-.65;pitch=.6;document.getElementById('explode').value=0;render();};
document.getElementById('cutaway').onclick=()=>{visibility({arm:false,original:false,cup:true,electronics:true});center=[0,0,-6];zoom=48;yaw=-.65;pitch=.8;render();};
document.getElementById('explode').oninput=render;canvas.onpointerdown=e=>{drag=true;lastX=e.clientX;lastY=e.clientY;canvas.setPointerCapture(e.pointerId);};canvas.onpointermove=e=>{if(!drag)return;yaw+=(e.clientX-lastX)*.008;pitch=Math.max(-Math.PI/2,Math.min(Math.PI/2,pitch+(e.clientY-lastY)*.008));lastX=e.clientX;lastY=e.clientY;render();};canvas.onpointerup=()=>drag=false;canvas.onpointercancel=()=>drag=false;canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(20,Math.min(240,zoom*Math.exp(e.deltaY*.001)));render();},{passive:false});addEventListener('resize',render);render();
</script></html>'''
(OUT/'viewer.html').write_text(template.replace('__DATA__', json.dumps(data, separators=(',', ':')).replace('</','<\\/')))

# Static CAD render: whole robot and cutaway enclosure, drawn from actual meshes.
W, H = 1800, 1100
im = Image.new('RGB', (W, H), '#f3f6f8')
draw = ImageDraw.Draw(im)
fontfile = '/System/Library/Fonts/Supplemental/Arial.ttf'
font = lambda size: ImageFont.truetype(fontfile, size)


def render_region(region, anchor, center, yaw, pitch, scale, include):
    cy, sy, cp, sp = np.cos(yaw), np.sin(yaw), np.cos(pitch), np.sin(pitch)
    rotation = np.array([[cy,-sy,0],[cp*sy,cp*cy,-sp],[sp*sy,sp*cy,cp]])
    x0,y0,x1,y1 = region
    depth = np.full((y1-y0,x1-x0), np.inf)
    rgb = np.zeros((y1-y0,x1-x0,3),dtype=np.uint8)
    rgb[:]=[243,246,248]
    light = np.array([.3, -.6, .75]); light /= np.linalg.norm(light)
    for part in data['parts'].values():
        if part['group'] not in include: continue
        v = np.array(part['vertices']); tri = np.array(part['triangles']); faces = v[tri]
        n = np.cross(faces[:,1]-faces[:,0], faces[:,2]-faces[:,0]); n /= np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
        shade = .55 + .45*np.abs(n@light)
        points = (v-np.array(center))@rotation.T
        projected = np.c_[anchor[0]+points[:,0]*scale, anchor[1]-points[:,2]*scale]
        for i,t in enumerate(tri):
            a,b,c=projected[t]
            den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(den)<1e-8: continue
            lo=np.maximum(np.floor(np.min(projected[t],axis=0)).astype(int),[x0,y0])
            hi=np.minimum(np.ceil(np.max(projected[t],axis=0)).astype(int)+1,[x1,y1])
            if np.any(hi<=lo):continue
            yy,xx=np.mgrid[lo[1]:hi[1],lo[0]:hi[0]];xx=xx+.5;yy=yy+.5
            u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
            vv=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
            ww=1-u-vv
            z=u*points[t[0],1]+vv*points[t[1],1]+ww*points[t[2],1]
            dst=depth[lo[1]-y0:hi[1]-y0,lo[0]-x0:hi[0]-x0]
            mask=(u>=-1e-7)&(vv>=-1e-7)&(ww>=-1e-7)&(z<dst)
            dst[mask]=z[mask]
            dst_rgb=rgb[lo[1]-y0:hi[1]-y0,lo[0]-x0:hi[0]-x0]
            dst_rgb[mask]=(255*np.array(part['color'])*shade[i]).astype(np.uint8)
    im.paste(Image.fromarray(rgb),region[:2])


draw.text((55,35),'UNDER-BASE ELECTRONICS POD',font=font(36),fill='#183644')
draw.text((55,85),'FIT REVISION 3 | tighter USB opening, battery toward edge, wall stop and local boss relief',font=font(23),fill='#526b78')
render_region((30,145,660,970),(345,570),(0,0,63),-.67,.28,4.3,{'original','arm','cup','electronics'})
render_region((700,170,1770,880),(1225,535),(0,0,-6),-.65,.85,8.,{'cup','electronics'})
draw.text((90,150),'Assembled: 12 mm cup + 2 mm lid',font=font(24),fill='#183644')
draw.text((780,150),'Lower cup: outward battery + tighter USB fit',font=font(24),fill='#183644')
draw.text((760,880),'Battery: 7.3 mm rearward / 3.65 mm left; wall replaces end stop',font=font(22),fill='#6d572c')
draw.text((760,920),'Both boards: 0.6 mm PSA lands; no pin headers',font=font(22),fill='#285e43')
draw.text((760,960),'USB 9.8 × 4.1 mm; two screw axes and C2 lid unchanged',font=font(22),fill='#8d4038')
draw.line((55,1010,1745,1010),fill='#c5d3d8',width=2)
draw.text((55,1034),'Reprint cup only; check USB cable, battery and boss fit. Saved training model remains frozen to C2.',font=font(22),fill='#96512a')
im.save(OUT/'preview.png')

# True-scale dimensioned top plan, with enough space for readable callouts.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="950" viewBox="0 0 1200 950">',
     '<rect width="1200" height="950" fill="#f3f6f8"/>',
     '<style>text{font-family:Arial,sans-serif;fill:#183644}.label{font-size:20px}.small{font-size:16px}.dim{font-size:18px;fill:#526b78}</style>',
     '<text x="45" y="48" font-size="30">Lower electronics pod — fit revision 3</text>',
     '<text x="45" y="82" class="label">Lid and arm hidden · dimensions in mm · no headers; direct solder wiring</text>']
S=8.; OX=420.; OY=460.
def rect(x,y,w,h,fill,stroke='#526b78',radius=0):
    return f'<rect x="{OX+(x-w/2)*S}" y="{OY-(y+h/2)*S}" width="{w*S}" height="{h*S}" rx="{radius*S}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
def line(points,color='#526b78',dashed=False):
    return '<polyline points="'+' '.join(f'{OX+x*S},{OY-y*S}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="2"'+(' stroke-dasharray="7 5"' if dashed else '')+'/>'
svg += [rect(0,0,70,70,'#c3d1d6',radius=5),rect(0,0,67.6,67.6,'#edf2f4',radius=3.8),
        rect(bx,by,59.5,19,'#d5b45e'),
        rect(bx+30.75,by,1.4,15.,'#c3d1d6'),
        rect(bx,by-10.5,42.,1.4,'#c3d1d6'),
        rect(bx,32.55,42.,2.9,'#c3d1d6'),
        rect(-22.21802,-15.5,21.,17.78,'#6c9c7a'),rect(-32.7,-15.5,3.,9.1,'#c0c4c3'),
        rect(10,-4.5,13,7,'#bf7767'),rect(0,-21,9,12,'#bf7767'),rect(10,-21,9,12,'#bf7767'),
        rect(23.62,-27.08,15.24,15.24,'#43854a'),rect(24.37,-34.83,1.3,1.5,'#343c3f'),
        rect(-34.1,-15.50733,1.2,9.8,'#f3f6f8','#197eab'),rect(23.62,-34.1,10,1.2,'#f3f6f8','#b56940')]
for x in (-31.6,-12.6):
    for y in (-25.14,-5.86):svg.append(rect(x,y,2.,.9,'#c3d1d6'))
svg += [rect(-10.96802,-15.5,.9,8.,'#c3d1d6')]
for x,y in [(-29.5,-29.5),(29.5,29.5)]:
    mask=''
    if x>0:
        svg.append('<defs><mask id="boss-relief"><rect width="1200" height="950" fill="white"/>'+rect(bx,by,60.1,19.6,'black','black')+'</mask></defs>')
        mask=' mask="url(#boss-relief)"'
    svg.append(f'<circle cx="{OX+x*S}" cy="{OY-y*S}" r="{3.8*S}" fill="#c3d1d6" stroke="#526b78" stroke-width="2"{mask}/>')
    svg.append(f'<circle cx="{OX+x*S}" cy="{OY-y*S}" r="{1.0*S}" fill="white" stroke="#526b78" stroke-width="2"/>')
svg += [line([(-35,39),(35,39)]),line([(-35,36),(-35,41)]),line([(35,36),(35,41)]),
        '<text x="395" y="140" class="dim">70</text>',
        line([(39,-35),(39,35)]),line([(36,-35),(41,-35)]),line([(36,35),(41,35)]),
        '<text x="744" y="465" class="dim">70</text>',
        line([(20,21.3),(44,22),(49,22)]),'<text x="825" y="275" class="label">Battery moved outward</text>',
        '<text x="825" y="304" class="small">+7.3 rear / 3.65 left</text>',
        '<text x="825" y="330" class="small">Boss pilot wall: 2.1 mm min.</text>',
        line([(-24,-15.5),(-43,-11),(-46,-11)]),'<text x="25" y="520" class="label">XIAO stops</text>',
        '<text x="25" y="547" class="small">USB 9.8 × 4.1</text>',
        line([(12,-7),(44,-8),(49,-8)]),'<text x="825" y="515" class="label">Clear wire-routing bay</text>',
        '<text x="825" y="544" class="small">Existing plugs laid flat</text>',
        line([(23.62,-31),(44,-24),(49,-24)]),'<text x="825" y="645" class="label">ONE Pololu at corner</text>',
        '<text x="825" y="674" class="small">Low PSA lands + stops</text>',
        line([(23.62,-35),(23.62,-42),(20,-42)]),'<text x="510" y="813" class="label">Slider opening 2.6 mm high (was 6)</text>',
        '<text x="510" y="842" class="small">Thin PCB-edge relief below opening</text>',
        '<text x="45" y="894" class="small">12 mm cup body + 2 mm lid = 14 mm closed package; registration tabs fit into lid pockets.</text>',
        '<text x="45" y="926" class="small">Two M2×10 screws into 2.0 mm blind holes matching the proven printed-model screw fit. No nuts.</text>',
        '</svg>']
(OUT/'layout.svg').write_text('\n'.join(svg)+'\n')
print('Wrote viewer.html, preview.png and layout.svg')
