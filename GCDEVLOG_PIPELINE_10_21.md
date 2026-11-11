# GCDevLog — Design-to-Development Pipeline
Updated: 2026-11-10
Project: WSBCO Golf Coach / Golf Coaching Intelligence Engine (GCIE)

This is the numbered continuation of the GCDevLog beginning at #10. These are approved development-pipeline requirements, **not claims of implementation or deployment**. Preserve existing #1–9 numbering and statuses (most recently #4–5 In Progress; #9 Complete). Items begin as Planned; statuses reflect active development. Coach approval is required for instructional knowledge promotion.

| # | Workstream | Status | Priority | Dependencies |
|---|---|---|---|---|
| 10 | FO/DTL Video Viewer & P-Position Utility | In Progress | P0 | Existing #4–5 |
| 11 | Fixed and Dynamic Biomechanical Overlays | Planned — pipeline | P0 | #10 |
| 12 | High-FPS Kinematic Sequence & Biomechanics | Planned — pipeline | P1 | #10–11 |
| 13 | Golf Coaching Intelligence Engine (GCIE) | Planned — pipeline | P0 | Existing student/session workflow |
| 14 | GCIE Knowledge Acquisition Model (KAM) | Planned — pipeline | P0 | #13 |
| 15 | GCIE Structured Knowledge Model (KM) & Retrieval | Planned — pipeline | P0 | #13–14 |
| 16 | PGA Teaching Framework, Preferences & Professional Values | Planned — pipeline | P0 | #13–15 |
| 17 | TGM, TPI, P1–P10 & Ball-Flight Integration | Planned — pipeline | P0 | #16 |
| 18 | Coach-Approved Case Learning & Outcome Analytics | Planned — pipeline | P1 | #14–17 |
| 19 | Interactive 3D Ball-Flight Simulator & Teaching Recommendations | Planned — pipeline | P1 | #16–17 |
| 20 | Student Lesson Report & Video Evidence Workflow | Planned — pipeline | P1 | #10–18 |
| 21 | One-Click P-Sheet Analyzer & X-Factor Approximation | In Progress | P1 | #10, #12 |

## #10 — FO/DTL Video Viewer & P-Position Utility
- Chromebook-first workflow; import uploaded videos and accessible Onform shared links (fallback to uploads if access/download restricted).
- Trim/select start and end; correct orientation/mirroring; frame-by-frame navigation and timestamps; support 120/240-fps iPhone/iPad slow-motion recordings without inventing missing frames.
- Identify P1–P10 in both face-on and down-the-line views, including accurate P7 impact timing; manual adjustment and explicit coach approval; persist frame selections and export evidence.
- Coordinate with existing GCDevLog #4 (in-house video biomechanics) and #5 (automatic P-position detection), without duplicating their scope.
- Current increment: frame-by-frame controls and browser-side pose-assisted candidate timestamps. P2–P9 and P7 require coach review; validate exact P7 contact and shaft-aware accuracy on FO/DTL sample videos before calling automatic detection complete.

## #11 — Fixed and Dynamic Biomechanical Overlays
- Fixed reference lines (address spine angle, head, hip depth, posture) and tracking overlays following landmarks over time.
- Per-overlay Fixed/Tracking toggles, simultaneous modes, color controls, manual correction, save/reload and report export.
- FO and DTL support across P1–P10.

## #12 — High-FPS Kinematic Sequence & Biomechanics
- Use quality FO/DTL 120/240-fps videos for pelvis/torso sequencing, turns, tilts, X-Factor and X-Factor Stretch, and relevant landmark trajectories.
- Show measurement confidence and camera/2D limitations; avoid claiming force-plate ground reaction forces or precise 3D joint angles from ordinary video.
- Reference views inspired by useful Onform/TPI visualizations, without implying proprietary integration.

## #13 — Golf Coaching Intelligence Engine (GCIE)
- Preserve existing FastAPI, database persistence and student/session OpenAI API workflow.
- PGA-guided diagnostic reasoning: observe ball flight, identify applicable law/principle, test the smallest practical safe setup/preference change, measure outcome, escalate only as needed.
- Provide a useful initial recommendation without requiring measured before/after data; refine as evidence arrives.
- Keep separate simulator/MCP pathway distinct from student/session API pathway. Multi-coach-ready architecture with coach-level permissions/provenance; initially learn from the owner's approved cases.

## #14 — Knowledge Acquisition Model (GCIE-KAM)
- Acquire, evaluate, validate, version and incorporate coach-authorized instructional sources and cases.
- Source provenance, quality ratings, competing hypotheses, human review and explicit approval before promoting knowledge.
- Distinguish coach observations/hypotheses from independently verified biomechanics; do not silently treat external videos as validated ground truth.

