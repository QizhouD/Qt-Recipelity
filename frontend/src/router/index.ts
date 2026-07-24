import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("@/views/RecipeList.vue"),
    },
    {
      path: "/recipes/new",
      name: "recipe-create",
      component: () => import("@/views/RecipeForm.vue"),
    },
    {
      path: "/recipes/:id",
      name: "recipe-detail",
      component: () => import("@/views/RecipeDetail.vue"),
    },
    {
      path: "/recipes/:id/edit",
      name: "recipe-edit",
      component: () => import("@/views/RecipeForm.vue"),
    },
    {
      path: "/ai-studio",
      name: "ai-studio",
      component: () => import("@/views/AIStudio.vue"),
    },
  ],
});

export default router;
