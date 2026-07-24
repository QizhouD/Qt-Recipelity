<template>
  <el-container class="app-layout">
    <el-header class="app-header">
      <div class="header-left">
        <el-button text class="menu-toggle" @click="collapse = !collapse">
          {{ collapse ? "☰" : "×" }}
        </el-button>
        <router-link to="/" class="app-title">Recipelity</router-link>
      </div>
      <div class="header-right">
        <el-button @click="$router.push('/ai-studio')">AI 创作</el-button>
        <el-button type="primary" @click="$router.push('/recipes/new')">添加菜谱</el-button>
      </div>
    </el-header>
    <el-container>
      <el-aside :width="collapse ? '0px' : '260px'" class="app-sidebar">
        <FilterPanel v-if="showFilters" :filters="recipeStore.filters"
          @change="onFilterChange" @reset="onFilterReset" />
      </el-aside>
      <el-main class="app-main"><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import FilterPanel from "@/components/FilterPanel.vue";
import { useRecipeStore } from "@/stores/recipe";

const recipeStore = useRecipeStore();
const route = useRoute();
const collapse = ref(false);
const showFilters = computed(() => route.name === "home");
function onFilterChange() { recipeStore.page = 1; recipeStore.fetchRecipes(); }
function onFilterReset() { recipeStore.resetFilters(); recipeStore.fetchRecipes(); }
</script>

<style scoped>
.app-layout{min-height:100vh}.app-header{display:flex;align-items:center;justify-content:space-between;
background:#fff;border-bottom:1px solid #e4e7ed;padding:0 16px;height:56px}
.header-left,.header-right{display:flex;align-items:center;gap:12px}.app-title{font-size:20px;
font-weight:700;color:#2f6d62;text-decoration:none}.menu-toggle{font-size:20px}.app-sidebar{
background:#fafafa;border-right:1px solid #e4e7ed;overflow-y:auto;transition:width .2s;padding:16px}
.app-main{background:#f5f7fa;min-height:calc(100vh - 56px);padding:20px}
@media(max-width:640px){.app-sidebar{display:none}.app-main{padding:12px}}
</style>
