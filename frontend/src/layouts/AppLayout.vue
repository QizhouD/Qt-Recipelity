<template>
  <el-container class="app-layout">
    <el-header class="app-header">
      <div class="header-left">
        <el-button class="menu-toggle" text @click="toggleDrawer">
          {{ mobileDrawer ? "×" : "☰" }}
        </el-button>
        <router-link to="/recipes" class="app-title">Recipelity</router-link>
      </div>
      <div class="header-right">
        <el-button text @click="$router.push('/about')">关于</el-button>
        <el-button text @click="$router.push('/ai-studio')">AI 创作</el-button>
        <el-button type="primary" @click="$router.push('/recipes/new')">
          添加菜谱
        </el-button>
      </div>
    </el-header>
    <el-container class="body-container">
      <!-- Desktop sidebar -->
      <el-aside
        v-if="showFilters && !isMobile"
        :width="collapse ? '0px' : '260px'"
        class="app-sidebar desktop-only"
      >
        <FilterPanel
          v-show="!collapse"
          :filters="recipeStore.filters"
          @change="onFilterChange"
          @reset="onFilterReset"
        />
      </el-aside>
      <!-- Mobile drawer -->
      <el-drawer
        v-model="mobileDrawer"
        title="筛选条件"
        direction="ltr"
        size="280px"
        :close-on-click-modal="true"
      >
        <FilterPanel
          :filters="recipeStore.filters"
          @change="onMobileFilterChange"
          @reset="onMobileFilterReset"
        />
      </el-drawer>
      <el-main class="app-main">
        <div v-if="recipeStore.loading" class="global-loading-bar">
          <div class="loading-bar-inner" />
        </div>
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import FilterPanel from "@/components/FilterPanel.vue";
import { useRecipeStore } from "@/stores/recipe";

const recipeStore = useRecipeStore();
const route = useRoute();
const collapse = ref(false);
const mobileDrawer = ref(false);

const isMobile = computed(() => window.innerWidth <= 768);
const showFilters = computed(() => {
  return route.name === "recipes" || route.path === "/recipes";
});

// Update document title from route meta
watch(
  () => route.meta?.title,
  (title) => {
    document.title = title ? `${title} — Recipelity` : "Recipelity";
  },
  { immediate: true },
);

function toggleDrawer() {
  if (isMobile.value) {
    mobileDrawer.value = !mobileDrawer.value;
  } else {
    collapse.value = !collapse.value;
  }
}

function onFilterChange() {
  recipeStore.page = 1;
  recipeStore.fetchRecipes();
}

function onMobileFilterChange() {
  recipeStore.page = 1;
  recipeStore.fetchRecipes();
  mobileDrawer.value = false;
}

function onFilterReset() {
  recipeStore.resetFilters();
  recipeStore.fetchRecipes();
}

function onMobileFilterReset() {
  recipeStore.resetFilters();
  recipeStore.fetchRecipes();
  mobileDrawer.value = false;
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 16px;
  height: 56px;
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.app-title {
  font-size: 20px;
  font-weight: 700;
  color: #2f6d62;
  text-decoration: none;
}
.menu-toggle {
  font-size: 20px;
}
.body-container {
  min-height: calc(100vh - 56px);
}
.app-sidebar {
  background: #fafafa;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
  transition: width 0.2s;
  padding: 16px;
}
.app-main {
  background: #f5f7fa;
  min-height: calc(100vh - 56px);
  padding: 20px;
  position: relative;
}
.global-loading-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: #e4e7ed;
  overflow: hidden;
  z-index: 10;
}
.loading-bar-inner {
  height: 100%;
  width: 40%;
  background: #2f6d62;
  animation: loading-slide 1.2s ease-in-out infinite;
}
@keyframes loading-slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(350%); }
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .desktop-only {
    display: none;
  }
  .app-main {
    padding: 12px;
  }
  .header-right .el-button--primary {
    padding: 5px 12px;
    font-size: 13px;
  }
}
</style>
