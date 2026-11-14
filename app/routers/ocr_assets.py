"""Same-origin proxy for Tesseract OCR assets used by Onform screenshot import."""

from __future__ import annotations

import re
from functools import lru_cache
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/media-assets/tesseract", tags=["Tesseract assets"])

TESSERACT_PACKAGE_ROOTS = (
    "https://unpkg.com/tesseract.js@5/dist",
    "https://cdn.jsdelivr.net/npm/tesseract.js@5/dist",
)
TESSERACT_CORE_ROOTS = (
    "https://unpkg.com/tesseract.js-core@5",
    "https://cdn.jsdelivr.net/npm/tesseract.js-core@5",
)
LANGUAGE_DATA_URL = "https://tessdata.projectnaptha.com/4.0.0/eng.traineddata.gz"
MAX_ASSET_BYTES = 40 * 1024 * 1024
CORE_ASSET_NAME = re.compile(
    r"^tesseract-core(?:-(?:simd|lstm|simd-lstm))?\.wasm(?:\.js)?$"
)


def _download(urls: tuple[str, ...] | list[str]) -> bytes:
    last_error: Exception | None = None
    for url in urls:
        try:
            request = Request(url, headers={"User-Agent": "WSBCO-Golf-Coach/1.0"})
            with urlopen(request, timeout=60) as upstream:
                content = upstream.read(MAX_ASSET_BYTES + 1)
            if len(content) > MAX_ASSET_BYTES:
                raise HTTPException(status_code=502, detail="OCR asset exceeds size limit")
            return content
        except HTTPException:
            raise
        except (OSError, URLError) as error:
            last_error = error
    raise HTTPException(
        status_code=502,
        detail=f"OCR asset could not be fetched by the app: {last_error}",
    )


@lru_cache(maxsize=8)
def _fetch_asset(asset_key: str) -> bytes:
    if asset_key == "bundle":
        return _download([f"{root}/tesseract.min.js" for root in TESSERACT_PACKAGE_ROOTS])
    if asset_key == "worker":
        return _download([f"{root}/worker.min.js" for root in TESSERACT_PACKAGE_ROOTS])
    if asset_key == "language":
        return _download([LANGUAGE_DATA_URL])
    if asset_key.startswith("core:"):
        filename = asset_key.partition(":")[2]
        if not CORE_ASSET_NAME.fullmatch(filename):
            raise HTTPException(status_code=404, detail="OCR asset not found")
        return _download([f"{root}/{filename}" for root in TESSERACT_CORE_ROOTS])
    raise HTTPException(status_code=404, detail="OCR asset not found")


def _response(asset_key: str, media_type: str) -> Response:
    return Response(
        _fetch_asset(asset_key),
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/tesseract.min.js")
def tesseract_bundle() -> Response:
    return _response("bundle", "text/javascript")


@router.get("/worker.min.js")
def tesseract_worker() -> Response:
    return _response("worker", "text/javascript")


@router.get("/core/{filename}")
def tesseract_core(filename: str) -> Response:
    media_type = "application/wasm" if filename.endswith(".wasm") else "text/javascript"
    return _response(f"core:{filename}", media_type)


@router.get("/lang/eng.traineddata.gz")
def tesseract_english_data() -> Response:
    return _response("language", "application/gzip")
