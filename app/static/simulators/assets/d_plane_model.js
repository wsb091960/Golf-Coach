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
 // Controlled experiment: lean changes loft with horizontal face angle fixed.
 // p.loft is the reference face loft at zero lean, not the stamped club loft.
 const lean=p.lean??0,dynamicLoft=p.loft-lean;
 const v=direction(p.path,p.attack),n=direction(p.face,dynamicLoft),c=cross(v,n),valid=norm(c)>1e-7,s=valid?unit(c):null;
 const lie=60*rad,side=p.hand==='left'?1:-1;
 const shaft=[side*Math.cos(lie),Math.sin(lean*rad)*Math.sin(lie),Math.cos(lean*rad)*Math.sin(lie)];
 const launch=unit(add(mul(v,1-p.weight),mul(n,p.weight)));
 const spinLoft=Math.acos(Math.max(-1,Math.min(1,dot(v,n))))*deg;
 const start=Math.atan2(launch[0],launch[1])*deg, elevation=Math.atan2(launch[2],Math.hypot(launch[0],launch[1]))*deg;
 const tilt=valid?Math.atan2(-s[2],Math.hypot(s[0],s[1]))*deg:null;
 const lift=valid?cross(s,launch):[0,0,0];
 const backspin=lift[2]>=-1e-7;
 return {v,n,s,shaft,lean,dynamicLoft,launch,spinLoft,start,elevation,tilt,lift,valid,backspin,f2p:p.face-p.path};
}
const api={add,mul,dot,cross,norm,unit,direction,compute};
if(typeof module!=='undefined')module.exports=api;else root.DPlane=api;
})(typeof window!=='undefined'?window:globalThis);
