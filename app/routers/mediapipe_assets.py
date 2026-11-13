"""Same-origin proxy for the pinned MediaPipe Web assets used by swing review."""

from __future__ import annotations

import re
from functools import lru_cache
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/media-assets/mediapipe", tags=["MediaPipe assets"])

PACKAGE_ROOTS = (
    "https://unpkg.com/@mediapipe/tasks-vision",
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision",
)
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
MAX_ASSET_BYTES = 40 * 1024 * 1024
WASM_NAME = re.compile(r"^vision_wasm(?:_nosimd)?_internal\.(?:js|wasm|data)$")


@lru_cache(maxsize=8)
def _fetch_asset(asset_key: str) -> bytes:
    if asset_key == "bundle":
        urls = [f"{root}/vision_bundle.mjs" for root in PACKAGE_ROOTS]
    elif asset_key == "model":
        urls = [MODEL_URL]
    elif asset_key.startswith("wasm:"):
        filename = asset_key.partition(":")[2]
        if not WASM_NAME.fullmatch(filename):
            raise HTTPException(status_code=404, detail="MediaPipe asset not found")
        urls = [f"{root}/wasm/{filename}" for root in PACKAGE_ROOTS]
    else:
        raise HTTPException(status_code=404, detail="MediaPipe asset not found")

    last_error: Exception | None = None
    for url in urls:
        try:
            request = Request(url, headers={"User-Agent": "WSBCO-Golf-Coach/1.0"})
            with urlopen(request, timeout=60) as upstream:
                content = upstream.read(MAX_ASSET_BYTES + 1)
            if len(content) > MAX_ASSET_BYTES:
                raise HTTPException(status_code=502, detail="MediaPipe asset exceeds size limit")
            return content
        except HTTPException:
            raise
        except (OSError, URLError) as error:
            last_error = error
    raise HTTPException(
        status_code=502,
        detail=f"MediaPipe asset could not be fetched by the app: {last_error}",
    )


def _asset_response(asset_key: str, media_type: str) -> Response:
    return Response(
        _fetch_asset(asset_key),
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/vision_bundle.mjs")
def vision_bundle() -> Response:
    return _asset_response("bundle", "text/javascript")


@router.get("/wasm/{filename}")
def vision_wasm(filename: str) -> Response:
    media_type = "application/wasm" if filename.endswith(".wasm") else "text/javascript"
    return _asset_response(f"wasm:{filename}", media_type)


@router.get("/pose_landmarker_lite.task")
def pose_landmarker_model() -> Response:
    return _asset_response("model", "application/octet-stream")
