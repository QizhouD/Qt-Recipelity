"""Integration tests for recipe CRUD, search, and nutrition."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_recipe(client: AsyncClient):
    payload = {
        "name": "Test Salad",
        "description": "A fresh salad",
        "prep_time": 10,
        "cook_time": 0,
        "difficulty": 1,
        "cuisine": "Western",
        "ingredients": [
            {"name": "Lettuce", "amount": 100, "unit": "g"},
            {"name": "Tomato", "amount": 1, "unit": "piece"},
        ],
        "steps": [
            {"order": 1, "description": "Wash and chop"},
        ],
        "nutrition": {"calories": 50, "protein": 2},
        "tags": ["Quick", "Vegetarian"],
    }

    # Create
    resp = await client.post("/api/v1/recipes", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Salad"
    assert data["total_time"] == 10
    assert len(data["ingredients"]) == 2
    assert len(data["steps"]) == 1
    assert data["nutrition"]["calories"] == 50
    assert {t["name"] for t in data["tags"]} == {"Quick", "Vegetarian"}
    recipe_id = data["id"]

    # Get by ID
    resp = await client.get(f"/api/v1/recipes/{recipe_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Salad"


@pytest.mark.asyncio
async def test_list_recipes_with_filters(client: AsyncClient):
    # Create two recipes
    for i, (name, cuisine) in enumerate([
        ("Salad", "Western"),
        ("Stir Fry", "Chinese"),
    ], 1):
        await client.post("/api/v1/recipes", json={
            "name": name, "cuisine": cuisine, "prep_time": i * 10,
            "ingredients": [], "steps": [],
        })

    # List all
    resp = await client.get("/api/v1/recipes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2

    # Filter by cuisine
    resp = await client.get("/api/v1/recipes?cuisine=Chinese")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["name"] == "Stir Fry"


@pytest.mark.asyncio
async def test_update_recipe(client: AsyncClient):
    # Create
    resp = await client.post("/api/v1/recipes", json={
        "name": "Original", "ingredients": [], "steps": [],
    })
    rid = resp.json()["id"]

    # Update
    resp = await client.patch(f"/api/v1/recipes/{rid}", json={
        "name": "Updated",
        "difficulty": 3,
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"
    assert resp.json()["difficulty"] == 3


@pytest.mark.asyncio
async def test_delete_recipe(client: AsyncClient):
    resp = await client.post("/api/v1/recipes", json={
        "name": "To Delete", "ingredients": [], "steps": [],
    })
    rid = resp.json()["id"]

    resp = await client.delete(f"/api/v1/recipes/{rid}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/recipes/{rid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/recipes/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_tags(client: AsyncClient):
    await client.post("/api/v1/recipes", json={
        "name": "R", "ingredients": [], "steps": [], "tags": ["TagA", "TagB"],
    })
    resp = await client.get("/api/v1/tags")
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()}
    assert names >= {"TagA", "TagB"}


@pytest.mark.asyncio
async def test_list_cuisines(client: AsyncClient):
    await client.post("/api/v1/recipes", json={
        "name": "A", "cuisine": "French", "ingredients": [], "steps": [],
    })
    await client.post("/api/v1/recipes", json={
        "name": "B", "cuisine": "Italian", "ingredients": [], "steps": [],
    })
    resp = await client.get("/api/v1/cuisines")
    assert resp.status_code == 200
    assert set(resp.json()) >= {"French", "Italian"}


@pytest.mark.asyncio
async def test_calculate_nutrition(client: AsyncClient):
    resp = await client.post("/api/v1/recipes", json={
        "name": "Chicken Dish",
        "ingredients": [{"name": "chicken", "amount": 200, "unit": "g"}],
        "steps": [],
    })
    rid = resp.json()["id"]

    resp = await client.post(f"/api/v1/recipes/{rid}/nutrition:calculate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "ingredient_database_estimate"
    # 200g chicken = 2 * 165 = 330 kcal
    assert abs(data["calories"] - 330) < 1
    assert abs(data["protein"] - 40) < 1


@pytest.mark.asyncio
async def test_calculate_chinese_ingredients_and_report_unmatched(client: AsyncClient):
    response = await client.post("/api/v1/recipes", json={
        "name": "番茄炒蛋",
        "ingredients": [
            {"name": "鸡蛋", "amount": 2, "unit": "个"},
            {"name": "番茄", "amount": 200, "unit": "克"},
            {"name": "神秘香料", "amount": 1, "unit": "克"},
        ],
        "steps": [],
    })
    recipe_id = response.json()["id"]
    response = await client.post(f"/api/v1/recipes/{recipe_id}/nutrition:calculate")
    assert response.status_code == 200
    data = response.json()
    assert data["matched_ingredients"] == 2
    assert data["unmatched_ingredients"] == ["神秘香料"]
    assert data["calories"] > 180


@pytest.mark.asyncio
async def test_invalid_recipe_validation(client: AsyncClient):
    resp = await client.post("/api/v1/recipes", json={
        "name": "",
        "ingredients": [],
        "steps": [],
    })
    assert resp.status_code == 422
