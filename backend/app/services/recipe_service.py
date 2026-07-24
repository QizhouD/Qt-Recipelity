"""Recipe business logic — CRUD, search, import, nutrition.

All functions receive a session rather than using a global one.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.recipe import Ingredient, Nutrition, Recipe, Step, Tag
from app.schemas.recipe import (
    RecipeCreate,
    RecipeSearchParams,
    RecipeUpdate,
)

logger = logging.getLogger(__name__)

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


# ── URL import ────────────────────────────────────────────────────────────────


# Hardcoded food nutrition database (per 100g values) — cal, pro, fat, carb, fib, sug, sod
def _nf(  # noqa: E501
    cal: float, pro: float, fat: float, carb: float, fib: float, sug: float, sod: float
) -> dict[str, float]:
    return {
        "calories": cal, "protein": pro, "fat": fat, "carbohydrates": carb,
        "fiber": fib, "sugar": sug, "sodium": sod,
    }

# fmt: off
_FOOD_RAW: dict[str, tuple] = {
    # English names
    "chicken":    (165, 20, 7.5, 0, 0, 0, 70),
    "beef":       (250, 26, 17, 0, 0, 0, 60),
    "pork":       (200, 17, 14, 0, 0, 0, 50),
    "fish":       (120, 20, 3, 0, 0, 0, 40),
    "egg":        (155, 13, 11, 1.1, 0, 1.1, 120),
    "milk":       (42, 3.2, 1, 5, 0, 5, 40),
    "rice":       (130, 2.7, 0.3, 28, 0.3, 0.1, 1),
    "noodles":    (158, 5.5, 1.6, 30, 2.5, 0.3, 11),
    "bread":      (265, 9, 3.2, 49, 2.7, 5.5, 601),
    "potato":     (77, 2, 0.1, 17, 2.2, 0.8, 6),
    "tomato":     (18, 0.9, 0.2, 4, 1.5, 2.6, 5),
    "cucumber":   (15, 0.7, 0.1, 3.6, 0.5, 1.8, 2),
    "lettuce":    (15, 1.4, 0.2, 2.9, 1.5, 0.9, 32),
    "onion":      (40, 1.1, 0.1, 9.3, 1.7, 4.7, 4),
    "carrot":     (41, 0.9, 0.2, 9.6, 2.8, 4.7, 42),
    "garlic":     (149, 6.4, 0.5, 33.1, 2.1, 1.0, 17),
    "ginger":     (80, 1.8, 0.3, 18.6, 2.7, 1.7, 13),
    "olive oil":  (884, 0, 100, 0, 0, 0, 0),
    "salt":       (0, 0, 0, 0, 0, 0, 39300),
    "sugar":      (387, 0, 0, 100, 0, 100, 1),
    "soy sauce":  (60, 8, 0, 5, 0, 3, 5700),
    "vinegar":    (11, 0.1, 0, 2.8, 0, 0.4, 15),
    # Chinese aliases
    "鸡肉": (165, 20, 7.5, 0, 0, 0, 70),
    "牛肉": (250, 26, 17, 0, 0, 0, 60),
    "猪肉": (200, 17, 14, 0, 0, 0, 50),
    "鱼":   (120, 20, 3, 0, 0, 0, 40),
    "鸡蛋": (155, 13, 11, 1.1, 0, 1.1, 120),
    "牛奶": (42, 3.2, 1, 5, 0, 5, 40),
    "米饭": (130, 2.7, 0.3, 28, 0.3, 0.1, 1),
    "面条": (158, 5.5, 1.6, 30, 2.5, 0.3, 11),
    "面包": (265, 9, 3.2, 49, 2.7, 5.5, 601),
    "土豆": (77, 2, 0.1, 17, 2.2, 0.8, 6),
    "番茄": (18, 0.9, 0.2, 4, 1.5, 2.6, 5),
    "黄瓜": (15, 0.7, 0.1, 3.6, 0.5, 1.8, 2),
    "生菜": (15, 1.4, 0.2, 2.9, 1.5, 0.9, 32),
    "洋葱": (40, 1.1, 0.1, 9.3, 1.7, 4.7, 4),
    "胡萝卜": (41, 0.9, 0.2, 9.6, 2.8, 4.7, 42),
    "青椒": (20, 0.9, 0.2, 4.6, 1.8, 2.4, 2),
    "红椒": (25, 1.5, 0.3, 5.5, 1.9, 4.2, 3),
    "大蒜": (149, 6.4, 0.5, 33.1, 2.1, 1.0, 17),
    "姜":   (80, 1.8, 0.3, 18.6, 2.7, 1.7, 13),
    "橄榄油": (884, 0, 100, 0, 0, 0, 0),
    "盐":   (0, 0, 0, 0, 0, 0, 39300),
    "糖":   (387, 0, 0, 100, 0, 100, 1),
    "酱油": (60, 8, 0, 5, 0, 3, 5700),
    "醋":   (11, 0.1, 0, 2.8, 0, 0.4, 15),
    "生抽": (60, 8, 0, 5, 0, 3, 5700),
    "老抽": (50, 4, 0, 8, 0, 4, 6000),
    "料酒": (20, 0.5, 0, 2, 0, 1, 5),
}
# fmt: on

FOOD_NUTRITION_DB: dict[str, dict[str, float]] = {
    k: _nf(*v) for k, v in _FOOD_RAW.items()
}


async def import_recipe_from_url(url: str) -> RecipeCreate:
    """Fetch and parse a recipe from a URL. Returns validated RecipeCreate data."""

    # Prevent SSRF: block internal addresses
    from urllib.parse import urlparse
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    blocked = {
        "localhost", "127.0.0.1", "0.0.0.0", "::1",
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
    }
    if hostname in blocked or hostname.startswith(("10.", "172.16.", "192.168.")):
        raise ValueError(f"URL with internal host is not allowed: {hostname}")

    async with httpx.AsyncClient(timeout=settings.import_request_timeout) as client:
        resp = await client.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Recipelity/0.1)"},
            follow_redirects=True,
        )
        resp.raise_for_status()
        # Truncate response to configured limit
        html = resp.text[: settings.import_max_response_bytes]

    soup = BeautifulSoup(html, "html.parser")

    # Detect site
    if "meishichina.com" in hostname:
        data = _parse_meishichina(soup, url)
    elif "xiachufang.com" in hostname:
        data = _parse_xiachufang(soup, url)
    elif "douguo.com" in hostname:
        data = _parse_douguo(soup, url)
    else:
        data = _parse_generic(soup, url)

    if not data.get("name"):
        raise ValueError("Could not extract recipe name from the page")

    return RecipeCreate(**data)


def _parse_meishichina(soup: BeautifulSoup, url: str) -> dict:
    data: dict = {}
    title = soup.find("h1", class_="recipe_De_title")
    if title:
        data["name"] = title.get_text(strip=True)
    desc = soup.find("div", class_="recipe_De_desc")
    if desc:
        data["description"] = desc.get_text(strip=True)

    img = soup.find("img", class_="recipe_De_img")
    if img and img.get("src"):
        from urllib.parse import urljoin
        data["image_url"] = urljoin(url, img["src"])

    ingredients = []
    for tag in soup.find_all("li", class_="recipe_ingredients_item"):
        name_tag = tag.find("span", class_="recipe_ingredients_name")
        if name_tag:
            ing = {"name": name_tag.get_text(strip=True)}
            amount_tag = tag.find("span", class_="recipe_ingredients_unit")
            if amount_tag:
                m = re.search(r"(\d+\.?\d*)\s*([^\d]+)", amount_tag.get_text(strip=True))
                if m:
                    ing["amount"] = float(m.group(1))
                    ing["unit"] = m.group(2).strip()
            ingredients.append(ing)
    data["ingredients"] = ingredients

    steps = []
    for i, tag in enumerate(soup.find_all("li", class_="recipe_step_item"), 1):
        desc_tag = tag.find("div", class_="recipe_step_txt")
        if desc_tag:
            steps.append({"order": i, "description": desc_tag.get_text(strip=True)})
    data["steps"] = steps

    return data


def _parse_xiachufang(soup: BeautifulSoup, url: str) -> dict:
    data: dict = {}
    title = soup.find("h1", class_="page-title")
    if title:
        data["name"] = title.get_text(strip=True)
    desc = soup.find("div", class_="desc mt30")
    if desc:
        data["description"] = desc.get_text(strip=True)

    ingredients = []
    for tag in soup.find_all("li", class_="ingredient"):
        name_tag = tag.find("span", class_="name")
        if name_tag:
            ing = {"name": name_tag.get_text(strip=True)}
            amount_tag = tag.find("span", class_="amount")
            if amount_tag:
                m = re.search(r"(\d+\.?\d*)\s*([^\d]+)", amount_tag.get_text(strip=True))
                if m:
                    ing["amount"] = float(m.group(1))
                    ing["unit"] = m.group(2).strip()
            ingredients.append(ing)
    data["ingredients"] = ingredients

    steps = []
    for i, tag in enumerate(soup.find_all("li", class_="step"), 1):
        desc_tag = tag.find("p", class_="text")
        if desc_tag:
            steps.append({"order": i, "description": desc_tag.get_text(strip=True)})
    data["steps"] = steps

    return data


def _parse_douguo(soup: BeautifulSoup, url: str) -> dict:
    data: dict = {}
    title = soup.find("h1", class_="recipe-title")
    if title:
        data["name"] = title.get_text(strip=True)
    desc = soup.find("div", class_="recipe-description")
    if desc:
        data["description"] = desc.get_text(strip=True)

    img = soup.find("img", class_="recipe-img")
    if img and img.get("src"):
        from urllib.parse import urljoin
        data["image_url"] = urljoin(url, img["src"])

    ingredients = []
    for tag in soup.find_all("li", class_="ingredient-item"):
        name_tag = tag.find("span", class_="ingredient-name")
        if name_tag:
            ing = {"name": name_tag.get_text(strip=True)}
            amount_tag = tag.find("span", class_="ingredient-amount")
            if amount_tag:
                m = re.search(r"(\d+\.?\d*)\s*([^\d]+)", amount_tag.get_text(strip=True))
                if m:
                    ing["amount"] = float(m.group(1))
                    ing["unit"] = m.group(2).strip()
            ingredients.append(ing)
    data["ingredients"] = ingredients

    steps = []
    for i, tag in enumerate(soup.find_all("li", class_="step-item"), 1):
        desc_tag = tag.find("div", class_="step-description")
        if desc_tag:
            steps.append({"order": i, "description": desc_tag.get_text(strip=True)})
    data["steps"] = steps

    return data


def _parse_generic(soup: BeautifulSoup, url: str) -> dict:
    data: dict = {}
    from urllib.parse import urljoin

    # Title
    for sel in ["h1", "h2.title", "div.recipe-title", "meta[property='og:title']"]:
        tag = soup.select_one(sel)
        if tag:
            data["name"] = (tag.get("content") or tag.get_text(strip=True))
            break

    # Description
    for sel in ["meta[property='og:description']", "div.description", "div.recipe-description"]:
        tag = soup.select_one(sel)
        if tag:
            data["description"] = (tag.get("content") or tag.get_text(strip=True))
            break

    # Image
    for sel in ["meta[property='og:image']", "img.recipe-image", "img.main-image"]:
        tag = soup.select_one(sel)
        if tag:
            src = tag.get("content") or tag.get("src")
            if src:
                data["image_url"] = urljoin(url, src)
                break

    # Ingredients — search containers with ingredient-related class names
    ingredients = []
    seen = set()
    for container in soup.find_all(["ul", "div"], class_=re.compile(r"ingredient|材料|食材", re.I)):
        for li in container.find_all("li"):
            text = li.get_text(strip=True)
            if text and len(text) < 200 and text not in seen:
                seen.add(text)
                m = re.search(r"(\d+\.?\d*)\s*([^\d]+)", text)
                if m:
                    ingredients.append({"name": m.group(2).strip(), "amount": float(m.group(1))})
                else:
                    ingredients.append({"name": text})
    data["ingredients"] = ingredients

    # Steps — search containers with step-related class names
    steps = []
    for container in soup.find_all(["ol", "ul", "div"], class_=re.compile(r"step|步骤|做法", re.I)):
        for i, li in enumerate(container.find_all("li"), 1):
            text = li.get_text(strip=True)
            if text and len(text) < 1000:
                steps.append({"order": i, "description": text})
    data["steps"] = steps

    return data


# ── nutrition calculation ─────────────────────────────────────────────────────


async def calculate_nutrition(db: AsyncSession, recipe: Recipe) -> Nutrition:
    """Calculate nutrition from ingredients using the hardcoded database.

    If the recipe already has manual nutrition data, return it unchanged.
    """
    from datetime import datetime

    if recipe.nutrition and recipe.nutrition.source == "manual":
        return recipe.nutrition

    totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbohydrates": 0.0,
              "fiber": 0.0, "sugar": 0.0, "sodium": 0.0}

    unmatched: list[str] = []
    await db.refresh(recipe, ["ingredients"])

    for ing in recipe.ingredients:
        # Try exact match first, then case-insensitive
        food = FOOD_NUTRITION_DB.get(ing.name) or FOOD_NUTRITION_DB.get(ing.name.lower())
        if not food or not ing.amount or not ing.unit:
            unmatched.append(ing.name)
            continue

        weight = ing.amount
        unit_lower = ing.unit.lower()
        if unit_lower in ("g", "克", "ml"):
            weight = ing.amount
        elif unit_lower in ("kg", "千克", "l"):
            weight = ing.amount * 1000
        elif unit_lower in ("mg", "毫克"):
            weight = ing.amount / 1000
        # else: treat as-is (individual pieces, etc.)

        ratio = weight / 100
        for key in totals:
            totals[key] += food[key] * ratio

    if recipe.nutrition:
        for key in totals:
            setattr(recipe.nutrition, key, round(totals[key], 1))
        recipe.nutrition.source = "calculated"
        recipe.nutrition.calculated_at = datetime.now(UTC)
    else:
        recipe.nutrition = Nutrition(
            calories=round(totals["calories"], 1),
            protein=round(totals["protein"], 1),
            fat=round(totals["fat"], 1),
            carbohydrates=round(totals["carbohydrates"], 1),
            fiber=round(totals["fiber"], 1),
            sugar=round(totals["sugar"], 1),
            sodium=round(totals["sodium"], 1),
            source="calculated",
            calculated_at=datetime.now(UTC),
        )

    await db.flush()
    return recipe.nutrition
