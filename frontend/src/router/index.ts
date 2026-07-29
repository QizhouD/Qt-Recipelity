import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/recipes",
    },
    {
      path: "/recipes",
      name: "recipes",
      component: () => import("@/views/RecipeList.vue"),
      meta: { title: "菜谱列表" },
    },
    {
      path: "/recipes/new",
      name: "recipe-create",
      component: () => import("@/views/RecipeForm.vue"),
      meta: { title: "新建菜谱" },
    },
    {
      path: "/recipes/:id",
      name: "recipe-detail",
      component: () => import("@/views/RecipeDetail.vue"),
      meta: { title: "菜谱详情" },
    },
    {
      path: "/recipes/:id/edit",
      name: "recipe-edit",
      component: () => import("@/views/RecipeForm.vue"),
      meta: { title: "编辑菜谱" },
    },
    {
      path: "/ai-studio",
      name: "ai-studio",
      component: () => import("@/views/AIStudio.vue"),
      meta: { title: "AI 创作" },
    },
    {
      path: "/about",
      name: "about",
      component: () => import("@/views/About.vue"),
      meta: { title: "关于" },
    },
    {
      path: "/:pathMatch(.*)*",
      name: "not-found",
      component: () => import("@/views/NotFound.vue"),
      meta: { title: "页面未找到" },
    },
  ],
});

export default router;
