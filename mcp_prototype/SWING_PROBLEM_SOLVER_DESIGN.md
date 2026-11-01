# Evidence-based Swing Problem Solver — design specification

Status: development proposal; no production changes.

## User workflow
Coach asks: "How do I fix this student's reverse pivot?"
1. Resolve selected student and session with explicit authorization.
2. Gather FO/DTL videos, P1–P10 annotations, Garmin R10 shots, coach notes, and TPI screen results where actually available.
3. Show an evidence inventory with missing measurements clearly marked. Never invent kinematic or pressure metrics.
4. Assess competing hypotheses: actual reverse-pressure/weight shift, upper-body tilt illusion, centered pivot, camera perspective, mobility/stability constraints, or sequencing problem.
5. Explain observable evidence vs estimates and confidence. A single 2D video cannot establish center-of-pressure movement; R10 launch metrics do not directly diagnose reverse pivot.
6. Evaluate TGM essentials/imperatives, relevant P-position checkpoints, and TPI body-swing screening, without forcing positions beyond physical capacity.
7. Compare with student's prior sessions; optional normative reference must be labeled and match age/skill/club when available.
8. Produce ranked causes, one primary priority, up to five drills with setup and cues, measurable baseline/targets, pass/fail retest and follow-up.
9. Coach approves recommendations; no automatic modification of records.

## Suggested structured response
- question, student/session references, evidence inventory
- observations with sources and timecodes
- competing explanations and confidence limits
- TGM assessment, TPI considerations, P-position findings
- baseline/previous session comparison
- primary correction, drills, cues, objective retest
- warnings/missing evidence

## Architecture
Read-only MCP retrieves authorized structured records. A local rule/measurement layer computes objective comparisons. An AI reasoning layer generates explanations and individualized recommendations. MCP alone is not an AI model; for automatic analysis inside the Golf Coach website, retain an LLM/API integration or explicitly integrate an alternate model runtime. The ChatGPT interface can perform reasoning on retrieved records but does not automatically populate the website.

## Acceptance criteria
- No diagnosis without sufficient evidence; clearly flag uncertain interpretations.
- No fabricated metrics, video landmarks, pressure data, or TPI findings.
- No student PII in logs; enforce owner authorization and audit access.
- Deterministic metric comparisons tested on synthetic sessions.
- Coach can inspect evidence and approve a plan.
- Production stays unchanged until explicit deployment approval.
