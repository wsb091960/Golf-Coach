const test = require('node:test');
const assert = require('node:assert/strict');
const G = require('../app/static/js/swing_geometry.js');

test('joint solving preserves limb and club lengths across delivery extremes', () => {
  for (const torso of [-120, 0, 120]) for (const pelvis of [-80, 0, 90])
  for (const bend of [0, 60]) for (const side of [-35, 35])
  for (const arms of [-75, 0, 75]) for (const elevation of [-80, 0, 90]) {
    const p = G.pose({torso, pelvis, bend, side, arms, elevation, wrist: 85, sway: 6});
    for (const [a, b, length] of [
      ['leadShoulder', 'leadElbow', .30], ['leadElbow', 'leadHand', .27],
      ['trailShoulder', 'trailElbow', .30], ['trailElbow', 'trailHand', .27],
      ['leadHip', 'leadKnee', .45], ['leadKnee', 'leadFoot', .44],
      ['trailHip', 'trailKnee', .45], ['trailKnee', 'trailFoot', .44],
      ['hands', 'clubhead', .94], ['leadShoulder', 'trailShoulder', .42],
      ['leadHip', 'trailHip', .30]
    ]) assert.ok(Math.abs(G.len(G.sub(p[a], p[b])) - length) < 1e-7, `${a} to ${b}`);
  }
});

test('turn, bend, sway, arms and wrist controls move the corresponding geometry', () => {
  const a = G.pose();
  for (const [key, value] of Object.entries({torso: 50, pelvis: 65, bend: 45, side: 5, sway: 3, arms: 20, elevation: -20, wrist: 45})) {
    const b = G.pose({...a.p, [key]: value});
    assert.notDeepEqual(b.segments, a.segments, key);
  }
  const hinged = G.pose({...a.p, wrist: 70});
  assert.deepEqual(hinged.hands, a.hands, 'wrist hinge retains grip position');
  assert.ok(G.len(G.sub(hinged.clubhead, a.clubhead)) > .1, 'hinge moves the head');
  const turned = G.pose({...a.p, pelvis: 65});
  assert.deepEqual(turned.shoulder, a.shoulder, 'isolated pelvis turn retains torso');
});

test('axial separation and metric units have an analytic reference', () => {
  assert.equal(G.pose({torso: -90, pelvis: -40}).xfactor, 50);
  const a=G.pose({sway: 0}), b=G.pose({sway: 1});
  assert.ok(Math.abs(b.shoulder[0]-a.shoulder[0]-.0254) < 1e-10);
  assert.deepEqual(a.hip, b.hip, 'torso sway does not silently change pelvis position');
});
