"""Conservative, rule-based GCIE lesson drafting. Never treats inferred causes as measured facts."""
PATTERNS = {
 "pull-hook":("starts left and curves farther left","face left of path, impact strike and alignment"),
 "pull":("starts left and remains relatively straight","face alignment and target-line setup"),
 "pull-fade":("starts left and curves right","leftward path with face right of path"),
 "draw":("curves right-to-left","face left of path and impact strike"),
 "straight":("flies relatively straight","start direction, strike and dispersion"),
 "fade":("curves left-to-right","face right of path and impact strike"),
 "push-draw":("starts right and curves left","rightward path with face left of path"),
 "push":("starts right and remains relatively straight","face alignment and target-line setup"),
 "push-slice":("starts right and curves farther right","face right of path, impact strike and alignment"),
}
def generate(pattern,handedness,club,observations):
    desc,geometry=PATTERNS[pattern]
    flip="For a left-handed golfer, reverse the directional descriptions used for a right-handed example." if handedness=="left" else "Directional descriptions refer to a right-handed golfer."
    target=("For an intentional push draw: start right, curve gently left, finish near target. Illustrative path +3°, face +1.5°, face-to-path −1.5°; these are NOT measurements." if pattern=="push-draw" and handedness=="right" else "Define the student's desired start line, curvature, finish and dispersion before setting any face/path targets.")
    return f"""GCIE GENERATED LESSON PLAN — {club.upper()} / {pattern.replace('-', ' ').title()}
Status: PROVISIONAL / UNVERIFIED. This is a rules-based coaching draft, not an AI diagnosis.
Handedness: {handedness.title()}
Coach observations: {observations or 'None supplied'}
{flip}

1. INTENDED FLIGHT VERSUS FAULT
Observed pattern description: {desc}. First ask whether this is the desired flight and whether the ball finishes inside the player's acceptable dispersion. A functional pattern does not require correction.
Teaching objective: {target}

2. ROOT-CAUSE TESTING (BEFORE MAKING A SWING CHANGE)
Ask for intended start/finish, typical miss, shot frequency and current target alignment. Capture 8–10 valid shots with the same target and club.
P1: Check grip, feet/hips/shoulders relative to target, posture, tee height, and ball position (driver typically near lead heel; individualize).
Check strike with impact spray or tape: toe/heel gear effect can alter driver curvature independently of face-to-path.
Compare launch direction, club path, face-to-path, offline distance, carry and strike. Working hypothesis to TEST: {geometry}. Do not assume this is the root cause.
Correct setup/aim first if shown to be responsible; otherwise test one delivery variable at a time.

3. TGM FRAMEWORK
Three imperatives: club-path control, clubface alignment, and timing of the delivery/release. Use measured ball flight to prioritize which imperative needs attention.
Three essentials: stationary head reference (not rigid), balance, and rhythm. Preserve athletic motion.

4. P1–P10 CHECKPOINTS
P1 address: grip, target alignment, ball position, balance.
P2 shaft parallel backswing: takeaway and face organization.
P3 lead arm parallel backswing: arm structure and wrist conditions.
P4 top: balanced pivot and functional face.
P5 lead arm parallel downswing: transition, pelvis/torso sequence.
P6 shaft parallel downswing: delivery direction and face organization.
P7 impact: face/path relationship, strike, low point and dynamic loft.
P8 shaft parallel through: release pattern.
P9 trail arm parallel through: extension and rotation.
P10 finish: stable balance and complete motion.
Prioritize P1, P5, P6, P7; do not prescribe all ten positions as separate corrections. 2D video cannot establish precise 3D angles.

5. TPI BODY–SWING CONNECTION
If motion suggests a limitation, screen lead-hip internal rotation, trail-hip external rotation, thoracic rotation, ankle mobility, single-leg balance, and pelvis/torso sequencing. Do not diagnose physical restrictions from ball flight alone.

6. THREE DRILLS AND PASS/FAIL
A. Start-line gate: soft markers in a safe window several feet ahead; hit 10 controlled shots. Pass: 7/10 through intended start window.
B. Face-to-path calibration: 60–70% swings; alter only the tested delivery priority, verify strike and measured path/face relationship. Pass: 6/10 meet the individually selected face/path window.
C. Target-transfer: normal speed, randomized targets, assess curve and finish. Pass: 7/10 finish in agreed dispersion with acceptable strike/carry.
If the pattern is already functional, emphasize consistency and target-transfer rather than mechanical intervention.

7. 45-MINUTE LESSON
0–5 min: intent, pattern, goals.
5–10 min: P1 setup and strike inspection.
10–15 min: 8–10 shot Garmin baseline.
15–25 min: one root-cause correction and drills A/B.
25–35 min: drill C, progress speed.
35–42 min: randomized 10-shot retest.
42–45 min: document intervention, results and next priority.

8. GARMIN R10 VERIFICATION
Record BEFORE/AFTER averages or distributions: club path (°), clubface (° if available), face-to-path (° if available), launch direction (°), carry (yd), offline (yd), strike location and shot dispersion.
Use only metrics actually supplied by the device or verified from other measurement; never fabricate face angle or spin axis. If unavailable, mark not measured. Keep alignment, ball, device positioning and hitting conditions consistent.
Success means improved intended flight and dispersion without harmful loss of strike or distance, not merely matching illustrative numbers.

9. OUTCOME AND EVIDENCE
No measured outcome yet. Record actual intervention, before/after values, student response, pass/fail and any TPI screen results. Coach must review before treating this plan as validated knowledge.
"""
