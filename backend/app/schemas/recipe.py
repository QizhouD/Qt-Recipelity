"""Pydantic schemas — the OpenAPI domain contract.

All write endpoints validate through these.  ORM objects are never returned directly.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ── ingredient ───────────────────────────────────────────────────────────────


class IngredientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    amount: float | None = None
    unit: str | None = Field(None, max_length=50)


class IngredientOut(BaseModel):
    id: int
    name: str
    amount: float | None = None
    unit: str | None = None

    model_config = {"from_attributes": True}


# ── step ─────────────────────────────────────────────────────────────────────


class StepCreate(BaseModel):
    order: int = Field(..., ge=0)
    description: str = Field(..., min_length=1)


class StepOut(BaseModel):
    id: int
    order: int
    description: str

    model_config = {"from_attributes": True}


# ── nutrition ────────────────────────────────────────────────────────────────


class NutritionCreate(BaseModel):
    calories: float | None = None
    protein: float | None = None
    fat: float | None = None
    carbohydrates: float | None = None
    fiber: float | None = None
    sugar: float | None = None
    sodium: float | None = None


class NutritionOut(NutritionCreate):
    id: int
    source: str | None = None
    calculated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── tag ──────────────────────────────────────────────────────────────────────


class TagOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# ── recipe ───────────────────────────────────────────────────────────────────


class RecipeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    prep_time: int | None = Field(None, ge=0)
    cook_time: int | None = Field(None, ge=0)
    difficulty: int | None = Field(None, ge=1, le=5)
    cuisine: str | None = Field(None, max_length=100)
    image_url: str | None = Field(None, max_length=500)
    source_url: str | None = Field(None, max_length=500)
    ingredients: list[IngredientCreate] = []
    steps: list[StepCreate] = []
    nutrition: NutritionCreate | None = None
    tags: list[str] = []  # tag names


class RecipeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    prep_time: int | None = Field(None, ge=0)
    cook_time: int | None = Field(None, ge=0)
    difficulty: int | None = Field(None, ge=1, le=5)
    cuisine: str | None = Field(None, max_length=100)
    image_url: str | None = Field(None, max_length=500)
    source_url: str | None = Field(None, max_length=500)
    ingredients: list[IngredientCreate] | None = None
    steps: list[StepCreate] | None = None
    nutrition: NutritionCreate | None = None
    tags: list[str] | None = None


class RecipeSummary(BaseModel):
    """Lightweight recipe for list views."""
    id: int
    name: str
    prep_time: int | None = None
    cook_time: int | None = None
    difficulty: int | None = None
    cuisine: str | None = None
    image_url: str | None = None
    tags: list[TagOut] = []
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class RecipeDetail(BaseModel):
    """Full recipe including ingredients, steps, and nutrition."""
    id: int
    name: str
    description: str | None = None
    prep_time: int | None = None
    cook_time: int | None = None
    total_time: int = 0
    difficulty: int | None = None
    cuisine: str | None = None
    image_url: str | None = None
    source_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    ingredients: list[IngredientOut] = []
    steps: list[StepOut] = []
    nutrition: NutritionOut | None = None
    tags: list[TagOut] = []

    model_config = {"from_attributes": True}


# ── pagination ───────────────────────────────────────────────────────────────


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    pages: int


# ── search / filter ──────────────────────────────────────────────────────────


class RecipeSearchParams(BaseModel):
    keyword: str | None = None
    tags: list[str] | None = None
    cuisine: str | None = None
    min_time: int | None = None
    max_time: int | None = None
    min_difficulty: int | None = Field(None, ge=1, le=5)
    max_difficulty: int | None = Field(None, ge=1, le=5)


# ── URL import ───────────────────────────────────────────────────────────────


class UrlImportRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)


class UrlImportResponse(BaseModel):
    recipe: RecipeCreate


# ── image recognition ───────────────────────────────────────────────────────


class RecognizedIngredient(BaseModel):
    name: str
    amount: float | None = None
    unit: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class RecognizedDish(BaseModel):
    name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    matched_recipe_ids: list[int] = []


class ImageRecognitionResponse(BaseModel):
    dish_candidates: list[RecognizedDish] = []
    ingredients: list[RecognizedIngredient] = []
    provider: str = ""
    warnings: list[str] = []


class AIRecipeDraft(RecipeCreate):
    """Editable recipe draft inferred by a multimodal model."""

    confidence: float = Field(..., ge=0.0, le=1.0)
    warnings: list[str] = []
    provider: str = ""


class GeneratedImageRequest(BaseModel):
    recipe_name: str = Field(..., min_length=1, max_length=200)
    recipe_text: str = Field(..., min_length=10, max_length=10000)
    style: str = Field("自然美食摄影", max_length=100)


class GeneratedImageResponse(BaseModel):
    image_url: str
    provider: str
    revised_prompt: str | None = None


# ── unified error ───────────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict | None = None
    request_id: str | None = None
