<template>
  <div class="recipe-list-page">
    <!-- Loading skeleton -->
    <div v-if="recipeStore.loading && !recipeStore.recipes.length" class="loading-state">
      <el-skeleton :rows="4" animated />
    </div>

    <!-- Error state -->
    <el-result
      v-else-if="recipeStore.error && !recipeStore.recipes.length"
      icon="error"
      title="加载失败"
      :sub-title="recipeStore.error"
    >
      <template #extra>
        <el-button type="primary" @click="recipeStore.fetchRecipes()">重试</el-button>
      </template>
    </el-result>

    <!-- Empty state -->
    <div v-else-if="!recipeStore.loading && !recipeStore.recipes.length" class="empty-state">
      <div class="empty-icon">📋</div>
      <p v-if="hasActiveFilters">没有符合条件的菜谱</p>
      <p v-else>暂无食谱</p>
      <el-button
        v-if="hasActiveFilters"
        type="default"
        @click="clearAllFilters"
      >
        清除筛选条件
      </el-button>
      <el-button
        v-else
        type="primary"
        @click="$router.push('/recipes/new')"
      >
        添加第一个食谱
      </el-button>
    </div>

    <!-- Recipe grid -->
    <template v-else>
      <div class="recipe-grid">
        <RecipeCard
          v-for="r in recipeStore.recipes"
          :key="r.id"
          :recipe="r"
          @click="$router.push(`/recipes/${r.id}`)"
        />
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="pagination">
        <el-pagination
          background
          layout="prev, pager, next"
          :total="recipeStore.total"
          :page-size="recipeStore.pageSize"
          :current-page="recipeStore.page"
          @current-change="onPageChange"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useRecipeStore } from "@/stores/recipe";
import RecipeCard from "@/components/RecipeCard.vue";

const recipeStore = useRecipeStore();
const route = useRoute();
const router = useRouter();

const totalPages = computed(() =>
  Math.max(1, Math.ceil(recipeStore.total / recipeStore.pageSize)),
);

const hasActiveFilters = computed(() => {
  const f = recipeStore.filters;
  return !!(
    f.keyword ||
    f.cuisine ||
    f.tags.length ||
    f.min_time != null ||
    f.max_time != null ||
    f.min_difficulty != null ||
    f.max_difficulty != null
  );
});

// ── URL → Store sync ──────────────────────────────────────────────────
function applyQueryToStore() {
  const q = route.query;
  recipeStore.filters.keyword = (q.keyword as string) || "";
  recipeStore.filters.cuisine = (q.cuisine as string) || "";
  recipeStore.filters.tags = Array.isArray(q.tags)
    ? (q.tags as string[])
    : q.tags
      ? [q.tags as string]
      : [];
  if (q.min_time) recipeStore.filters.min_time = Number(q.min_time);
  else recipeStore.filters.min_time = undefined;
  if (q.max_time) recipeStore.filters.max_time = Number(q.max_time);
  else recipeStore.filters.max_time = undefined;
  if (q.min_difficulty) recipeStore.filters.min_difficulty = Number(q.min_difficulty);
  else recipeStore.filters.min_difficulty = undefined;
  if (q.max_difficulty) recipeStore.filters.max_difficulty = Number(q.max_difficulty);
  else recipeStore.filters.max_difficulty = undefined;
  recipeStore.page = Number(q.page) || 1;
}

function applyStoreToQuery() {
  const q: Record<string, string | string[]> = {};
  const f = recipeStore.filters;
  if (f.keyword) q.keyword = f.keyword;
  if (f.cuisine) q.cuisine = f.cuisine;
  if (f.tags.length) q.tags = f.tags;
  if (f.min_time != null) q.min_time = String(f.min_time);
  if (f.max_time != null) q.max_time = String(f.max_time);
  if (f.min_difficulty != null) q.min_difficulty = String(f.min_difficulty);
  if (f.max_difficulty != null) q.max_difficulty = String(f.max_difficulty);
  if (recipeStore.page > 1) q.page = String(recipeStore.page);

  router.replace({ query: q });
}

// ── Watch route query changes → update store + fetch ──────────────────
watch(
  () => route.query,
  () => {
    applyQueryToStore();
    recipeStore.fetchRecipes();
  },
  { immediate: false },
);

onMounted(() => {
  applyQueryToStore();
  recipeStore.fetchRecipes();
});

// ── User actions → update URL ─────────────────────────────────────────
// Debounced keyword input is handled inside FilterPanel via emit
function onPageChange(p: number) {
  recipeStore.page = p;
  applyStoreToQuery();
  recipeStore.fetchRecipes();
}

function clearAllFilters() {
  recipeStore.resetFilters();
  applyStoreToQuery();
  recipeStore.fetchRecipes();
}
</script>

<style scoped>
.recipe-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}
.loading-state {
  padding: 40px 20px;
}
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #909399;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.empty-state p {
  margin: 8px 0 16px;
  font-size: 16px;
}
.pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

@media (max-width: 640px) {
  .recipe-grid {
    grid-template-columns: 1fr;
  }
}
</style>
