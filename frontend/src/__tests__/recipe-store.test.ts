import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useRecipeStore } from "@/stores/recipe";

// Mock axios
vi.mock("@/api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import apiClient from "@/api/client";

describe("useRecipeStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("initializes with default filters", () => {
    const store = useRecipeStore();
    expect(store.filters.keyword).toBe("");
    expect(store.filters.cuisine).toBe("");
    expect(store.filters.tags).toEqual([]);
    expect(store.page).toBe(1);
    expect(store.loading).toBe(false);
  });

  it("resetFilters clears all filters and resets page", () => {
    const store = useRecipeStore();
    store.filters.keyword = "chicken";
    store.filters.tags = ["tag1"];
    store.page = 3;
    store.resetFilters();
    expect(store.filters.keyword).toBe("");
    expect(store.filters.tags).toEqual([]);
    expect(store.page).toBe(1);
  });

  it("fetchRecipes builds correct URL with filters", async () => {
    const store = useRecipeStore();
    const mockGet = vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0, page: 1, page_size: 12 },
    });

    store.filters.keyword = "test";
    store.filters.tags = ["Quick", "Healthy"];
    await store.fetchRecipes();

    expect(mockGet).toHaveBeenCalledTimes(1);
    const calledUrl = mockGet.mock.calls[0][0] as string;
    expect(calledUrl).toContain("keyword=test");
    expect(calledUrl).toContain("tags=Quick");
    expect(calledUrl).toContain("tags=Healthy");
    expect(calledUrl).toContain("page=1");
  });

  it("fetchRecipes sets error on failure", async () => {
    const store = useRecipeStore();
    vi.mocked(apiClient.get).mockRejectedValue({ message: "Network Error" });

    await store.fetchRecipes();
    expect(store.error).toBe("Network Error");
  });

  it("fetchRecipe returns recipe detail", async () => {
    const store = useRecipeStore();
    const mockRecipe = {
      id: 1,
      name: "Test",
      total_time: 30,
      ingredients: [],
      steps: [],
      tags: [],
    };
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockRecipe });

    const result = await store.fetchRecipe(1);
    expect(result.name).toBe("Test");
    expect(store.currentRecipe?.name).toBe("Test");
  });

  it("createRecipe posts and returns data", async () => {
    const store = useRecipeStore();
    const mockRecipe = { id: 2, name: "New" };
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockRecipe });

    const result = await store.createRecipe({ name: "New" });
    expect(result.id).toBe(2);
    expect(apiClient.post).toHaveBeenCalledWith("/recipes", { name: "New" });
  });

  it("deleteRecipe calls delete endpoint", async () => {
    const store = useRecipeStore();
    vi.mocked(apiClient.delete).mockResolvedValue({});

    await store.deleteRecipe(5);
    expect(apiClient.delete).toHaveBeenCalledWith("/recipes/5");
  });

  it("calculateNutrition returns nutrition data", async () => {
    const store = useRecipeStore();
    const mockNutrition = {
      calories: 300,
      protein: 10,
      matched_ingredients: 3,
      unmatched_ingredients: ["mystery"],
    };
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockNutrition });

    const result = await store.calculateNutrition(1);
    expect(result.matched_ingredients).toBe(3);
    expect(apiClient.post).toHaveBeenCalledWith("/recipes/1/nutrition:calculate");
  });
});
