const {test} = require('node:test');
const assert = require('node:assert/strict');
const M = require('../app/static/js/d_plane_model.js');
const close = (a,b) => assert(Math.abs(a-b)<1e-9, `${a} != ${b}`);
test('rigid oblique lean changes face and loft while keeping shaft on board', () => {
  const base={path:4,face:2,attack:-4,loft:25,weight:.75,hand:'right'};
  const neutral=M.compute(base), forward=M.compute({...base,lean:10}), backward=M.compute({...base,lean:-5});
  close(neutral.dynamicLoft,25); assert(forward.dynamicLoft<25); assert(backward.dynamicLoft>25);
  close(M.dot(forward.shaft,forward.referenceShaft),Math.cos(10*Math.PI/180));
  assert(forward.effectiveFace>neutral.effectiveFace);
  close(M.norm(forward.shaft),1); close(forward.f2p,forward.effectiveFace-forward.path);
  close(M.dot(forward.n,forward.shaft),M.dot(neutral.n,neutral.shaft));
  assert.notDeepEqual(neutral.n,forward.n); assert.notEqual(neutral.spinLoft,forward.spinLoft);
  close(M.dot(forward.s,forward.v),0); close(M.dot(forward.s,forward.n),0);
});
test('handedness mirrors shaft side without changing forward-lean sign', () => {
  const p={path:0,face:0,attack:-4,loft:25,lean:12,weight:.75};
  const right=M.compute({...p,hand:'right'}),left=M.compute({...p,hand:'left'});
  close(left.shaft[0],-right.shaft[0]); close(left.shaft[1],right.shaft[1]); close(left.shaft[2],right.shaft[2]);
  close(left.dynamicLoft,right.dynamicLoft);
});
test('zero spin loft remains explicitly undefined when delivery vectors coincide', () => {
  const swingDirection=Math.asin(Math.tan(5*Math.PI/180)/Math.tan(Math.PI/3))*180/Math.PI;
  const r=M.compute({path:swingDirection,face:0,attack:5,loft:5,lean:0,weight:.75});
  assert.equal(r.valid,false); assert.equal(r.s,null); assert.equal(r.tilt,null);
});
test('head attachment and every shaft point share fixed board without offset neck', () => {
  for(const hand of ['right','left']) for(const lean of [-10,0,10,25])
  for(const lieOffset of [-10,0,10]) for(const face of [-15,0,15]) for(const loft of [0,25,65]) {
    const r=M.compute({path:4,face,attack:-4,loft,lean,lieOffset,hand,weight:.75});
    const club=M.clubGeometry(r,hand);
    for(const p of [club.hosel,club.grip,M.add(club.hosel,M.mul(r.shaft,.16))]) close(M.dot(p,club.planeNormal),0);
    const attachment=club.point(.19,-.035,-.065);
    attachment.forEach((v,i)=>close(v,club.hosel[i]));
    close(M.norm(M.add(club.grip,M.mul(club.hosel,-1))),1.15);
    // Whole head is translated with the shaft, preserving its rigid dimensions.
    close(M.norm(M.add(club.point(0,0,0),M.mul(attachment,-1))),Math.hypot(.19,.035,.065));
    const a=club.hosel[1],b=M.dot(club.hosel,r.referenceShaft);
    assert(a>=-.4&&a<=1.5&&b>=-.22&&b<=1.4,'Attachment lies inside visible board');
  }
});

test('turning the plane squares the delivered face and keeps the club on the plane', () => {
  for (const hand of ['right', 'left']) {
    const inputs = {path:4, face:2, attack:-4, loft:25, lean:10, weight:.75, hand};
    const original = M.compute(inputs);
    const square = M.compute({...inputs, planeRotation:-original.effectiveFace});
    close(square.effectiveFace, 0);
    close(square.path, original.path-original.effectiveFace);
    close(square.dynamicLoft, original.dynamicLoft);
    close(square.spinLoft, original.spinLoft);
    close(square.f2p, original.f2p);
    const club = M.clubGeometry(square, hand);
    close(M.dot(club.hosel, club.planeNormal), 0);
    close(M.dot(club.grip, club.planeNormal), 0);
    const neutral = M.compute({...inputs, planeRotation:-original.effectiveFace, lean:0});
    assert.deepEqual(square.planeForward, neutral.planeForward);
    assert.deepEqual(square.referenceShaft, neutral.referenceShaft);
  }
});
