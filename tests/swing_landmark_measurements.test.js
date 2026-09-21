const assert = require('assert');
const m = require('../app/static/js/swing_landmark_measurements.js');

const level = m.calculate2D({
  left_shoulder:{x:.35,y:.30}, right_shoulder:{x:.65,y:.30},
  left_hip:{x:.40,y:.60}, right_hip:{x:.60,y:.60},
});
assert.deepStrictEqual(level, {shoulder_tilt:0, hip_tilt:0, spine_tilt:0});

const tilted = m.calculate2D({
  left_shoulder:{x:.35,y:.32}, right_shoulder:{x:.65,y:.28},
  left_hip:{x:.40,y:.61}, right_hip:{x:.60,y:.59},
});
assert(tilted.shoulder_tilt > 0);
assert(tilted.hip_tilt > 0);

const analysis = {extra_metrics_json: JSON.stringify({onform_screenshot_imports:[
  {checkpoint_position:'P7', metrics:{pelvis_rotation:9, torso_rotation:5, x_factor:-4}},
]})};
assert.strictEqual(m.latestOnformMetrics(analysis,'P7').x_factor,-4);
assert.deepStrictEqual(m.latestOnformMetrics(analysis,'P4'),{});
console.log('swing landmark measurement tests passed');
