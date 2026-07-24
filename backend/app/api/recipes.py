"""Recipe CRUD + search + nutrition API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.recipe import (
    PaginatedResponse,
    RecipeCreate,
    RecipeDetail,
    RecipeSearchParams,
    RecipeSummary,
    RecipeUpdate,
)
from app.services.nutrition_service import analyze_recipe_nutrition
from app.services.recipe_service import (
    create_recipe,
    delete_recipe,
    get_all_cuisines,
    get_all_tags,
    get_recipe_by_id,
    get_recipes,
    update_recipe,
)

router = APIRouter(prefix="/api/v1", tags=["recipes"])


@router.get("/recipes", response_model=PaginatedResponse)
async def list_recipes(
    keyword: str | None = Query(None),
    tags: list[str] | None = Query(None),
    cuisine: str | None = Query(None),
    min_time: int | None = Query(None),
    max_time: int | None = Query(None),
    min_difficulty: int | None = Query(None, ge=1, le=5),
    max_difficulty: int | None = Query(None, ge=1, le=5),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    search = RecipeSearchParams(
        keyword=keyword, tags=tags, cuisine=cuisine,
        min_time=min_time, max_time=max_time,
        min_difficulty=min_difficulty, max_difficulty=max_difficulty,
    )
    recipes, total = await get_recipes(db, search, page=page, page_size=page_size)
    import math
    return PaginatedResponse(
        items=[RecipeSummary.model_validate(r) for r in recipes],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.post("/recipes", response_model=RecipeDetail, status_code=201)
async def add_recipe(data: RecipeCreate, db: AsyncSession = Depends(get_db)):
    recipe = await create_recipe(db, data)
    return RecipeDetail.model_validate(recipe)


@router.get("/recipes/{recipe_id}", response_model=RecipeDetail)
async def get_recipe(recipe_id: int, db: AsyncSession = Depends(get_db)):
    recipe = await get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RecipeDetail.model_validate(recipe)


@router.patch("/recipes/{recipe_id}", response_model=RecipeDetail)
async def patch_recipe(recipe_id: int, data: RecipeUpdate, db: AsyncSession = Depends(get_db)):
    recipe = await get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    recipe = await update_recipe(db, recipe, data)
    return RecipeDetail.model_validate(recipe)


@router.delete("/recipes/{recipe_id}", status_code=204)
async def remove_recipe(recipe_id: int, db: AsyncSession = Depends(get_db)):
    recipe = await get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    await delete_recipe(db, recipe)


@router.get("/tags")
async def list_tags(db: AsyncSession = Depends(get_db)):
    tags = await get_all_tags(db)
    return [{"id": t.id, "name": t.name} for t in tags]


@router.get("/cuisines")
async def list_cuisines(db: AsyncSession = Depends(get_db)):
    return await get_all_cuisines(db)


@router.post("/recipes/{recipe_id}/nutrition:calculate")
async def calc_nutrition(recipe_id: int, db: AsyncSession = Depends(get_db)):
    recipe = await get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    nutrition, unmatched, matched = await analyze_recipe_nutrition(db, recipe)
    return {
        "calories": nutrition.calories,
        "protein": nutrition.protein,
        "fat": nutrition.fat,
        "carbohydrates": nutrition.carbohydrates,
        "fiber": nutrition.fiber,
        "sugar": nutrition.sugar,
        "sodium": nutrition.sodium,
        "source": nutrition.source,
        "calculated_at": nutrition.calculated_at.isoformat() if nutrition.calculated_at else None,
        "matched_ingredients": matched,
        "unmatched_ingredients": unmatched,
    }
