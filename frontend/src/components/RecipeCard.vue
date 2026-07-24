<template>
  <el-card class="recipe-card" shadow="hover" @click="$emit('click')">
    <RecipeImage :src="recipe.image_url" :alt="recipe.name" compact />
    <div class="body">
      <h3>{{ recipe.name }}</h3>
      <div class="meta">
        <el-tag v-if="recipe.cuisine" size="small">{{ recipe.cuisine }}</el-tag>
        <span v-if="recipe.difficulty">{{ "★".repeat(recipe.difficulty) }}</span>
        <span v-if="recipe.prep_time || recipe.cook_time">
          ⏱ {{ (recipe.prep_time || 0) + (recipe.cook_time || 0) }} 分钟
        </span>
      </div>
      <div class="tags"><el-tag v-for="tag in recipe.tags" :key="tag.id"
        size="small" type="info">{{ tag.name }}</el-tag></div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import RecipeImage from "@/components/RecipeImage.vue";
import type { RecipeSummary } from "@/types";
defineProps<{ recipe: RecipeSummary }>();
defineEmits<{ click: [] }>();
</script>

<style scoped>
.recipe-card{cursor:pointer;overflow:hidden}.recipe-card :deep(.el-card__body){padding:0}
.body{padding:14px}.body h3{margin:0 0 10px}.meta,.tags{display:flex;align-items:center;
gap:8px;flex-wrap:wrap}.meta{font-size:13px;color:#77807d}.tags{margin-top:9px}
</style>
