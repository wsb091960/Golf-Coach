from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


SYSTEM_PROMPT = """You are the embedded WSBCO Golf Coach assistant for a PGA professional.
Use an observation-first workflow. Treat Garmin R10 and Onform as secondary verification,
never as prerequisites. Apply The Golfing Machine physics/geometry, TPI body-swing
connection, and P1-P10 checkpoints. Do not diagnose a medical condition. Distinguish a
visible pattern from its possible causes and recommend a TPI screen when physical capacity
may be limiting. Return concise JSON with keys analysis and practice_plan. The practice
plan must contain a priority, a student-friendly explanation, five individually named
drills, a ball-flight cue, a pass/fail test, and reassessment guidance. Answer the coach's actual request directly. When the
coach asks for drills, provide five distinct, practical drills unless another number is
requested. For every drill include setup, action, coaching feel, dosage, and success check.
Do not invent measurements."""


def _falling_backward_plan(goal: str, observations: dict[str, str]) -> dict[str, str]:
    analysis = """Observed pattern: the golfer falls backward or away from the target while completing the finish.

What it may indicate: pressure may remain on the trail foot too long; the pelvis may stop rotating and move toward the ball; or the golfer may lack enough lead-hip rotation, lead-leg balance, ankle mobility, or torso-pelvis separation to accept and stabilize the finish. Treat these as possibilities—not conclusions—until the motion and physical screens are checked.

P-position checkpoints:
• P5: pressure is beginning to favor the lead side while the pelvis starts opening.
• P7: the lead leg accepts pressure without the upper body backing away.
• P8–P10: the pelvis and chest keep turning, the trail heel releases, and the golfer can hold a tall finish over the lead side.

TGM/TPI interpretation: preserve the swing's geometry and low-point control while testing the body-swing connection. Screen lead-hip internal rotation, lead-leg single-leg balance, ankle dorsiflexion, and torso rotation before assuming this is purely technical."""
    plan = """Priority: learn to move pressure to the lead side and keep rotating into a stable P10 finish.

1. Step-Through Finish Drill
Setup: Address the ball normally with a short iron and make a half swing.
Action: After impact, allow the trail foot to step toward the target so it finishes beside or slightly beyond the lead foot.
Feel: Chest, belt buckle, and trail knee travel toward the target together—no leaning away.
Dosage: 5 rehearsals, then 10 balls at 50–60% speed.
Success check: Finish upright without a backward step or loss of balance.

2. Lead-Foot-Back Pressure Drill
Setup: Take normal address, then pull the lead foot back 4–6 inches into a slightly closed, staggered stance.
Action: Make waist-high swings while allowing the lead hip to turn behind you through impact.
Feel: Pressure moves into the lead heel while the lead pocket rotates behind the body.
Dosage: 2 sets of 8 balls.
Success check: Hold P10 for three seconds with the trail toe down and most pressure on the lead foot.

3. Chair/Wall Lead-Hip Drill
Setup: Rehearse without a ball with the lead glute lightly touching the back of a chair or wall.
Action: From P5 through P8, turn the lead hip around and behind you while maintaining light contact.
Feel: The pelvis rotates instead of thrusting toward the ball; the torso stays centered rather than falling backward.
Dosage: 10 slow rehearsals, then 5 half-speed shots.
Success check: The lead hip moves behind the address position without the head or chest backing away.

4. Step-and-Pump Drill
Setup: Begin with the feet close together.
Action: Start the backswing; as the hands approach P3, step the lead foot toward the target, complete the backswing, pump once toward P5, then swing through at 60–70%.
Feel: Pressure arrives on the lead side before the arms accelerate; the lead hip then turns behind you.
Dosage: 5 rehearsals, 5 half-speed balls, then 10 balls at 70%.
Success check: At P5 pressure favors the lead side, and the finish is balanced without a rescue step.

5. Swing-and-Freeze Finish Drill
Setup: Hit a teed-up ball with a 7- or 8-iron at 60–70% speed.
Action: Complete the swing and freeze at P10 for a slow count of five.
Feel: Tall lead side, knees close together, belt buckle and chest facing the target, trail foot balanced on its toe.
Dosage: 10 balls; reset after every shot.
Success check: Pass when 4 of 5 swings can be held for five seconds with no backward sway, hop, or foot adjustment.

Suggested order: Chair/Wall → Lead-Foot-Back → Step-and-Pump → Step-Through → Swing-and-Freeze.

Reassessment: Once the golfer can pass 4 of 5 balanced finishes, use face-on and down-the-line Onform video to check P5, P7, and P10. Garmin data is secondary; use it to confirm that improved balance also improves strike, start direction, and curvature rather than chasing numbers first."""
    return {"analysis": analysis, "practice_plan": plan}


