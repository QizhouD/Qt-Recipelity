"""Large-model providers for image-to-recipe and recipe-to-image workflows."""

from __future__ import annotations

import asyncio
import base64
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.schemas.recipe import AIRecipeDraft, GeneratedImageRequest


class AIProviderError(RuntimeError):
    pass


class AIRecipeProvider(ABC):
    @abstractmethod
    async def recipe_from_image(self, image: bytes, content_type: str) -> AIRecipeDraft: ...

    @abstractmethod
    async def image_from_recipe(self, request: GeneratedImageRequest) -> tuple[str, str | None]: ...


class OpenAIRecipeProvider(AIRecipeProvider):
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise AIProviderError("未配置 OPENAI_API_KEY，AI 功能暂不可用")

        from openai import OpenAI

        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.ai_request_timeout,
        )

    async def recipe_from_image(self, image: bytes, content_type: str) -> AIRecipeDraft:
        encoded = base64.b64encode(image).decode("ascii")
        prompt = (
            "分析这张食物图片，生成一份可执行的中文菜谱草稿。"
            "食材数量和营养值只能合理估算，并在 warnings 中说明不确定项。"
            "营养值表示整份菜谱，钠单位为 mg，其余宏量营养素为 g，热量为 kcal。"
            "步骤从 1 开始。不要声称识别结果绝对准确。"
        )

        def call() -> AIRecipeDraft:
            response = self.client.responses.parse(
                model=settings.ai_vision_model,
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:{content_type};base64,{encoded}",
                        },
                    ],
                }],
                text_format=AIRecipeDraft,
            )
            draft = response.output_parsed
            if draft is None:
                raise AIProviderError("模型未返回可解析的菜谱")
            draft.provider = f"openai:{settings.ai_vision_model}"
            if draft.nutrition:
                draft.warnings.append("营养数据由模型根据图片估算，仅供参考。")
            return draft

        try:
            return await asyncio.to_thread(call)
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(f"图片生成菜谱失败：{exc}") from exc

    async def image_from_recipe(self, request: GeneratedImageRequest) -> tuple[str, str | None]:
        prompt = (
            f"菜名：{request.recipe_name}\n菜谱：{request.recipe_text}\n"
            f"风格：{request.style}。生成真实、自然、适合作为菜谱封面的成品菜照片。"
            "保持食材与菜谱一致，不添加文字、水印、餐具品牌或人物。"
        )

        def call() -> tuple[str, str | None]:
            result = self.client.images.generate(
                model=settings.ai_image_model,
                prompt=prompt,
                size="1024x1024",
                quality="medium",
            )
            item = result.data[0]
            if not item.b64_json:
                raise AIProviderError("图片模型未返回图像数据")
            target_dir = Path(settings.generated_media_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid4().hex}.png"
            (target_dir / filename).write_bytes(base64.b64decode(item.b64_json))
            return f"/media/{filename}", getattr(item, "revised_prompt", None)

        try:
            return await asyncio.to_thread(call)
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(f"菜谱配图生成失败：{exc}") from exc


def get_ai_provider() -> AIRecipeProvider:
    if settings.ai_provider.lower() != "openai":
        raise AIProviderError(f"不支持的 AI_PROVIDER：{settings.ai_provider}")
    return OpenAIRecipeProvider()
