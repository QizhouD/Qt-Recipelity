"""Recipe business logic — CRUD, search, nutrition.

All functions receive a session rather than using a global one.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.recipe import Ingredient, Nutrition, Recipe, Step, Tag
from app.schemas.recipe import (
    RecipeCreate,
    RecipeSearchParams,
    RecipeUpdate,
)

# ── CRUD ──────────────────────────────────────────────────────────────────────


async def get_recipes(
    db: AsyncSession,
    params: RecipeSearchParams,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Recipe], int]:
    """Paginated recipe list with optional filters."""
    query = select(Recipe).options(
        selectinload(Recipe.tags),
    )

    if params.keyword:
        kw = f"%{params.keyword}%"
        query = query.filter(
            or_(
                Recipe.name.ilike(kw),
                Recipe.description.ilike(kw),
                Recipe.ingredients.any(Ingredient.name.ilike(kw)),
            )
        )
    if params.tags:
        query = query.filter(Recipe.tags.any(Tag.name.in_(params.tags)))
    if params.cuisine:
        query = query.filter(Recipe.cuisine.ilike(f"%{params.cuisine}%"))
    if params.min_time is not None:
        query = query.filter(
            func.coalesce(Recipe.prep_time, 0) + func.coalesce(Recipe.cook_time, 0)
            >= params.min_time
        )
    if params.max_time is not None:
        query = query.filter(
            func.coalesce(Recipe.prep_time, 0) + func.coalesce(Recipe.cook_time, 0)
            <= params.max_time
        )
    if params.min_difficulty is not None:
        query = query.filter(Recipe.difficulty >= params.min_difficulty)
    if params.max_difficulty is not None:
        query = query.filter(Recipe.difficulty <= params.max_difficulty)

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(Recipe.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    recipes = result.unique().scalars().all()

    return list(recipes), total


async def get_recipe_by_id(db: AsyncSession, recipe_id: int) -> Recipe | None:
    """Fetch a single recipe with all relationships eager-loaded."""
    result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.steps),
            selectinload(Recipe.nutrition),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe_id)
    )
    return result.unique().scalar_one_or_none()


async def create_recipe(db: AsyncSession, data: RecipeCreate) -> Recipe:
    """Create a new recipe with all nested relations."""
    recipe = Recipe(
        name=data.name,
        description=data.description,
        prep_time=data.prep_time,
        cook_time=data.cook_time,
        difficulty=data.difficulty,
        cuisine=data.cuisine,
        image_url=data.image_url,
        source_url=data.source_url,
    )

    for ing_data in data.ingredients:
        recipe.ingredients.append(
            Ingredient(name=ing_data.name, amount=ing_data.amount, unit=ing_data.unit)
        )

    for step_data in data.steps:
        recipe.steps.append(
            Step(order=step_data.order, description=step_data.description)
        )

    if data.nutrition:
        recipe.nutrition = Nutrition(
            calories=data.nutrition.calories,
            protein=data.nutrition.protein,
            fat=data.nutrition.fat,
            carbohydrates=data.nutrition.carbohydrates,
            fiber=data.nutrition.fiber,
            sugar=data.nutrition.sugar,
            sodium=data.nutrition.sodium,
            source="manual",
        )

    for tag_name in data.tags:
        tag = (await db.execute(select(Tag).where(Tag.name == tag_name))).scalar_one_or_none()
        if not tag:
            tag = Tag(name=tag_name)
            db.add(tag)
        recipe.tags.append(tag)

    db.add(recipe)
    await db.flush()
    # Re-fetch with eager loading for safe Pydantic validation outside session
    result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.steps),
            selectinload(Recipe.nutrition),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe.id)
    )
    return result.unique().scalar_one()


async def update_recipe(db: AsyncSession, recipe: Recipe, data: RecipeUpdate) -> Recipe:
    """Update an existing recipe. Only fields present in `data` are changed."""

    for field in ("name", "description", "prep_time", "cook_time", "difficulty",
                  "cuisine", "image_url", "source_url"):
        val = getattr(data, field)
        if val is not None:
            setattr(recipe, field, val)

    if data.ingredients is not None:
        recipe.ingredients.clear()
        for ing_data in data.ingredients:
            recipe.ingredients.append(
                Ingredient(name=ing_data.name, amount=ing_data.amount, unit=ing_data.unit)
            )

    if data.steps is not None:
        recipe.steps.clear()
        for step_data in data.steps:
            recipe.steps.append(
                Step(order=step_data.order, description=step_data.description)
            )

    if data.nutrition is not None:
        if recipe.nutrition:
            nut_fields = (
                "calories", "protein", "fat", "carbohydrates", "fiber", "sugar", "sodium"
            )
            for field in nut_fields:
                val = getattr(data.nutrition, field)
                if val is not None:
                    setattr(recipe.nutrition, field, val)
        else:
            recipe.nutrition = Nutrition(
                calories=data.nutrition.calories,
                protein=data.nutrition.protein,
                fat=data.nutrition.fat,
                carbohydrates=data.nutrition.carbohydrates,
                fiber=data.nutrition.fiber,
                sugar=data.nutrition.sugar,
                sodium=data.nutrition.sodium,
                source="manual",
            )

    if data.tags is not None:
        recipe.tags.clear()
        for tag_name in data.tags:
            tag = (await db.execute(select(Tag).where(Tag.name == tag_name))).scalar_one_or_none()
            if not tag:
                tag = Tag(name=tag_name)
                db.add(tag)
            recipe.tags.append(tag)

    await db.flush()
    # Re-fetch with eager loading for safe Pydantic validation
    result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.steps),
            selectinload(Recipe.nutrition),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe.id)
    )
    return result.unique().scalar_one()


async def delete_recipe(db: AsyncSession, recipe: Recipe) -> None:
    await db.delete(recipe)
    await db.flush()


# ── tags & cuisines ───────────────────────────────────────────────────────────


async def get_all_tags(db: AsyncSession) -> list[Tag]:
    result = await db.execute(select(Tag).order_by(Tag.name))
    return list(result.scalars().all())


async def get_all_cuisines(db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(Recipe.cuisine).where(Recipe.cuisine.isnot(None)).distinct()
    )
    return sorted(c for (c,) in result if c)

