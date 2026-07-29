<template>
  <!-- 404: recipe not found -->
  <el-result
    v-if="notFound"
    icon="warning"
    title="菜谱未找到"
    sub-title="该菜谱可能已被删除或不存在"
  >
    <template #extra>
      <el-button type="primary" @click="$router.push('/recipes')">
        返回菜谱列表
      </el-button>
    </template>
  </el-result>

  <!-- Loading -->
  <div v-else-if="!recipe" class="loading-wrap">
    <el-skeleton :rows="8" animated />
  </div>

  <!-- Recipe detail -->
  <div v-else class="page">
    <div class="toolbar">
      <el-button text @click="$router.back()">← 返回</el-button>
      <div>
        <el-button @click="$router.push(`/recipes/${recipe.id}/edit`)">
          编辑
        </el-button>
        <el-button type="danger" data-testid="btn-delete-recipe" @click="remove">删除</el-button>
      </div>
    </div>
    <div class="layout">
      <main>
        <RecipeImage :src="recipe.image_url" :alt="recipe.name" />
        <div class="content">
          <h1>{{ recipe.name }}</h1>
          <p v-if="recipe.description">{{ recipe.description }}</p>
          <div class="chips">
            <el-tag v-if="recipe.cuisine">{{ recipe.cuisine }}</el-tag>
            <el-tag v-if="recipe.difficulty" type="warning">
              {{ "★".repeat(recipe.difficulty) }}{{ "☆".repeat(5 - recipe.difficulty) }}
            </el-tag>
            <el-tag type="info">⏱ {{ recipe.total_time ?? 0 }} 分钟</el-tag>
            <el-tag v-for="tag in recipe.tags" :key="tag.id" type="info">
              {{ tag.name }}
            </el-tag>
          </div>
          <section v-if="recipe.ingredients.length">
            <h2>🥬 食材</h2>
            <ul>
              <li v-for="item in recipe.ingredients" :key="item.id">
                <b>{{ item.name }}</b>
                <span>{{ item.amount ?? "适量" }} {{ item.unit || "" }}</span>
              </li>
            </ul>
          </section>
          <section v-if="recipe.steps.length">
            <h2>📝 步骤</h2>
            <ol>
              <li v-for="step in recipe.steps" :key="step.id">
                {{ step.description }}
              </li>
            </ol>
          </section>
        </div>
      </main>
      <aside>
        <h2>营养成分估算</h2>
        <NutritionChart v-if="recipe.nutrition" :nutrition="recipe.nutrition" />

        <!-- Unmatched ingredients -->
        <el-alert
          v-if="unmatched.length"
          type="warning"
          :closable="false"
          :title="`未能识别以下食材：${unmatched.join('、')}`"
          show-icon
        />
        <!-- Matched -->
        <el-alert
          v-if="recipe.nutrition?.matched_ingredients != null"
          type="success"
          :closable="false"
          :title="`成功匹配 ${recipe.nutrition.matched_ingredients} 项食材`"
          show-icon
        />
        <!-- Source info -->
        <div v-if="recipe.nutrition" class="nutrition-meta">
          <span v-if="recipe.nutrition.source">
            数据来源：{{
              recipe.nutrition.source === "ingredient_database_estimate"
                ? "食材数据库估算"
                : recipe.nutrition.source === "manual"
                  ? "手动填写"
                  : recipe.nutrition.source
            }}
          </span>
          <span v-if="recipe.nutrition.calculated_at">
            计算时间：{{ new Date(recipe.nutrition.calculated_at).toLocaleString("zh-CN") }}
          </span>
        </div>
        <p class="note">
          根据已填写食材及用量估算整份菜谱。结果仅供参考，不作为医疗或饮食处方。
        </p>
        <!-- Nutrition recalculation hint -->
        <el-alert
          v-if="nutritionStale"
          type="info"
          :closable="false"
          title="食材或用量已修改，建议重新分析营养成分"
          show-icon
        />
        <el-button
          type="primary"
          class="full"
          :loading="analyzing"
          @click="analyze"
        >
          {{ recipe.nutrition ? "重新分析" : "分析营养成分" }}
        </el-button>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import NutritionChart from "@/components/NutritionChart.vue";
import RecipeImage from "@/components/RecipeImage.vue";
import { useRecipeStore } from "@/stores/recipe";
import type { RecipeDetail } from "@/types";

const route = useRoute();
const store = useRecipeStore();
const recipe = ref<RecipeDetail | null>(null);
const analyzing = ref(false);
const unmatched = ref<string[]>([]);
const notFound = ref(false);
const nutritionStale = ref(false);

async function loadRecipe() {
  try {
    recipe.value = await store.fetchRecipe(Number(route.params.id));
    notFound.value = false;
    unmatched.value = recipe.value.nutrition?.unmatched_ingredients || [];
  } catch (e: unknown) {
    const status = (e as { code?: string })?.code;
    if (status === "HTTP_404") {
      notFound.value = true;
    } else {
      ElMessage.error((e as { message?: string })?.message || "菜谱加载失败");
    }
  }
}

onMounted(loadRecipe);

async function remove() {
  try {
    await ElMessageBox.confirm(
      "确定删除这份菜谱吗？删除后无法恢复。",
      "删除确认",
      { type: "warning", confirmButtonText: "确定删除", cancelButtonText: "取消" },
    );
    if (!recipe.value) return;
    await store.deleteRecipe(recipe.value.id);
    ElMessage.success("菜谱已删除");
    // Navigate back to list; replace history so back doesn't return to deleted page
    window.location.replace("/recipes");
  } catch {
    /* user cancelled */
  }
}

async function analyze() {
  if (!recipe.value) return;
  analyzing.value = true;
  try {
    const data = await store.calculateNutrition(recipe.value.id);
    recipe.value.nutrition = {
      ...data,
      id: recipe.value.nutrition?.id || data.id || 0,
    };
    unmatched.value = data.unmatched_ingredients || [];
    nutritionStale.value = false;
    ElMessage.success(`营养分析完成，已匹配 ${data.matched_ingredients ?? 0} 项食材`);
  } catch (e: unknown) {
    ElMessage.error(
      (e as { message?: string })?.message || "营养分析失败",
    );
  } finally {
    analyzing.value = false;
  }
}
</script>

<style scoped>
.page {
  max-width: 1120px;
  margin: auto;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 18px;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 24px;
}
main,
aside {
  background: #fff;
  border-radius: 14px;
  overflow: hidden;
}
aside {
  height: max-content;
  padding: 20px;
  position: sticky;
  top: 20px;
}
.content {
  padding: 24px;
}
.content h1 {
  margin: 0 0 8px;
}
.chips {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  margin-top: 12px;
}
section {
  margin-top: 28px;
}
section h2,
aside h2 {
  font-size: 19px;
}
li {
  margin: 9px 0;
  line-height: 1.6;
}
ul {
  padding: 0;
  list-style: none;
}
ul li {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px dashed #ddd;
  padding-bottom: 7px;
}
.note {
  font-size: 12px;
  color: #87908d;
  line-height: 1.6;
}
.nutrition-meta {
  font-size: 12px;
  color: #909399;
  margin: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.full {
  width: 100%;
  margin-top: 12px;
}
aside .el-alert {
  margin: 12px 0;
}
.loading-wrap {
  max-width: 900px;
  margin: auto;
  padding: 40px 20px;
}
@media (max-width: 780px) {
  .layout {
    grid-template-columns: 1fr;
  }
  aside {
    position: static;
  }
}
</style>
