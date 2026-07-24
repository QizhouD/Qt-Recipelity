<template>
  <div class="recipe-list-page">
    <div v-if="recipeStore.loading" class="loading-state">
      <el-icon class="is-loading"><span>⟳</span></el-icon> 加载中...
    </div>

    <div v-else-if="!recipeStore.recipes.length" class="empty-state">
      <div class="empty-icon">📋</div>
      <p>暂无食谱</p>
      <el-button type="primary" @click="$router.push('/recipes/new')">
        添加第一个食谱
      </el-button>
    </div>

    <template v-else>
      <div class="recipe-grid">
        <RecipeCard
          v-for="r in recipeStore.recipes" :key="r.id" :recipe="r"
          @click="$router.push(`/recipes/${r.id}`)"
        />
      </div>

      <div v-if="recipeStore.total > recipeStore.pageSize" class="pagination">
        <el-pagination
          background layout="prev, pager, next"
          :total="recipeStore.total" :page-size="recipeStore.pageSize"
          :current-page="recipeStore.page"
          @current-change="(p: number) => { recipeStore.page = p; recipeStore.fetchRecipes(); }"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useRecipeStore } from "@/stores/recipe";
import RecipeCard from "@/components/RecipeCard.vue";

const recipeStore = useRecipeStore();

onMounted(() => {
  recipeStore.fetchRecipes();
});
</script>

<style scoped>
.recipe-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}
.loading-state, .empty-state { text-align: center; padding: 60px 20px; color: #909399; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state p { margin: 8px 0 16px; font-size: 16px; }
.pagination { display: flex; justify-content: center; margin-top: 24px; }

@media (max-width: 640px) {
  .recipe-grid { grid-template-columns: 1fr; }
}
</style>
