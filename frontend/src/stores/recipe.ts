import { defineStore } from "pinia";
import { ref } from "vue";
import apiClient from "@/api/client";
import type {
  Nutrition,
  PaginatedResponse,
  RecipeDetail,
  RecipeSummary,
} from "@/types";

export const useRecipeStore = defineStore("recipe", () => {
  const recipes = ref<RecipeSummary[]>([]);
  const total = ref(0);
  const page = ref(1);
  const pageSize = ref(12);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const currentRecipe = ref<RecipeDetail | null>(null);

  // Current filters
  const filters = ref({
    keyword: "",
    cuisine: "",
    tags: [] as string[],
    min_time: undefined as number | undefined,
    max_time: undefined as number | undefined,
    min_difficulty: undefined as number | undefined,
    max_difficulty: undefined as number | undefined,
  });

  // Request cancellation: abort previous fetch when a new one starts
  let abortController: AbortController | null = null;

  async function fetchRecipes() {
    // Cancel any in-flight request
    if (abortController) {
      abortController.abort();
    }
    abortController = new AbortController();

    loading.value = true;
    error.value = null;
    try {
      const params = new URLSearchParams();
      params.set("page", String(page.value));
      params.set("page_size", String(pageSize.value));
      if (filters.value.keyword) params.set("keyword", filters.value.keyword);
      if (filters.value.cuisine) params.set("cuisine", filters.value.cuisine);
      if (filters.value.min_time != null) params.set("min_time", String(filters.value.min_time));
      if (filters.value.max_time != null) params.set("max_time", String(filters.value.max_time));
      if (filters.value.min_difficulty != null)
        params.set("min_difficulty", String(filters.value.min_difficulty));
      if (filters.value.max_difficulty != null)
        params.set("max_difficulty", String(filters.value.max_difficulty));
      // Tags: append each tag as a separate "tags" entry for repeated query params
      for (const t of filters.value.tags) {
        params.append("tags", t);
      }

      const resp = await apiClient.get<PaginatedResponse<RecipeSummary>>(
        `/recipes?${params.toString()}`,
        { signal: abortController.signal },
      );
      recipes.value = resp.data.items;
      total.value = resp.data.total;
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      error.value = (e as { message?: string })?.message || "加载菜谱失败";
    } finally {
      loading.value = false;
    }
  }

  async function fetchRecipe(id: number) {
    loading.value = true;
    error.value = null;
    try {
      const resp = await apiClient.get<RecipeDetail>(`/recipes/${id}`);
      currentRecipe.value = resp.data;
      return resp.data;
    } catch (e: unknown) {
      error.value = (e as { message?: string })?.message || "加载菜谱详情失败";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createRecipe(data: Record<string, unknown>) {
    const resp = await apiClient.post<RecipeDetail>("/recipes", data);
    return resp.data;
  }

  async function updateRecipe(id: number, data: Record<string, unknown>) {
    const resp = await apiClient.patch<RecipeDetail>(`/recipes/${id}`, data);
    return resp.data;
  }

  async function deleteRecipe(id: number) {
    await apiClient.delete(`/recipes/${id}`);
  }

  async function calculateNutrition(id: number): Promise<Nutrition> {
    const resp = await apiClient.post<Nutrition>(`/recipes/${id}/nutrition:calculate`);
    return resp.data;
  }

  function resetFilters() {
    filters.value = {
      keyword: "",
      cuisine: "",
      tags: [],
      min_time: undefined,
      max_time: undefined,
      min_difficulty: undefined,
      max_difficulty: undefined,
    };
    page.value = 1;
  }

  return {
    recipes,
    total,
    page,
    pageSize,
    loading,
    error,
    currentRecipe,
    filters,
    fetchRecipes,
    fetchRecipe,
    createRecipe,
    updateRecipe,
    deleteRecipe,
    calculateNutrition,
    resetFilters,
  };
});
