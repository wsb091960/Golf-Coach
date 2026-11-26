"""Keep image columns backward compatible while new R2 uploads store references.

Existing rows contain raw PNG/JPEG/WEBP bytes. R2 rows contain a short, versioned
marker instead; the object name is never an arbitrary URL or filesystem path.
No existing rows are migrated or deleted by importing this module.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import Response

from app.services.media_storage import MediaStore, r2_enabled

MARKER = b"WSBCO_MEDIA_REF_V1\x00"
CATEGORIES = frozenset({"session_screenshots", "p_position_sheets"})
IMAGE_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
IMAGE_ROOT = Path(__file__).resolve().parents[1] / "media"
logger = logging.getLogger(__name__)


def _store(category: str) -> MediaStore:
    if category not in CATEGORIES:
        raise ValueError("Invalid stored image category")
    return MediaStore(category, IMAGE_ROOT / category)


def image_reference(value: bytes) -> tuple[str, str] | None:
    """Parse only our own constrained marker; raw legacy image bytes pass through."""
    if not value.startswith(MARKER):
        return None
    try:
        if len(value) > 1024:
            raise ValueError("Oversized reference")
        record = json.loads(value[len(MARKER):].decode("utf-8"))
        if not isinstance(record, dict) or set(record) != {"category", "name"}:
            raise ValueError("Invalid reference")
        category, name = record["category"], record["name"]
        if category not in CATEGORIES or not isinstance(name, str):
            raise ValueError("Invalid reference")
        if not re.fullmatch(r"r2__[0-9a-f]{32}\.(?:jpg|png|webp)", name):
            raise ValueError("Invalid reference")
        return category, name
    except (ValueError, TypeError, UnicodeError) as exc:
        raise HTTPException(503, "The saved image reference is invalid") from exc


def store_image_data(data: bytes, content_type: str, category: str) -> bytes:
    """Return raw bytes locally, or a reference after the private R2 write succeeds."""
    if category not in CATEGORIES or content_type not in IMAGE_EXTENSIONS:
        raise ValueError("Invalid stored image type")
    if not r2_enabled():
        return data
    name = f"r2__{uuid4().hex}{IMAGE_EXTENSIONS[content_type]}"
    try:
        _store(category).save_bytes(name, data, content_type)
    except Exception as exc:
        raise HTTPException(503, "Image storage is temporarily unavailable; no image was saved") from exc
    return MARKER + json.dumps({"category": category, "name": name}, separators=(",", ":")).encode("utf-8")


def resolve_image_data(value: bytes) -> bytes:
    reference = image_reference(value)
    if reference is None:
        return value
    category, name = reference
    return _store(category).read_bytes(name)


def image_response(request: Request, value: bytes, content_type: str):
    reference = image_reference(value)
    if reference is None:
        return Response(content=value, media_type=content_type,
                        headers={"Cache-Control": "private, max-age=3600"})
    category, name = reference
    return _store(category).response(request, name, content_type)


def cleanup_image_data(values) -> None:
    """Best effort after rollback/deletion; retain an orphan if storage is offline."""
    for value in values:
        try:
            reference = image_reference(value)
            if reference is not None:
                category, name = reference
                _store(category).delete(name)
        except Exception:
            logger.warning("An external image could not be removed; storage cleanup needs retry")
