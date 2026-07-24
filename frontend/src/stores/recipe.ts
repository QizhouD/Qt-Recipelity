import { defineStore } from "pinia";
import { ref } from "vue";
import apiClient from "@/api/client";
import type {
  PaginatedResponse,
  RecipeDetail,
  RecipeSummary,
} from "@/types";

export const useRecipeStore = defineStore("recipe", () => {
  const recipes = ref<RecipeSummary[]>([]);
  const total = ref(0);
  const page = ref(1);
  const pageSize = ref(20);
  const loading = ref(false);
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

  async function fetchRecipes() {
    loading.value = true;
    try {
      const params: Record<string, string> = {
        page: String(page.value),
        page_size: String(pageSize.value),
      };
      if (filters.value.keyword) params.keyword = filters.value.keyword;
      if (filters.value.cuisine) params.cuisine = filters.value.cuisine;
      if (filters.value.min_time) params.min_time = String(filters.value.min_time);
      if (filters.value.max_time) params.max_time = String(filters.value.max_time);
      if (filters.value.min_difficulty) params.min_difficulty = String(filters.value.min_difficulty);
      if (filters.value.max_difficulty) params.max_difficulty = String(filters.value.max_difficulty);
      filters.value.tags.forEach((t) => {
        params.tags = t; // axios handles repeated params
      });

      const resp = await apiClient.get<PaginatedResponse<RecipeSummary>>(
        "/recipes", { params: { ...params, tags: filters.value.tags } }
      );
      recipes.value = resp.data.items;
      total.value = resp.data.total;
    } finally {
      loading.value = false;
    }
  }

  async function fetchRecipe(id: number) {
    const resp = await apiClient.get<RecipeDetail>(`/recipes/${id}`);
    currentRecipe.value = resp.data;
    return resp.data;
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

  async function calculateNutrition(id: number) {
    const resp = await apiClient.post(`/recipes/${id}/nutrition:calculate`);
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
    recipes, total, page, pageSize, loading, currentRecipe, filters,
    fetchRecipes, fetchRecipe, createRecipe, updateRecipe, deleteRecipe,
    calculateNutrition, resetFilters,
  };
});
