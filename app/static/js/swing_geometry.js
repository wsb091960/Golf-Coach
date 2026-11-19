/* Metric-driven teaching geometry. Coordinates: +X target, +Y ball, +Z up. */
(function(root){
'use strict';
const R=Math.PI/180, add=(a,b)=>a.map((v,i)=>v+b[i]), sub=(a,b)=>a.map((v,i)=>v-b[i]), mul=(a,s)=>a.map(v=>v*s), dot=(a,b)=>a.reduce((v,x,i)=>v+x*b[i],0), cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]], len=a=>Math.hypot(...a), unit=a=>mul(a,1/(len(a)||1));
const rx=(p,t)=>[p[0],p[1]*Math.cos(t)-p[2]*Math.sin(t),p[1]*Math.sin(t)+p[2]*Math.cos(t)];
const ry=(p,t)=>[p[0]*Math.cos(t)+p[2]*Math.sin(t),p[1],-p[0]*Math.sin(t)+p[2]*Math.cos(t)];
const rz=(p,t)=>[p[0]*Math.cos(t)-p[1]*Math.sin(t),p[0]*Math.sin(t)+p[1]*Math.cos(t),p[2]];
const rotate=(p,axis,t)=>add(add(mul(p,Math.cos(t)),mul(cross(axis,p),Math.sin(t))),mul(axis,dot(axis,p)*(1-Math.cos(t))));
const presets={P1:{torso:0,pelvis:0,bend:32,side:0,sway:0,arms:0,elevation:-60,wrist:0},P4:{torso:-90,pelvis:-40,bend:25,side:-12,sway:-.5,arms:-35,elevation:55,wrist:85},P6:{torso:15,pelvis:30,bend:32,side:18,sway:1,arms:-22,elevation:-35,wrist:50},P7:{torso:20,pelvis:35,bend:30,side:18,sway:1.5,arms:0,elevation:-60,wrist:8}};

