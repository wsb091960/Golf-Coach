(function(root){
const rad=Math.PI/180,deg=180/Math.PI;
const add=(a,b)=>a.map((x,i)=>x+b[i]);
const mul=(a,k)=>a.map(x=>x*k);
const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const norm=a=>Math.hypot(...a);
const unit=a=>mul(a,1/(norm(a)||1));
const direction=(h,v)=>[Math.cos(v*rad)*Math.sin(h*rad),Math.cos(v*rad)*Math.cos(h*rad),Math.sin(v*rad)];
function compute(p){
 // Illustrative rigid rotation about an oblique horizontal axis.
 // Axis azimuth is a model assumption, not a measured wrist-release relationship.
 const lean=p.lean??0,side=p.hand==='left'?1:-1,lie=60*rad;
 const localShaft=[side*Math.cos(lie),0,Math.sin(lie)];
 const axis=unit(cross(localShaft,[0,1,0])),t=lean*rad;
 const leanRotate=a=>add(add(mul(a,Math.cos(t)),mul(cross(axis,a),Math.sin(t))),mul(axis,dot(axis,a)*(1-Math.cos(t))));
 const planeRotation=p.planeRotation??0, a=planeRotation*rad;
 const cos=Math.cos(a), sin=Math.sin(a);
 const turn=([x,y,z])=>[x*cos+y*sin,y*cos-x*sin,z];
 const planeForward=[sin,cos,0], referenceShaft=turn(localShaft);
 const q=side*(p.lieOffset??0)*rad;
 const rotate=([x,y,z])=>turn(leanRotate([x*Math.cos(q)+z*Math.sin(q),y,-x*Math.sin(q)+z*Math.cos(q)]));
 const localNormal=direction(p.face,p.loft);
 const referenceNormal=turn(localNormal),n=unit(rotate(localNormal));
 const dynamicLoft=Math.atan2(n[2],Math.hypot(n[0],n[1]))*deg;
 const effectiveFace=Math.atan2(n[0],n[1])*deg;
 const swingDirection=p.path+planeRotation; const swingPlane=(p.swingPlane??60)*rad; const path=swingDirection-Math.asin(Math.max(-1,Math.min(1,Math.tan(p.attack*rad)/Math.tan(swingPlane))))*deg; const v=direction(path,p.attack),c=cross(v,n),valid=norm(c)>1e-7,s=valid?unit(c):null;
 const toe=rotate(unit(cross(localNormal,[0,0,1]))),faceUp=unit(cross(toe,n));
 const shaft=turn(leanRotate(localShaft));
 const launch=unit(add(mul(v,1-p.weight),mul(n,p.weight)));
 const spinLoft=Math.acos(Math.max(-1,Math.min(1,dot(v,n))))*deg;
 const start=Math.atan2(launch[0],launch[1])*deg, elevation=Math.atan2(launch[2],Math.hypot(launch[0],launch[1]))*deg;
 const tilt=valid?Math.atan2(-s[2],Math.hypot(s[0],s[1]))*deg:null;
 const lift=valid?cross(s,launch):[0,0,0];
 const backspin=lift[2]>=-1e-7;
 return {v,n,s,shaft,referenceShaft,planeForward,lean,dynamicLoft,launch,spinLoft,start,elevation,tilt,lift,valid,backspin,effectiveFace,referenceNormal,toe,faceUp,swingDirection,path,f2p:effectiveFace-path};
}
// Place the entire illustrative club on the fixed board. Translating just the
// shaft leaves a disconnected hosel behind the board, even when its endpoints
// pass a coplanarity check. Every head vertex uses the same translation here.
function clubGeometry(r,hand){
 const mirror=hand==='left'?1:-1;
 const planeNormal=unit(cross(r.planeForward,r.referenceShaft));
 const localPoint=(a,b,d=0)=>add(add(mul(r.toe,a*mirror),mul(r.faceUp,b)),mul(r.n,d));
 const rawHosel=localPoint(.19,-.035,-.065);
 const shift=mul(planeNormal,-dot(rawHosel,planeNormal));
 const point=(a,b,d=0)=>add(localPoint(a,b,d),shift);
 const hosel=point(.19,-.035,-.065);
 const grip=add(hosel,mul(r.shaft,1.15));
 return {point,hosel,grip,planeNormal};
}
const api={add,mul,dot,cross,norm,unit,direction,compute,clubGeometry};
if(typeof module!=='undefined')module.exports=api;else root.DPlane=api;
})(typeof window!=='undefined'?window:globalThis);
