"""Generative AI endpoints."""

from __future__ import annotations

import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.providers.ai_recipe_provider import AIProviderError, get_ai_provider
from app.schemas.recipe import (
    AIRecipeDraft,
    GeneratedImageRequest,
    GeneratedImageResponse,
)

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def validate_image(contents: bytes, content_type: str | None) -> None:
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="仅支持 JPEG、PNG 或 WebP")
    if not contents or len(contents) > settings.image_max_bytes:
        raise HTTPException(status_code=413, detail="图片为空或超过上传大小限制")
    try:
        with Image.open(io.BytesIO(contents)) as image:
            image.verify()
        with Image.open(io.BytesIO(contents)) as image:
            if image.width * image.height > settings.image_max_pixels:
                raise HTTPException(status_code=413, detail="图片像素超过限制")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="图片文件已损坏或格式不正确") from exc


@router.post("/recipe-from-image", response_model=AIRecipeDraft)
async def recipe_from_image(file: UploadFile = File(...)):
    contents = await file.read()
    validate_image(contents, file.content_type)
    try:
        return await get_ai_provider().recipe_from_image(
            contents, file.content_type or "image/jpeg"
        )
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/image-from-recipe", response_model=GeneratedImageResponse)
async def image_from_recipe(body: GeneratedImageRequest):
    try:
        provider = get_ai_provider()
        image_url, revised_prompt = await provider.image_from_recipe(body)
        return GeneratedImageResponse(
            image_url=image_url,
            provider=f"openai:{settings.ai_image_model}",
            revised_prompt=revised_prompt,
        )
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
