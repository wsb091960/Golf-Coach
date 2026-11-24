const {test} = require('node:test');
const assert = require('node:assert/strict');
const M = require('../app/static/js/d_plane_model.js');
const close = (a,b) => assert(Math.abs(a-b)<1e-9, `${a} != ${b}`);
test('lean changes shaft projection and delivered loft while holding horizontal face angle', () => {
  const base={path:4,face:2,attack:-4,loft:25,weight:.75,hand:'right'};
  const neutral=M.compute(base), forward=M.compute({...base,lean:10}), backward=M.compute({...base,lean:-5});
  close(neutral.dynamicLoft,25); close(forward.dynamicLoft,15); close(backward.dynamicLoft,30);
  close(Math.atan2(forward.shaft[1],forward.shaft[2])*180/Math.PI,10);
  close(Math.atan2(forward.n[0],forward.n[1])*180/Math.PI,2);
  close(M.norm(forward.shaft),1); close(forward.f2p,-2);
  assert.notDeepEqual(neutral.n,forward.n); assert.notEqual(neutral.spinLoft,forward.spinLoft);
  close(M.dot(forward.s,forward.v),0); close(M.dot(forward.s,forward.n),0);
});
test('handedness mirrors shaft side without changing forward-lean sign', () => {
  const p={path:0,face:0,attack:-4,loft:25,lean:12,weight:.75};
  const right=M.compute({...p,hand:'right'}),left=M.compute({...p,hand:'left'});
  close(left.shaft[0],-right.shaft[0]); close(left.shaft[1],right.shaft[1]); close(left.shaft[2],right.shaft[2]);
  close(left.dynamicLoft,right.dynamicLoft);
});
test('zero spin loft remains explicitly undefined, including lean-adjusted delivery', () => {
  const r=M.compute({path:0,face:0,attack:5,loft:15,lean:10,weight:.75});
  assert.equal(r.valid,false); assert.equal(r.s,null); assert.equal(r.tilt,null);
});
