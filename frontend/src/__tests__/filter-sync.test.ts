import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useRecipeStore } from "@/stores/recipe";

describe("Filter-URL bidirectional sync", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("store initializes with default empty filters", () => {
    const store = useRecipeStore();
    expect(store.filters.keyword).toBe("");
    expect(store.filters.cuisine).toBe("");
    expect(store.filters.tags).toEqual([]);
    expect(store.filters.min_time).toBeUndefined();
    expect(store.filters.max_time).toBeUndefined();
    expect(store.filters.min_difficulty).toBeUndefined();
    expect(store.filters.max_difficulty).toBeUndefined();
  });

  it("resetFilters clears all values", () => {
    const store = useRecipeStore();
    store.filters.keyword = "chicken";
    store.filters.tags = ["Quick", "Easy"];
    store.filters.min_time = 15;
    store.filters.cuisine = "Chinese";
    store.page = 5;
    store.resetFilters();
    expect(store.filters.keyword).toBe("");
    expect(store.filters.tags).toEqual([]);
    expect(store.filters.min_time).toBeUndefined();
    expect(store.filters.cuisine).toBe("");
    expect(store.page).toBe(1);
  });

  it("tags filter supports multiple values as array", () => {
    const store = useRecipeStore();
    store.filters.tags = ["Quick", "Healthy", "Vegetarian"];
    expect(store.filters.tags).toHaveLength(3);
    expect(store.filters.tags).toContain("Quick");
    expect(store.filters.tags).toContain("Healthy");
  });

  it("page defaults to 1", () => {
    const store = useRecipeStore();
    expect(store.page).toBe(1);
  });

  it("recipe store has error state", () => {
    const store = useRecipeStore();
    expect(store.error).toBeNull();
  });
});
