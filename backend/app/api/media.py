"""Safe recipe image upload endpoints."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings

router = APIRouter(prefix="/api/v1/media", tags=["media"])
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/images")
async def upload_recipe_image(file: UploadFile = File(...)) -> dict[str, str]:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="仅支持 JPEG、PNG 或 WebP 图片")
    contents = await file.read()
    if not contents or len(contents) > settings.image_max_bytes:
        raise HTTPException(status_code=413, detail="图片为空或超过大小限制")
    try:
        with Image.open(io.BytesIO(contents)) as source:
            source.load()
            if source.width * source.height > settings.image_max_pixels:
                raise HTTPException(status_code=413, detail="图片像素超过限制")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((1920, 1920))
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="图片已损坏或格式不正确") from exc

    target_dir = Path(settings.generated_media_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"recipe-{uuid4().hex}.webp"
    image.save(target_dir / filename, "WEBP", quality=88, method=6)
    return {"image_url": f"/media/{filename}"}
