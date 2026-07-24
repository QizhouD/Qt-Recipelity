<template>
  <div v-if="recipe" class="page">
    <div class="toolbar"><el-button text @click="$router.back()">← 返回</el-button>
      <div><el-button @click="$router.push(`/recipes/${recipe.id}/edit`)">编辑</el-button>
        <el-button type="danger" @click="remove">删除</el-button></div></div>
    <div class="layout">
      <main>
        <RecipeImage :src="recipe.image_url" :alt="recipe.name" />
        <div class="content"><h1>{{ recipe.name }}</h1><p>{{ recipe.description }}</p>
          <div class="chips"><el-tag v-if="recipe.cuisine">{{ recipe.cuisine }}</el-tag>
            <el-tag v-if="recipe.difficulty" type="warning">{{ "★".repeat(recipe.difficulty) }}</el-tag>
            <el-tag type="info">⏱ {{ recipe.total_time }} 分钟</el-tag>
            <el-tag v-for="tag in recipe.tags" :key="tag.id" type="info">{{ tag.name }}</el-tag></div>
          <section><h2>食材</h2><ul><li v-for="item in recipe.ingredients" :key="item.id">
            <b>{{ item.name }}</b><span>{{ item.amount ?? "适量" }} {{ item.unit || "" }}</span>
          </li></ul></section>
          <section><h2>步骤</h2><ol><li v-for="step in recipe.steps" :key="step.id">
            {{ step.description }}</li></ol></section>
        </div>
      </main>
      <aside><h2>营养成分估算</h2>
        <NutritionChart v-if="recipe.nutrition" :nutrition="recipe.nutrition" />
        <el-alert v-if="unmatched.length" type="warning" :closable="false"
          :title="`未能计算：${unmatched.join('、')}`" show-icon />
        <p class="note">根据已填写食材及用量估算整份菜谱。结果仅供参考，不作为医疗或饮食处方。</p>
        <el-button type="primary" class="full" :loading="analyzing" @click="analyze">
          {{ recipe.nutrition ? "重新分析" : "分析营养成分" }}</el-button>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import NutritionChart from "@/components/NutritionChart.vue";
import RecipeImage from "@/components/RecipeImage.vue";
import { useRecipeStore } from "@/stores/recipe";
import type { RecipeDetail } from "@/types";
const route=useRoute(),router=useRouter(),store=useRecipeStore();
const recipe=ref<RecipeDetail|null>(null),analyzing=ref(false),unmatched=ref<string[]>([]);
onMounted(async()=>{try{recipe.value=await store.fetchRecipe(Number(route.params.id))}
catch{ElMessage.error("菜谱加载失败");router.push("/")}});
async function remove(){try{await ElMessageBox.confirm("确定删除这份菜谱吗？","删除确认",
{type:"warning"});await store.deleteRecipe(Number(recipe.value!.id));router.push("/")}
catch{/* cancelled */}}
async function analyze(){analyzing.value=true;try{const data=await store.calculateNutrition(
Number(recipe.value!.id));recipe.value!.nutrition={id:recipe.value!.nutrition?.id||0,...data};
unmatched.value=data.unmatched_ingredients||[];ElMessage.success(
`营养分析完成，已匹配 ${data.matched_ingredients} 项食材`)}
catch(e){ElMessage.error((e as {message?:string}).message||"营养分析失败")}
finally{analyzing.value=false}}
</script>

<style scoped>
.page{max-width:1120px;margin:auto}.toolbar{display:flex;justify-content:space-between;margin-bottom:18px}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:24px}main,aside{background:#fff;
border-radius:14px;overflow:hidden}aside{height:max-content;padding:20px;position:sticky;top:20px}
.content{padding:24px}.content h1{margin:0 0 8px}.chips{display:flex;gap:7px;flex-wrap:wrap}
section{margin-top:28px}section h2,aside h2{font-size:19px}li{margin:9px 0;line-height:1.6}
ul{padding:0;list-style:none}ul li{display:flex;justify-content:space-between;border-bottom:1px dashed #ddd;
padding-bottom:7px}.note{font-size:12px;color:#87908d;line-height:1.6}.full{width:100%;margin-top:12px}
aside .el-alert{margin:12px 0}@media(max-width:780px){.layout{grid-template-columns:1fr}aside{position:static}}
</style>