## #15 — Knowledge Model (GCIE-KM) & Retrieval
- Structured, retrievable representation of PGA framework, teaching preferences, TGM/TPI, P-position evidence, ball-flight laws, interventions, tests, and outcomes.
- RAG/semantic retrieval with citations and evidence strength; retrieve comparable approved cases and show alternatives.
- Design schema and vector search for scalability, longitudinal analytics and eventual validated predictive ranking, not premature causal claims.

## #16 — PGA Teaching Framework, Preferences & Professional Values
- Highest-priority governing instructional authority: PGA PGM teaching philosophy, professional ethics and student-centered values.
- Keep six PGA laws, fourteen principles, and nine ball-flight patterns distinct; record teaching preferences separately from laws/principles.
- Preferences include grip, stance, alignment, posture, ball position, foot flare and student-specific accommodations.
- Always test the smallest safe, measurable preference adjustment first when appropriate; never force body positions beyond student capability.

## #17 — TGM, TPI, P1–P10 & Ball-Flight Integration
- Under the PGA framework, integrate TGM three essentials/imperatives, TPI body-swing screening, P1–P10 checkpoints, modern ball-flight relationships and Garmin R10 metrics.
- Screen lead-hip IR, trail-hip ER, thoracic rotation, lead-leg balance and ankle mobility where relevant.
- Keep interpretations testable and evidence-grounded. Include the coach's Adam Scott P5-to-P6 observation as a coach-authored hypothesis: hands AND club move nearly straight down rather than forward, with trail-arm external rotation associated with shallowing and face control; verify against actual frames before generalizing.

## #18 — Coach-Approved Case Learning & Outcome Analytics
- Structured Coaching Case Record: presenting issue, ball flight, setup, observations, metrics, video/P checkpoints, TPI findings, hypotheses, intervention, before/after results, follow-up and evidence quality.
- Mandatory coach approval for validated case library; compare similar cases, track outcomes and revisions.
- Only consider trained intervention-ranking models after adequate representative data, held-out validation and ongoing monitoring.

## #19 — Interactive 3D Ball-Flight Simulator & Teaching Recommendations
- Visually engaging 3D ball-flight comparison based on manually entered simulator metrics, with before/after toggle and clear simulated/not-measured labeling.
- Offer PGA-aligned explanation of how to produce a desired change, using the coaching reference-guide format; useful as a lesson-marketing demonstration.
- Do not imply exact flight prediction beyond the inputs/model's limits.

## #20 — Student Lesson Report & Video Evidence Workflow
- Integrate saved FO/DTL video, approved P1–P10 frames, overlays, Garmin R10 metrics, coach observations, diagnosis, smallest-change tests and before/after evidence.
- Report follows PGA hierarchy, with distinct six laws, fourteen principles, nine ball flights, preferences, TGM/TPI and biomechanics as relevant.
- Preserve existing print-pagination work: Visual Observation + Swing Problem together; five drills and three topic-matched video links; support persistent evidence and re-extraction.
- Coach reviews/approves lesson conclusions and knowledge promotion.

## #21 — One-Click P-Sheet Analyzer & X-Factor Approximation
- Analyze uploaded FO/DTL P-sheet images with automatic frame, body-landmark and club detection; do not require manual point marking.
- Flag visible candidate patterns with frame evidence, overlay, and confidence: sway/slide, casting or early release, steepening/shallowing, over-the-top delivery, early extension/loss of posture, setup geometry, and finish balance.
- Provide a low/medium/high qualitative estimate of relative thorax/shoulder-to-pelvis rotation near the top of the backswing when visible. Label it as a coarse, view-dependent approximation—not a measured 3D angle or a grade where high is automatically better.
- Prefer matching FO/DTL views of the same swing, automatically phase-align them where possible, and show the supporting frames and assumptions. If the views are unsynchronized or camera geometry is inadequate, report a single-view proxy or “insufficient evidence” instead of fabricating a combined 3D value.
- Include confidence and camera/2D limitations; allow the coach to accept or correct each finding. Apply the PGA framework before recommending instruction, and prioritize the smallest safe, testable change.

## Execution rules
1. Status 'Planned — pipeline' means approved for future development, not completed.
2. No production deployment, data migration or automatic student-data learning is authorized by this planning file.
3. Preserve earlier GCDevLog numbers; cross-reference #4–5 rather than overwriting.
4. Promote items through Planned → In Progress → Verification → Complete with test evidence and coach sign-off.
