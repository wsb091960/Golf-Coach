const fs = require("fs");
const vm = require("vm");

const code = fs.readFileSync("app/static/js/onform_screenshot_import.js", "utf8");
const fakeRoot = { querySelectorAll: () => [], querySelector: () => null };
const elements = new Map([
  ["onform-screenshot-import", fakeRoot],
  ["onform-screenshot-file-1", { addEventListener() {} }],
  ["onform-screenshot-file-2", { addEventListener() {} }],
  ["onform-screenshot-preview-1", {}], ["onform-screenshot-preview-2", {}],
  ["onform-screenshot-extract", { addEventListener() {} }],
  ["onform-screenshot-save", { addEventListener() {} }],
  ["onform-screenshot-status", {}], ["onform-screenshot-verified", {}],
  ["onform-screenshot-shot", {}], ["onform-screenshot-checkpoint", {}],
  ["onform-screenshot-conflicts", {}],
]);
const context = {
  console, FormData: function(){}, fetch: async () => ({}),
  URL: { createObjectURL: () => "blob:test" },
  document: { getElementById: (id) => elements.get(id) || null, querySelector: () => ({ dataset: { analysisId: "a1" } }) },
  window: {}, setTimeout,
};
context.window = context;
vm.createContext(context);
vm.runInContext(code, context);

const { parseSpatialWords, parseRibbonText, mergeMetrics } = context.OnformScreenshotParser;
function assert(cond, msg) { if (!cond) throw new Error(msg); }
function word(text, x0, y0, x1, y1, confidence=95) { return { text, bbox:{x0,y0,x1,y1}, confidence }; }

// Synthetic Onform ribbon: labels at y=20, values y=62, direction/units y=95.
const words1 = [
  word("FACE",10,15,52,31), word("TO",56,15,76,31), word("PATH",80,15,126,31),
  word("CLUB",155,15,198,31), word("PATH",202,15,248,31),
  word("FACE",278,15,320,31), word("ANGLE",324,15,378,31),
  word("ATTACK",405,15,462,31), word("ANGLE",466,15,520,31),
  word("LAUNCH",550,15,610,31), word("DIRECTION",614,15,704,31),
  word("BACK",735,15,778,31), word("SPIN",782,15,823,31),
  word("BALL",850,15,889,31), word("SPEED",893,15,945,31),
  word("CLUB",975,15,1018,31), word("SPEED",1022,15,1074,31),
  word("-0.9°R",52,58,100,79), word("0.0°L",186,58,230,79), word("0.9°R",318,58,360,79),
  word("6.1°D",450,58,492,79), word("0.7°R",620,58,664,79), word("5509",768,58,811,79),
  word("99.2",881,58,922,79), word("75.4",1005,58,1046,79),
  word("RIGHT",55,91,101,108), word("LEFT",190,91,225,108), word("RIGHT",320,91,366,108),
  word("DOWN",452,91,492,108), word("RIGHT",620,91,666,108), word("RPM",772,91,807,108),
  word("MPH",884,91,920,108), word("MPH",1007,91,1044,108),
  // Stray number from image should never be cross-wired into a metric.
  word("25",1300,3,1325,20)
];
let p = parseSpatialWords(words1, 1400).metrics;
assert(p.face_to_path === 0.9, "face-to-path right");
assert(p.club_path === -0.0 || Object.is(p.club_path,-0), "club path left zero");
assert(p.club_face === 0.9, "face angle");
assert(p.attack_angle === -6.1, "attack down negative");
assert(p.launch_direction === 0.7, "launch right");
assert(p.spin_rate === 5509, "back spin spatially paired");
assert(p.ball_speed === 99.2, "ball speed spatially paired");
assert(p.club_speed === 75.4, "club speed spatially paired");
assert(!("launch_angle" in p), "missing label/value remains blank");

const words2 = [
  word("LAUNCH",10,15,70,31), word("ANGLE",74,15,128,31),
  word("SIDE",165,15,202,31), word("SPIN",206,15,247,31),
  word("TORSO",285,15,335,31), word("TURN",339,15,380,31),
  word("PELVIS",420,15,476,31), word("TURN",480,15,521,31),
  word("XFACTOR",560,15,629,31),
  word("TORSO",670,15,720,31), word("SWAY",724,15,766,31),
  word("PELVIS",805,15,861,31), word("SWAY",865,15,907,31),
  word("PELVIS",945,15,1001,31), word("LIFT",1005,15,1040,31),
  word("20.3°",50,58,96,79), word("-79",190,58,225,79), word("5°",320,58,338,79),
  word("9°",460,58,478,79), word("-4°",590,58,620,79), word('0.1"',702,58,739,79),
  word('0.1"',839,58,876,79), word('0.1"',977,58,1014,79),
  word("OPEN",306,91,350,108), word("OPEN",446,91,490,108), word("TORSO-HIP",570,91,642,108),
  word("AWAY",696,91,740,108), word("TOWARDS",820,91,886,108), word("DOWN",976,91,1017,108)
];
p = parseSpatialWords(words2, 1200).metrics;
assert(p.launch_angle === 20.3, "launch angle");
assert(p.side_spin_rpm === -79, "side spin");
assert(p.torso_rotation === 5 && p.torso_rotation_direction === "OPEN", "torso turn/direction");
assert(p.pelvis_rotation === 9 && p.pelvis_rotation_direction === "OPEN", "pelvis turn/direction");
assert(p.x_factor === -4, "x factor");
assert(p.torso_sway === 0.1 && p.torso_sway_direction === "AWAY", "torso sway");
assert(p.pelvis_sway === 0.1 && p.pelvis_sway_direction === "TOWARDS", "pelvis sway");
assert(p.pelvis_lift === 0.1 && p.pelvis_lift_direction === "DOWN", "pelvis lift");

// Conservative text fallback: only adjacent label/value pairs are accepted.
let t = parseRibbonText("BACK SPIN 5509 RPM BALL SPEED 99.2 MPH");
assert(t.spin_rate === 5509 && t.ball_speed === 99.2, "adjacent fallback");
t = parseRibbonText("BACK SPIN BALL SPEED CLUB SPEED 0 -3 1 5509");
assert(!("spin_rate" in t) && !("ball_speed" in t), "plain-text fallback must not cross-wire earlier labels");

const merged = mergeMetrics({launch_angle:20.3, ball_speed:99.2}, {launch_angle:20.3, pelvis_rotation:9});
assert(merged.merged.pelvis_rotation === 9 && merged.disagreement.length === 0, "merge nonconflicting screenshots");
assert(mergeMetrics({launch_angle:20.3}, {launch_angle:21.0}).disagreement.length === 1, "conflict detected");
console.log("onform spatial screenshot parser tests passed");
