import { describe, it, expect, vi } from "vitest";

// ── Mock vue-echarts BEFORE any component that uses it is imported ─────
// (vi.mock calls are hoisted to the top of the file by vitest)
vi.mock("vue-echarts", () => ({
  default: {
    name: "VChart",
    props: ["option", "autoresize"],
    template: '<div class="v-chart-mock" data-testid="echarts-mock"></div>',
  },
}));

import { mount } from "@vue/test-utils";
import { createRouter, createWebHistory } from "vue-router";
import { createPinia, setActivePinia } from "pinia";
import ElementPlus from "element-plus";

// ── RecipeImage fallback ────────────────────────────────────────────────

import RecipeImage from "@/components/RecipeImage.vue";

describe("RecipeImage", () => {
  it("renders image with src", () => {
    const wrapper = mount(RecipeImage, {
      props: { src: "/test.jpg", alt: "Test" },
    });
    const img = wrapper.find("img");
    expect(img.exists()).toBe(true);
    expect(img.attributes("src")).toBe("/test.jpg");
  });

  it("shows fallback when src is empty", () => {
    const wrapper = mount(RecipeImage, { props: { src: "", alt: "No" } });
    const fallback = wrapper.find(".fallback");
    expect(fallback.exists()).toBe(true);
    expect(fallback.text()).toContain("暂无菜谱图片");
  });
});

// ── NutritionChart renders (with mocked ECharts) ────────────────────────

import NutritionChart from "@/components/NutritionChart.vue";

describe("NutritionChart", () => {
  it("renders container div with nutrition data", () => {
    const wrapper = mount(NutritionChart, {
      props: {
        nutrition: {
          id: 1,
          calories: 200,
          protein: 20,
          fat: 10,
          carbohydrates: 30,
          fiber: 5,
          sugar: 2,
          sodium: 100,
          matched_ingredients: 3,
          unmatched_ingredients: ["未知"],
          source: "ingredient_database_estimate",
        },
      },
    });
    const chart = wrapper.find(".nutrition-chart");
    expect(chart.exists()).toBe(true);
    // The mock VChart should be rendered
    expect(wrapper.find('[data-testid="echarts-mock"]').exists()).toBe(true);
  });

  it("renders with zero nutrition values", () => {
    const wrapper = mount(NutritionChart, {
      props: {
        nutrition: {
          id: 1,
          calories: 0,
          protein: 0,
          fat: 0,
          carbohydrates: 0,
        },
      },
    });
    expect(wrapper.find(".nutrition-chart").exists()).toBe(true);
  });
});

// ── NotFound page ───────────────────────────────────────────────────────

import NotFound from "@/views/NotFound.vue";

describe("NotFound", () => {
  it("renders 404 result with back button", () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: "/:pathMatch(.*)", component: NotFound }],
    });
    setActivePinia(createPinia());
    const wrapper = mount(NotFound, {
      global: { plugins: [router, ElementPlus] },
    });
    expect(wrapper.text()).toContain("404");
    expect(wrapper.text()).toContain("返回菜谱列表");
  });
});

// ── About page ──────────────────────────────────────────────────────────

import About from "@/views/About.vue";

describe("About", () => {
  it("renders about page content", () => {
    const wrapper = mount(About, {
      global: { plugins: [ElementPlus] },
    });
    expect(wrapper.text()).toContain("Recipelity");
    expect(wrapper.text()).toContain("营养估算");
    expect(wrapper.text()).toContain("AI 创作");
  });
});
