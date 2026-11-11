from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request


class PSheetAnalysisError(RuntimeError):
    pass


SYSTEM_PROMPT = """You analyze golf P-position contact sheets for a PGA golf coach.
The six PGA Laws and fourteen Principles govern all instructional interpretation. This is a visual screening aid, not a diagnosis and not a substitute for the coach.

The uploaded images are labeled P1-P10 and may be face-on (FO) or down-the-line (DTL). Read titles and labels carefully. Report only patterns clearly visible in the images. Treat P positions as candidate labels if frame content does not match.

Look for visible candidate patterns: sway/slide; casting or early release; shaft steepening/shallowing; over-the-top delivery; early extension/loss of posture; setup geometry; and finish balance. Do not state a root cause or prescribe a correction. Cite the frame labels and view for every finding. Use confidence low/moderate/high and explain what the coach should verify.

For X-Factor, the actual measure is 3D relative axial rotation of thorax and pelvis. Ordinary 2D P-sheets cannot establish an exact 3D angle. If shoulder and pelvis orientation are both visible near the top, provide only a broad, view-dependent approximate range in degrees, state the view and assumptions, and label it an approximation. If views are unsynchronized, obstructed, or insufficient, return no numeric range and explain why. Never manufacture a number.

Return only the requested JSON object. Be concise and evidence-specific."""


SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fault_id": {"type": "string"},
                    "title": {"type": "string"},
                    "observation": {"type": "string"},
                    "view": {"type": "string"},
                    "evidence_positions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "confidence": {"type": "string"},
                    "coach_check": {"type": "string"},
                },
                "required": [
                    "fault_id", "title", "observation", "view",
                    "evidence_positions", "confidence", "coach_check",
                ],
                "additionalProperties": False,
            },
        },
        "x_factor": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "approximate_range_degrees": {
                    "type": ["array", "null"],
                    "items": {"type": "number"},
                },
                "view": {"type": "string"},
                "confidence": {"type": "string"},
                "explanation": {"type": "string"},
                "evidence_positions": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "status", "approximate_range_degrees", "view",
                "confidence", "explanation", "evidence_positions",
            ],
            "additionalProperties": False,
        },
        "limitations": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["summary", "findings", "x_factor", "limitations"],
    "additionalProperties": False,
}


def analyze(sheets: list[dict]) -> tuple[dict, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise PSheetAnalysisError("The coaching analysis API key is not configured.")

    total_bytes = sum(len(sheet["image_data"]) for sheet in sheets)
    if total_bytes > 18 * 1024 * 1024:
        raise PSheetAnalysisError("The selected sheets exceed the 18 MB analysis limit.")

    content = [{
        "type": "input_text",
        "text": "Review these session P-sheets. Treat each image as a separate camera view unless the labels establish otherwise. Sheet titles: "
        + "; ".join(sheet["title"] for sheet in sheets),
    }]
    for sheet in sheets:
        encoded = base64.b64encode(sheet["image_data"]).decode("ascii")
        content.append({
            "type": "input_image",
            "image_url": f"data:{sheet['content_type']};base64,{encoded}",
            "detail": "high",
        })

    model = os.getenv("OPENAI_COACH_MODEL", "gpt-5.6-luna").strip()
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": content},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "p_sheet_swing_screen",
                "strict": True,
                "schema": SCHEMA,
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=75) as response:
            body = json.loads(response.read().decode("utf-8"))
        for item in body.get("output", []):
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    return json.loads(part.get("text", "{}")), model
    except urllib.error.HTTPError as error:
        if error.code == 429:
            message = "The coaching analysis API reported a usage limit."
        elif error.code in {401, 403}:
            message = "The coaching analysis API key or model access needs attention."
        else:
            message = f"The coaching analysis API returned HTTP {error.code}."
        raise PSheetAnalysisError(message) from None
    except (urllib.error.URLError, TimeoutError):
        raise PSheetAnalysisError("The coaching analysis request timed out or could not connect.") from None
    except (ValueError, KeyError, TypeError):
        raise PSheetAnalysisError("The coaching analysis API returned an unreadable response.") from None
    raise PSheetAnalysisError("The coaching analysis API returned no usable analysis.")
