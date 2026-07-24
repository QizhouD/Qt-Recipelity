<template>
  <div class="ai-page">
    <section class="hero">
      <div><small>RECIIPELITY AI</small><h1>让灵感变成完整菜谱</h1>
        <p>上传食物照片生成菜谱与营养估算，或把菜谱文字变成封面图。</p></div>
      <el-tag type="warning" effect="plain">AI 结果需人工确认</el-tag>
    </section>
    <el-tabs v-model="tab" class="studio">
      <el-tab-pane label="图片生成菜谱" name="recipe">
        <div class="grid">
          <el-card>
            <template #header><b>1. 上传食物图片</b></template>
            <el-upload drag :auto-upload="false" :limit="1"
              accept="image/jpeg,image/png,image/webp" :on-change="selectFile"
              :on-remove="clearFile">
              <div class="plus">＋</div><div>拖入图片，或点击选择</div>
              <small>JPEG / PNG / WebP，最大 10 MB</small>
            </el-upload>
            <img v-if="preview" :src="preview" class="preview" alt="待分析食物" />
            <el-button type="primary" size="large" class="full" :disabled="!file"
              :loading="analyzing" @click="analyze">生成菜谱</el-button>
          </el-card>
          <el-card>
            <template #header><b>2. 检查生成结果</b></template>
            <el-empty v-if="!draft" description="生成结果将在这里出现" />
            <template v-else>
              <div class="title"><div><h2>{{ draft.name }}</h2><span>{{ draft.cuisine }}</span></div>
                <el-progress type="circle" :width="64"
                  :percentage="Math.round(draft.confidence * 100)" /></div>
              <p>{{ draft.description }}</p>
              <el-alert v-for="warning in draft.warnings" :key="warning" :title="warning"
                type="warning" :closable="false" show-icon />
              <h3>食材</h3><div class="chips"><el-tag v-for="item in draft.ingredients"
                :key="item.name" effect="plain">{{ item.name }} {{ item.amount ?? "" }}{{ item.unit ?? "" }}
              </el-tag></div>
              <h3>步骤</h3><ol><li v-for="step in draft.steps" :key="step.order">
                {{ step.description }}</li></ol>
              <div v-if="draft.nutrition" class="nutrition">
                <span>热量 {{ show(draft.nutrition.calories) }} kcal</span>
                <span>蛋白质 {{ show(draft.nutrition.protein) }} g</span>
                <span>脂肪 {{ show(draft.nutrition.fat) }} g</span>
                <span>碳水 {{ show(draft.nutrition.carbohydrates) }} g</span>
              </div>
              <el-button type="success" size="large" class="full" @click="useDraft">
                编辑并保存菜谱</el-button>
            </template>
          </el-card>
        </div>
      </el-tab-pane>
      <el-tab-pane label="菜谱生成图片" name="image">
        <div class="grid">
          <el-card>
            <template #header><b>1. 输入菜谱</b></template>
            <el-form label-position="top">
              <el-form-item label="菜名"><el-input v-model="form.recipe_name" /></el-form-item>
              <el-form-item label="食材与做法"><el-input v-model="form.recipe_text"
                type="textarea" :rows="10" maxlength="10000" show-word-limit /></el-form-item>
              <el-form-item label="画面风格"><el-select v-model="form.style" class="full">
                <el-option v-for="style in styles" :key="style" :label="style" :value="style" />
              </el-select></el-form-item>
              <el-button type="primary" size="large" class="full" :loading="generating"
                @click="generate">生成菜谱配图</el-button>
            </el-form>
          </el-card>
          <el-card class="image-result">
            <template #header><b>2. 生成结果</b></template>
            <el-empty v-if="!generated" description="配图将在这里出现" />
            <template v-else><img :src="generated.image_url" alt="AI 生成菜谱配图" />
              <p>由 {{ generated.provider }} 生成</p>
              <a :href="generated.image_url" download target="_blank">
                <el-button type="success" class="full">下载图片</el-button></a>
            </template>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, type UploadFile } from "element-plus";
import apiClient from "@/api/client";
import type { AIRecipeDraft, GeneratedImage } from "@/types";

const router = useRouter();
const tab = ref("recipe"), file = ref<File>(), preview = ref("");
const analyzing = ref(false), generating = ref(false);
const draft = ref<AIRecipeDraft>(), generated = ref<GeneratedImage>();
const styles = ["自然美食摄影", "中式餐桌氛围", "极简杂志封面"];
const form = reactive({ recipe_name: "", recipe_text: "", style: styles[0] });
function selectFile(value: UploadFile) {
  if (!value.raw) return; clearFile(); file.value = value.raw;
  preview.value = URL.createObjectURL(value.raw); draft.value = undefined;
}
function clearFile() { file.value = undefined; if (preview.value) URL.revokeObjectURL(preview.value); preview.value = ""; }
function show(value?: number) { return value == null ? "—" : Math.round(value * 10) / 10; }
async function analyze() {
  if (!file.value) return; analyzing.value = true;
  try { const body = new FormData(); body.append("file", file.value);
    draft.value = (await apiClient.post<AIRecipeDraft>("/ai/recipe-from-image", body,
      { timeout: 120000 })).data;
  } catch (e) { ElMessage.error((e as {message?:string}).message || "菜谱生成失败"); }
  finally { analyzing.value = false; }
}
function useDraft() {
  if (!draft.value) return; sessionStorage.setItem("aiRecipeDraft", JSON.stringify(draft.value));
  router.push({ name: "recipe-create", query: { from: "ai" } });
}
async function generate() {
  if (!form.recipe_name.trim() || form.recipe_text.trim().length < 10)
    return void ElMessage.warning("请填写菜名和至少 10 个字的菜谱");
  generating.value = true;
  try { generated.value = (await apiClient.post<GeneratedImage>("/ai/image-from-recipe",
      form, { timeout: 120000 })).data;
  } catch (e) { ElMessage.error((e as {message?:string}).message || "图片生成失败"); }
  finally { generating.value = false; }
}
onBeforeUnmount(clearFile);
</script>

<style scoped>
.ai-page{max-width:1180px;margin:auto}.hero{display:flex;align-items:flex-end;justify-content:space-between;
gap:24px;padding:28px 32px;color:#fff;border-radius:20px;margin-bottom:20px;
background:linear-gradient(135deg,#18233b,#2f6d62)}.hero h1{margin:8px 0;font-size:34px}
.hero p{margin:0;color:#dce8e5}.studio{background:#fff;border-radius:16px;padding:8px 20px 20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:12px}.plus{font-size:36px}
.full{width:100%;margin-top:16px}.preview,.image-result img{width:100%;max-height:360px;
object-fit:cover;border-radius:12px;margin-top:14px}.title{display:flex;justify-content:space-between}
.title h2{margin:0}.chips{display:flex;flex-wrap:wrap;gap:8px}li{margin-bottom:8px;line-height:1.6}
.nutrition{display:grid;grid-template-columns:1fr 1fr;gap:8px;background:#f3f7f5;padding:14px;
border-radius:10px}.el-alert{margin:8px 0}.image-result a{text-decoration:none}
@media(max-width:800px){.grid{grid-template-columns:1fr}.hero{align-items:flex-start;flex-direction:column}
.hero h1{font-size:27px}}
</style>
