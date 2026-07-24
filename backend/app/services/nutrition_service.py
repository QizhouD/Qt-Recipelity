"""Ingredient-based nutrition estimation for recipe imports and manual recipes."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recipe import Nutrition, Recipe

FIELDS = ("calories", "protein", "fat", "carbohydrates", "fiber", "sugar", "sodium")

# Per 100 g: kcal, protein g, fat g, carbohydrate g, fiber g, sugar g, sodium mg.
FOODS: dict[str, tuple[float, ...]] = {
    "chicken": (165, 20, 7.5, 0, 0, 0, 70), "beef": (250, 26, 17, 0, 0, 0, 60),
    "pork": (200, 17, 14, 0, 0, 0, 50), "fish": (120, 20, 3, 0, 0, 0, 40),
    "egg": (155, 13, 11, 1.1, 0, 1.1, 120), "milk": (42, 3.2, 1, 5, 0, 5, 40),
    "rice": (130, 2.7, .3, 28, .3, .1, 1), "noodles": (158, 5.5, 1.6, 30, 2.5, .3, 11),
    "bread": (265, 9, 3.2, 49, 2.7, 5.5, 601), "potato": (77, 2, .1, 17, 2.2, .8, 6),
    "tomato": (18, .9, .2, 4, 1.5, 2.6, 5), "cucumber": (15, .7, .1, 3.6, .5, 1.8, 2),
    "lettuce": (15, 1.4, .2, 2.9, 1.5, .9, 32), "onion": (40, 1.1, .1, 9.3, 1.7, 4.7, 4),
    "carrot": (41, .9, .2, 9.6, 2.8, 4.7, 42), "garlic": (149, 6.4, .5, 33.1, 2.1, 1, 17),
    "ginger": (80, 1.8, .3, 18.6, 2.7, 1.7, 13), "oil": (884, 0, 100, 0, 0, 0, 0),
    "salt": (0, 0, 0, 0, 0, 0, 39300), "sugar": (387, 0, 0, 100, 0, 100, 1),
    "soy sauce": (60, 8, 0, 5, 0, 3, 5700), "vinegar": (11, .1, 0, 2.8, 0, .4, 15),
}
ALIASES = {
    "鸡肉": "chicken", "鸡胸肉": "chicken", "鸡腿肉": "chicken", "牛肉": "beef",
    "猪肉": "pork", "鱼": "fish", "鱼肉": "fish", "鸡蛋": "egg", "蛋": "egg",
    "牛奶": "milk", "米饭": "rice", "大米": "rice", "面条": "noodles", "面包": "bread",
    "土豆": "potato", "马铃薯": "potato", "番茄": "tomato", "西红柿": "tomato",
    "黄瓜": "cucumber", "生菜": "lettuce", "洋葱": "onion", "胡萝卜": "carrot",
    "大蒜": "garlic", "蒜": "garlic", "姜": "ginger", "橄榄油": "oil",
    "食用油": "oil", "油": "oil", "盐": "salt", "糖": "sugar", "白糖": "sugar",
    "酱油": "soy sauce", "生抽": "soy sauce", "老抽": "soy sauce", "醋": "vinegar",
}
PIECE_GRAMS = {"egg": 50, "tomato": 150, "cucumber": 200, "onion": 150,
               "carrot": 100, "potato": 180, "garlic": 5}


def ingredient_grams(name: str, amount: float, unit: str) -> tuple[str, float] | None:
    key = ALIASES.get(name.strip().lower(), name.strip().lower())
    if key not in FOODS:
        return None
    normalized_unit = unit.strip().lower()
    if normalized_unit in {"g", "克", "ml", "毫升"}:
        grams = amount
    elif normalized_unit in {"kg", "千克", "公斤", "l", "升"}:
        grams = amount * 1000
    elif normalized_unit in {"mg", "毫克"}:
        grams = amount / 1000
    elif normalized_unit in {"个", "只", "枚", "颗", "piece", "pieces"}:
        grams = amount * PIECE_GRAMS.get(key, 100)
    elif normalized_unit in {"汤匙", "大勺", "tbsp"}:
        grams = amount * 15
    elif normalized_unit in {"茶匙", "小勺", "tsp"}:
        grams = amount * 5
    else:
        return None
    return key, grams


async def analyze_recipe_nutrition(
    db: AsyncSession, recipe: Recipe
) -> tuple[Nutrition, list[str], int]:
    await db.refresh(recipe, ["ingredients"])
    totals = [0.0] * len(FIELDS)
    unmatched: list[str] = []
    matched = 0
    for ingredient in recipe.ingredients:
        if not ingredient.amount or not ingredient.unit:
            unmatched.append(ingredient.name)
            continue
        converted = ingredient_grams(ingredient.name, ingredient.amount, ingredient.unit)
        if not converted:
            unmatched.append(ingredient.name)
            continue
        key, grams = converted
        matched += 1
        for index, value in enumerate(FOODS[key]):
            totals[index] += value * grams / 100

    values = dict(zip(FIELDS, (round(value, 1) for value in totals), strict=True))
    if recipe.nutrition is None:
        recipe.nutrition = Nutrition(**values)
    else:
        for field, value in values.items():
            setattr(recipe.nutrition, field, value)
    recipe.nutrition.source = "ingredient_database_estimate"
    recipe.nutrition.calculated_at = datetime.now(UTC)
    await db.flush()
    return recipe.nutrition, unmatched, matched