const blend=(a,b,t)=>Object.fromEntries(Object.keys(a).map(k=>[k,a[k]*(1-t)+b[k]*t]));
presets.P2=blend(presets.P1,presets.P4,1/3);presets.P3=blend(presets.P1,presets.P4,2/3);presets.P5=blend(presets.P4,presets.P6,.5);
presets.P8={torso:65,pelvis:60,bend:22,side:15,sway:1.5,arms:30,elevation:-10,wrist:12};presets.P9={torso:95,pelvis:80,bend:12,side:5,sway:1.5,arms:50,elevation:35,wrist:65};presets.P10={torso:110,pelvis:90,bend:5,side:0,sway:1.5,arms:60,elevation:55,wrist:85};
function elbow(a,b,pole,l1=.30,l2=.27){const d=sub(b,a),distance=Math.max(1e-6,len(d)),u=unit(d);const along=(l1*l1-l2*l2+distance*distance)/(2*distance),h=Math.sqrt(Math.max(0,l1*l1-along*along));const perpendicular=unit(sub(pole,mul(u,dot(pole,u))));return add(a,add(mul(u,along),mul(perpendicular,h)));}
function pose(input={}){
 const p={...presets.P7,...input};const trunk=v=>ry(rx(v,-p.bend*R),p.side*R),torso=v=>trunk(rz(v,-p.torso*R)),pelvis=v=>rz(v,-p.pelvis*R);
 const hip=[0,0,.87],shoulder=add(hip,add(trunk([0,0,.51]),[p.sway*.0254,0,0]));
 const leadHip=add(hip,pelvis([.15,0,0])),trailHip=add(hip,pelvis([-.15,0,0]));
 const leadShoulder=add(shoulder,torso([.21,0,0])),trailShoulder=add(shoulder,torso([-.21,0,0]));
 let hands=add(shoulder,torso([.46*Math.sin(p.arms*R)*Math.cos(p.elevation*R),.46*Math.cos(p.arms*R)*Math.cos(p.elevation*R),.46*Math.sin(p.elevation*R)]));
 for(let i=0;i<12;i++)for(const joint of[leadShoulder,trailShoulder]){const d=sub(hands,joint);if(len(d)>.55)hands=add(joint,mul(unit(d),.55));}
 const leadHand=add(hands,torso([.016,0,0])),trailHand=add(hands,torso([-.016,0,0]));
 const leadElbow=elbow(leadShoulder,leadHand,torso([.7,.5,-.1])),trailElbow=elbow(trailShoulder,trailHand,torso([-.7,.5,-.1]));
 const extension=unit(sub(hands,mul(add(leadElbow,trailElbow),.5))),shaft=rotate(extension,unit(torso([1,0,0])),p.wrist*R),clubhead=add(hands,mul(shaft,.94));
 const leadFoot=[.19,0,.035],trailFoot=[-.19,0,.035],leadKnee=elbow(leadHip,leadFoot,[0,1,0],.45,.44),trailKnee=elbow(trailHip,trailFoot,[0,1,0],.45,.44);
 const ring=(c,fn,a,b)=>Array.from({length:49},(_,i)=>add(c,fn([Math.cos(i/48*Math.PI*2)*a,Math.sin(i/48*Math.PI*2)*b,0])));
 const segments=[['spine',hip,shoulder],['torso',leadShoulder,trailShoulder],['pelvis',leadHip,trailHip],['lead',leadShoulder,leadElbow],['lead',leadElbow,leadHand],['trail',trailShoulder,trailElbow],['trail',trailElbow,trailHand],['leg',leadHip,leadKnee],['leg',leadKnee,leadFoot],['leg',trailHip,trailKnee],['leg',trailKnee,trailFoot],['club',hands,clubhead]];
 const faceAxis=unit(cross(shaft,torso([0,1,0]))),faceNormal=unit(cross(faceAxis,shaft));const faceCorners=[[-1,-1],[1,-1],[1,1],[-1,1]].map(([x,y])=>add(clubhead,add(mul(faceAxis,x*.06),mul(shaft,y*.025))));
 return{p,hip,shoulder,hands,clubhead,leadHip,trailHip,leadShoulder,trailShoulder,leadElbow,trailElbow,leadHand,trailHand,leadFoot,trailFoot,leadKnee,trailKnee,segments,torsoRing:ring(shoulder,torso,.29,.19),pelvisRing:ring(hip,pelvis,.23,.16),spineTip:add(shoulder,trunk([0,0,.13])),torsoForward:add(shoulder,torso([0,.31,0])),pelvisForward:add(hip,pelvis([0,.28,0])),faceCorners,faceNormal,xfactor:Math.abs(p.torso-p.pelvis)};
}
function mount(canvas,opts={}){
 let current=pose(opts.pose),baseline=pose(opts.baseline||opts.pose),showBaseline=true,showPlanes=true,yaw=-.55,pitch=.23,drag=null,zoom=1;
 const colors={spine:'#56cee3',torso:'#eab557',pelvis:'#63c69d',lead:'#f2eee1',trail:'#8aa8a2',leg:'#839c95',club:'#fff'};
 function draw(){const box=canvas.getBoundingClientRect();if(box.width<1)return;const dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(box.width*dpr);canvas.height=Math.round(box.height*dpr);const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);const w=box.width,h=box.height;
 const cam=[Math.sin(yaw)*Math.cos(pitch),Math.cos(yaw)*Math.cos(pitch),Math.sin(pitch)],right=[Math.cos(yaw),-Math.sin(yaw),0],up=unit(cross(right,cam));
 const fitPoints=[...current.segments,...(showBaseline?baseline.segments:[])].flatMap(s=>[s[1],s[2]]).concat(current.torsoRing,current.pelvisRing);
 const xs=fitPoints.map(p=>dot(p,right)),ys=fitPoints.map(p=>dot(p,up));const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys),scale=Math.min(w*.76/(maxX-minX+.06),h*.80/(maxY-minY+.06))*zoom;
 const centerX=(minX+maxX)/2,centerY=(minY+maxY)/2;const project=v=>[w*.48+(dot(v,right)-centerX)*scale,h*.53-(dot(v,up)-centerY)*scale];
 c.fillStyle='#112e2e';c.fillRect(0,0,w,h);
 function line(points,color,width=1,dash=[]){c.beginPath();points.forEach((p,i)=>{const q=project(p);if(!i)c.moveTo(...q);else c.lineTo(...q);});c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.lineJoin='round';c.setLineDash(dash);c.stroke();c.setLineDash([]);}
 function label(text,v,color,dx=8,dy=0){const p=project(v);c.font='12px system-ui';const tw=c.measureText(text).width;const x=Math.max(8,Math.min(w-tw-8,p[0]+dx)),y=Math.max(15,Math.min(h-12,p[1]+dy));c.fillStyle='#112e2ee0';c.fillRect(x-4,y-13,tw+8,18);c.fillStyle=color;c.fillText(text,x,y);}
 function polygon(points,color){c.beginPath();points.forEach((p,i)=>{const q=project(p);if(!i)c.moveTo(...q);else c.lineTo(...q);});c.closePath();c.fillStyle=color;c.fill();}
 for(let i=-1;i<=1.001;i+=.2){line([[i,-.8,0],[i,1,0]],'#284943');line([[-1,i,0],[1,i,0]],'#284943');}line([[-.9,.55,.002],[.9,.55,.002]],'#8da99c',1,[5,6]);label('TARGET',[.85,.55,0],'#a1b9ad',-16,20);line([[.85,.55,0],[.73,.50,0]],'#8da99c');line([[.85,.55,0],[.73,.60,0]],'#8da99c');
 if(showBaseline){baseline.segments.forEach(([,a,b])=>line([a,b],'#99b1a35e',2,[4,5]));line(baseline.torsoRing,'#99b1a35e',1,[4,5]);line(baseline.pelvisRing,'#99b1a35e',1,[4,5]);}
 if(showPlanes){polygon(current.pelvisRing,'#63c69d20');polygon(current.torsoRing,'#eab55720');const plane=[current.leadShoulder,current.trailShoulder,current.trailHip,current.leadHip];polygon(plane,'#3d89831a');line(current.torsoRing,colors.torso,1.5);line(current.pelvisRing,colors.pelvis,1.5);line([current.hip,current.pelvisForward],colors.pelvis,2);line([current.shoulder,current.torsoForward],colors.torso,2);}
 const sorted=[...current.segments].sort((a,b)=>dot(mul(add(a[1],a[2]),.5),cam)-dot(mul(add(b[1],b[2]),.5),cam));
 sorted.forEach(([kind,a,b])=>{line([a,b],'#0c2525',kind==='club'?5:8);line([a,b],colors[kind],kind==='spine'?5:kind==='club'?2.5:4);});
 line([current.shoulder,current.spineTip],colors.spine,3);polygon(current.faceCorners,'#eea6d8');line([...current.faceCorners,current.faceCorners[0]],'#f8d7ef',1.5);
 for(const key of['leadShoulder','trailShoulder','leadElbow','trailElbow','leadHip','trailHip','hands','leadKnee','trailKnee']){const p=project(current[key]);c.beginPath();c.arc(...p,3.5,0,Math.PI*2);c.fillStyle='#d5e4d9';c.fill();}
 label('TORSO '+current.p.torso.toFixed(0)+'°',current.torsoRing[0],colors.torso,12,pitch>1?-35:-8);label('PELVIS '+current.p.pelvis.toFixed(0)+'°',current.pelvisRing[0],colors.pelvis,12,pitch>1?40:20);
 c.font='11px system-ui';c.fillStyle='#9ab5a9';c.fillText('3D GEOMETRY · DRAG TO ORBIT',16,24);c.fillStyle='#739487';c.fillText('Illustrative joints & proportions',16,h-16);
 }
 const observer=new ResizeObserver(draw);observer.observe(canvas);canvas.style.touchAction='none';canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,yaw,pitch};canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointermove',e=>{if(!drag)return;yaw=drag.yaw-(e.clientX-drag.x)*.008;pitch=Math.max(-.3,Math.min(1.5,drag.pitch+(e.clientY-drag.y)*.008));draw();});canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);canvas.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();yaw+=(e.key==='ArrowRight'?.1:e.key==='ArrowLeft'?-.1:0);pitch=Math.max(-.3,Math.min(1.5,pitch+(e.key==='ArrowUp'?.1:e.key==='ArrowDown'?-.1:0)));draw();});
 draw();return{setPose:(p,b)=>{current=pose(p);if(b)baseline=pose(b);draw();},setView:name=>{[yaw,pitch]=name==='face'?[0,.02]:name==='dtl'?[-Math.PI/2,.02]:name==='top'?[0,1.5]:[-.55,.23];draw();},setBaseline:value=>{showBaseline=value;draw();},setPlanes:value=>{showPlanes=value;draw();},draw,destroy:()=>observer.disconnect()};
}
const api={pose,presets,mount,add,sub,len,dot,cross,unit,rx,ry,rz};if(typeof module!=='undefined')module.exports=api;else root.SwingGeometry=api;
})(typeof window!=='undefined'?window:globalThis);