def _fallback(goal: str, observations: dict[str, str], evidence: dict[str, str] | None = None) -> dict[str, str]:
    visible = observations.get("swing_characteristics", "No visual characteristics entered.").strip()
    normalized = f"{goal} {visible}".lower()
    if ("fall" in normalized or "backward" in normalized or "backwards" in normalized) and "finish" in normalized and not evidence:
        return _falling_backward_plan(goal, observations)
    capacity = "; ".join(v for k, v in observations.items() if k in {"mobility", "stability", "balance", "sequencing"} and v.strip())
    evidence_note = ""
    if evidence:
        values = [v.strip() for v in evidence.values() if isinstance(v, str) and v.strip()]
        if values:
            evidence_note = " Evidence supplied for refinement: " + " | ".join(values)
    analysis = (
        f"Goal: {goal or 'Improve the observed motion and ball flight.'}\n"
        f"Observed pattern: {visible}\n"
        "Interpretation: treat the pattern as an observation, not a diagnosis. Confirm setup and strike first, "
        "then identify the earliest P-position where the motion changes."
        + (f"\nBody-swing considerations: {capacity}" if capacity else "") + evidence_note
    )
    plan = (
        "Priority: improve the earliest observable cause rather than the finish symptom.\n"
        "Student explanation: make one small change, then let ball flight tell us whether it helped.\n"
        "Drill: slow-motion rehearsal to the first affected P-position, pause, then swing through in balance.\n"
        "Dosage: 5 rehearsals, 5 half-speed shots, then 5 normal shots; repeat twice.\n"
        "Ball-flight cue: use the student's stated goal; do not chase a launch-monitor number yet.\n"
        "Pass/fail: pass when at least 3 of 5 shots show the intended start/curve and the finish is balanced.\n"
        "Reassessment: add Garmin and Onform evidence only after the preliminary test."
    )
    return {"analysis": analysis, "practice_plan": plan}


class CoachingAIError(RuntimeError):
    pass


def generate(goal: str, observations: dict[str, str], evidence: dict[str, str] | None = None) -> dict[str, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise CoachingAIError("API key is missing from the running server. Add OPENAI_API_KEY and restart the server.")
    payload = {
        "model": os.getenv("OPENAI_COACH_MODEL", "gpt-5.6-luna"),
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"goal": goal, "visual_observations": observations, "secondary_evidence": evidence or {}, "stage": "refined" if evidence else "preliminary"})},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "coaching_plan",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "analysis": {"type": "string"},
                        "practice_plan": {
                            "type": "object",
                            "properties": {
                                "priority": {"type": "string"},
                                "explanation_for_student": {"type": "string"},
                                "drills": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "setup": {"type": "string"},
                                            "action": {"type": "string"},
                                            "feel": {"type": "string"},
                                            "dosage": {"type": "string"},
                                            "success_check": {"type": "string"},
                                        },
                                        "required": ["name", "setup", "action", "feel", "dosage", "success_check"],
                                        "additionalProperties": False,
                                    },
                                },
                                "ball_flight_cue": {"type": "string"},
                                "pass_fail_test": {"type": "string"},
                                "reassessment": {"type": "string"},
                            },
                            "required": ["priority", "explanation_for_student", "drills", "ball_flight_cue", "pass_fail_test", "reassessment"],
                            "additionalProperties": False,
                        },
                    },
                    "required": ["analysis", "practice_plan"],
                    "additionalProperties": False,
                },
            }
        },
    }
    request = urllib.request.Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body: dict[str, Any] = json.loads(response.read().decode())
        for item in body.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    result = json.loads(content.get("text", "{}"))
                    if result.get("analysis") and result.get("practice_plan"):
                        plan = result["practice_plan"]
                        if isinstance(plan, dict):
                            result["practice_plan"] = json.dumps(plan, ensure_ascii=False)
                        return result
    except urllib.error.HTTPError as error:
        messages = {401: "OpenAI rejected the API key. Replace it in the server environment and restart.", 403: "OpenAI denied access. Check project and model permissions.", 404: "OpenAI could not find the requested model or resource. Check model access.", 429: "OpenAI reported a usage limit. Check API credits, billing, and rate limits.", 400: "OpenAI rejected the request format. The integration needs review."}
        raise CoachingAIError(f"HTTP {error.code}: " + messages.get(error.code, "OpenAI request failed. Retry later.")) from None
    except (urllib.error.URLError, TimeoutError):
        raise CoachingAIError("The OpenAI connection failed or timed out. Retry when the connection is available.") from None
    except (ValueError, KeyError, TypeError):
        raise CoachingAIError("OpenAI returned an unreadable response. No new plan was saved.") from None
    raise CoachingAIError("OpenAI returned no usable coaching plan. No new plan was saved.")
