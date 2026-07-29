"""Safe recipe image upload endpoints."""

from __future__ import annotations

import io
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings

router = APIRouter(prefix="/api/v1/media", tags=["media"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
FORMAT_TO_CONTENT_TYPE = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
FORMAT_TO_EXTENSIONS = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
    "WEBP": {".webp"},
}

# Maximum dimension: reject images larger than this on either axis (sanity check)
MAX_DIMENSION = 8192

_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


def _validate_and_sanitize_filename(original: str) -> str | None:
    """Return a safe base name or None if the extension is not allowed."""
    if "/" in original or "\\" in original:
        return None
    # Strip path separators
    base = Path(original).name
    # Reject empty or suspicious names
    if not base or base.startswith("."):
        return None
    ext = Path(base).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    # Sanitize: allow only safe characters
    safe = _SAFE_FILENAME_RE.sub("_", Path(base).stem)
    if not safe:
        safe = "upload"
    return f"{safe}{ext}"


@router.post("/images")
async def upload_recipe_image(file: UploadFile = File(...)) -> dict[str, str]:
    """Upload a recipe image (JPEG / PNG / WebP, max 5 MB).

    Returns ``{"image_url": "/media/<filename>"}``.
    """
    # ── 1. Content-Type check ───────────────────────────────────────────
    ct = file.content_type or ""
    if ct not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"仅支持 JPEG、PNG 或 WebP 图片，收到: {ct or '未知'}",
        )

    # ── 2. Filename extension check ─────────────────────────────────────
    safe_filename = _validate_and_sanitize_filename(file.filename or "")
    if safe_filename is None:
        raise HTTPException(
            status_code=400,
            detail="文件名不安全或仅支持 .jpg / .jpeg / .png / .webp 文件",
        )
    ext = Path(safe_filename).suffix.lower()

    # ── 3. Read & size check ────────────────────────────────────────────
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="图片为空")
    if len(contents) > settings.image_max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"图片超过大小限制（最大 {settings.image_max_bytes // (1024 * 1024)} MB）",
        )

    # ── 4. Actual image content verification (Pillow) ───────────────────
    try:
        with Image.open(io.BytesIO(contents)) as source:
            image_format = source.format
            expected_content_type = FORMAT_TO_CONTENT_TYPE.get(image_format or "")
            if expected_content_type is None:
                raise HTTPException(status_code=400, detail="图片格式不受支持")
            if ct != expected_content_type or ext not in FORMAT_TO_EXTENSIONS[image_format]:
                raise HTTPException(status_code=400, detail="图片内容、文件名和 MIME 类型不一致")
            source.load()
            w, h = source.size
            if w > MAX_DIMENSION or h > MAX_DIMENSION:
                raise HTTPException(status_code=413, detail="图片尺寸超过限制")
            if w * h > settings.image_max_pixels:
                raise HTTPException(status_code=413, detail="图片像素超过限制")
            # Normalize and resize
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((1920, 1920))
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="图片已损坏或格式不正确") from exc

    # ── 5. Save with secure random name ─────────────────────────────────
    target_dir = Path(settings.media_root)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"recipe-{uuid4().hex}.webp"
    image.save(target_dir / filename, "WEBP", quality=88, method=6)
    return {"image_url": f"/media/{filename}"}
