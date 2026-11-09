"""Conservative selection of shaft candidates using coach-verified references.

A candidate is never marked verified by this function. Ambiguous or missing
references cause abstention, rather than fabricated clubhead measurements.
"""
from __future__ import annotations
from math import hypot, isfinite


def select_candidate(candidates, grip, reference_head=None, *, max_head_error_px=35,
                     min_separation_px=12):
    """Select only when a verified reference disambiguates the candidates.

    reference_head must be a coach-verified head at THIS frame; this is a
    candidate matching/validation tool, not a temporal predictor.
    """
    if reference_head is None:
        return {"status": "needs_verified_reference", "selected": None, "verified": False}
    if len(grip) != 2 or len(reference_head) != 2 or not all(isfinite(float(x)) for x in [*grip, *reference_head]):
        raise ValueError("Reference coordinates must be finite 2D points")
    if hypot(reference_head[0]-grip[0], reference_head[1]-grip[1]) < 8:
        raise ValueError("Reference shaft too short")
    ranked = []
    for candidate in candidates:
        head = candidate.get("clubhead_candidate")
        if not isinstance(head, (list, tuple)) or len(head) != 2:
            continue
        if not all(isfinite(float(x)) for x in head):
            continue
        error = hypot(head[0]-reference_head[0], head[1]-reference_head[1])
        ranked.append((error, candidate))
    ranked.sort(key=lambda row: row[0])
    if not ranked or ranked[0][0] > max_head_error_px:
        return {"status": "no_matching_candidate", "selected": None, "verified": False}
    if len(ranked) > 1 and ranked[1][0]-ranked[0][0] < min_separation_px:
        return {"status": "ambiguous_candidates", "selected": None, "verified": False,
                "best_error_px": round(ranked[0][0], 2)}
    return {"status": "candidate_matches_reference", "selected": ranked[0][1],
            "head_error_px": round(ranked[0][0], 2), "verified": False}
