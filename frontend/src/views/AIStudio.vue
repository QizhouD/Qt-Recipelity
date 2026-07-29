<template>
  <div class="ai-page">
    <section class="hero">
      <div>
        <small>RECIPELITY AI</small>
        <h1>让灵感变成完整菜谱</h1>
        <p>上传食物照片生成菜谱与营养估算，或把菜谱文字变成封面图。</p>
      </div>
      <el-tag type="warning" effect="plain">AI 结果需人工确认</el-tag>
    </section>

    <el-tabs v-model="tab" class="studio">
      <!-- Tab 1: Image → Recipe -->
      <el-tab-pane label="图片生成菜谱" name="recipe">
        <div class="grid">
          <!-- Upload -->
          <el-card>
            <template #header><b>1. 上传食物图片</b></template>
            <el-upload
              drag
              :auto-upload="false"
              :limit="1"
              accept="image/jpeg,image/png,image/webp"
              :on-change="selectFile"
              :on-remove="clearFile"
              :before-upload="validateImageFile"
            >
              <div class="plus">＋</div>
              <div>拖入图片，或点击选择</div>
              <small>JPEG / PNG / WebP，最大 10 MB</small>
            </el-upload>
            <img
              v-if="preview"
              :src="preview"
              class="preview"
              alt="待分析食物"
            />
            <el-button
              type="primary"
              size="large"
              class="full"
              :disabled="!file"
              :loading="analyzing"
              @click="analyze"
            >
              生成菜谱
            </el-button>
          </el-card>

          <!-- Result -->
          <el-card>
            <template #header><b>2. 检查生成结果</b></template>

            <!-- API not configured -->
            <el-result
              v-if="apiConfigError"
              icon="info"
              title="AI 功能未配置"
              sub-title="请在 .env 中设置 OPENAI_API_KEY 以启用 AI 创作功能。"
            >
              <template #extra>
                <el-button type="primary" @click="$router.push('/about')">
                  查看配置说明
                </el-button>
              </template>
            </el-result>

            <!-- Analyzing -->
            <div v-else-if="analyzing" class="analyzing-hint">
              <el-icon class="is-loading"><span>⟳</span></el-icon>
              <p>AI 正在分析图片，这可能需要 30-60 秒…</p>
            </div>

            <!-- Empty -->
            <el-empty
              v-else-if="!draft && !analyzeError"
              description="生成结果将在这里出现"
            />

            <!-- Error -->
            <el-result
              v-else-if="analyzeError"
              icon="error"
              title="生成失败"
              :sub-title="analyzeError"
            >
              <template #extra>
                <el-button type="primary" @click="analyze">重试</el-button>
              </template>
            </el-result>

            <!-- Draft -->
            <template v-else-if="draft">
              <div class="title">
                <div>
                  <h2>{{ draft.name }}</h2>
                  <span>{{ draft.cuisine }}</span>
                </div>
                <el-progress
                  type="circle"
                  :width="64"
                  :percentage="Math.round(draft.confidence * 100)"
                  :status="draft.confidence < 0.5 ? 'warning' : undefined"
                />
              </div>
              <el-alert
                v-if="draft.confidence < 0.5"
                type="warning"
                :closable="false"
                show-icon
                title="AI 置信度较低，请仔细核对生成结果"
              />
              <p>{{ draft.description }}</p>
              <el-alert
                v-for="warning in draft.warnings"
                :key="warning"
                :title="warning"
                type="warning"
                :closable="false"
                show-icon
              />
              <h3>食材</h3>
              <div class="chips">
                <el-tag
                  v-for="item in draft.ingredients"
                  :key="item.name"
                  effect="plain"
                >
                  {{ item.name }} {{ item.amount ?? "" }}{{ item.unit ?? "" }}
                </el-tag>
              </div>
              <h3>步骤</h3>
              <ol>
                <li v-for="step in draft.steps" :key="step.order">
                  {{ step.description }}
                </li>
              </ol>
              <div v-if="draft.nutrition" class="nutrition">
                <span>热量 {{ show(draft.nutrition.calories) }} kcal</span>
                <span>蛋白质 {{ show(draft.nutrition.protein) }} g</span>
                <span>脂肪 {{ show(draft.nutrition.fat) }} g</span>
                <span>碳水 {{ show(draft.nutrition.carbohydrates) }} g</span>
              </div>
              <el-button
                type="success"
                size="large"
                class="full"
                @click="useDraft"
              >
                编辑并保存菜谱
              </el-button>
            </template>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- Tab 2: Recipe → Image -->
      <el-tab-pane label="菜谱生成图片" name="image">
        <div class="grid">
          <el-card>
            <template #header><b>1. 输入菜谱</b></template>

            <!-- API not configured -->
            <el-result
              v-if="apiConfigError"
              icon="info"
              title="AI 功能未配置"
              sub-title="请在 .env 中设置 OPENAI_API_KEY 以启用 AI 创作功能。"
            />

            <el-form v-else label-position="top">
              <el-form-item label="菜名">
                <el-input
                  v-model="form.recipe_name"
                  placeholder="例如：红烧肉"
                />
              </el-form-item>
              <el-form-item label="食材与做法">
                <el-input
                  v-model="form.recipe_text"
                  type="textarea"
                  :rows="10"
                  maxlength="10000"
                  show-word-limit
                  placeholder="描述食材、用量和烹饪方法…"
                />
              </el-form-item>
              <el-form-item label="画面风格">
                <el-select v-model="form.style" class="full">
                  <el-option
                    v-for="style in styles"
                    :key="style"
                    :label="style"
                    :value="style"
                  />
                </el-select>
              </el-form-item>
              <el-button
                type="primary"
                size="large"
                class="full"
                :loading="generating"
                @click="generate"
              >
                生成菜谱配图
              </el-button>
            </el-form>
          </el-card>

          <!-- Generated image -->
          <el-card class="image-result">
            <template #header><b>2. 生成结果</b></template>
            <el-empty
              v-if="!generated && !generating"
              description="配图将在这里出现"
            />
            <div v-else-if="generating" class="analyzing-hint">
              <el-icon class="is-loading"><span>⟳</span></el-icon>
              <p>正在生成配图，这可能需要 30-60 秒…</p>
            </div>
            <template v-else-if="generated">
              <img
                :src="generated.image_url"
                alt="AI 生成菜谱配图"
              />
              <p>由 {{ generated.provider }} 生成</p>
              <div class="image-actions">
                <el-button
                  type="primary"
                  class="full"
                  @click="downloadImage"
                >
                  下载图片
                </el-button>
              </div>
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
const tab = ref("recipe");
const file = ref<File>();
const preview = ref("");
const analyzing = ref(false);
const generating = ref(false);
const draft = ref<AIRecipeDraft>();
const generated = ref<GeneratedImage>();
const analyzeError = ref<string | null>(null);
const apiConfigError = ref(false);

const styles = ["自然美食摄影", "中式餐桌氛围", "极简杂志封面"];
const form = reactive({
  recipe_name: "",
  recipe_text: "",
  style: styles[0],
});

// ── File handling ──────────────────────────────────────────────────────
function validateImageFile(rawFile: UploadFile) {
  const validTypes = ["image/jpeg", "image/png", "image/webp"];
  if (rawFile.raw && !validTypes.includes(rawFile.raw.type)) {
    ElMessage.error("仅支持 JPEG、PNG、WebP 格式的图片");
    return false;
  }
  if (rawFile.raw && rawFile.raw.size > 10 * 1024 * 1024) {
    ElMessage.error("图片大小不能超过 10 MB");
    return false;
  }
  return true;
}

function selectFile(value: UploadFile) {
  if (!value.raw) return;
  if (!validateImageFile(value)) return;
  clearFile();
  file.value = value.raw;
  preview.value = URL.createObjectURL(value.raw);
  draft.value = undefined;
  analyzeError.value = null;
}

function clearFile() {
  file.value = undefined;
  if (preview.value) URL.revokeObjectURL(preview.value);
  preview.value = "";
}

// ── Helpers ─────────────────────────────────────────────────────────────
function show(value?: number) {
  return value == null ? "—" : Math.round(value * 10) / 10;
}

function handleApiError(e: unknown): string {
  const msg = (e as { message?: string })?.message || "请求失败";
  const code = (e as { code?: string })?.code;
  // Detect unconfigured API key
  if (
    code === "HTTP_503" ||
    msg.toLowerCase().includes("not configured") ||
    msg.toLowerCase().includes("api key") ||
    msg.includes("未配置") ||
    msg.includes("degradation")
  ) {
    apiConfigError.value = true;
    return "AI 功能未配置，请在 .env 中设置 OPENAI_API_KEY";
  }
  return msg;
}

// ── Image → Recipe ──────────────────────────────────────────────────────
async function analyze() {
  if (!file.value) return;
  analyzing.value = true;
  analyzeError.value = null;
  apiConfigError.value = false;
  try {
    const body = new FormData();
    body.append("file", file.value);
    draft.value = (
      await apiClient.post<AIRecipeDraft>("/ai/recipe-from-image", body, {
        timeout: 120000,
      })
    ).data;
  } catch (e: unknown) {
    analyzeError.value = handleApiError(e);
  } finally {
    analyzing.value = false;
  }
}

function useDraft() {
  if (!draft.value) return;
  sessionStorage.setItem("aiRecipeDraft", JSON.stringify(draft.value));
  router.push({ name: "recipe-create", query: { from: "ai" } });
}

// ── Recipe → Image ──────────────────────────────────────────────────────
async function generate() {
  if (!form.recipe_name.trim()) {
    return ElMessage.warning("请填写菜名");
  }
  if (form.recipe_text.trim().length < 10) {
    return ElMessage.warning("请填写至少 10 个字的菜谱描述");
  }
  generating.value = true;
  apiConfigError.value = false;
  try {
    generated.value = (
      await apiClient.post<GeneratedImage>("/ai/image-from-recipe", form, {
        timeout: 120000,
      })
    ).data;
  } catch (e: unknown) {
    handleApiError(e);
    if (!apiConfigError.value) {
      ElMessage.error((e as { message?: string })?.message || "图片生成失败");
    }
  } finally {
    generating.value = false;
  }
}

function downloadImage() {
  if (!generated.value?.image_url) return;
  // Open image in new tab for download
  window.open(generated.value.image_url, "_blank");
}

onBeforeUnmount(clearFile);
</script>

<style scoped>
.ai-page {
  max-width: 1180px;
  margin: auto;
}
.hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 32px;
  color: #fff;
  border-radius: 20px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, #18233b, #2f6d62);
}
.hero h1 {
  margin: 8px 0;
  font-size: 34px;
}
.hero p {
  margin: 0;
  color: #dce8e5;
}
.studio {
  background: #fff;
  border-radius: 16px;
  padding: 8px 20px 20px;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 12px;
}
.plus {
  font-size: 36px;
}
.full {
  width: 100%;
  margin-top: 16px;
}
.preview,
.image-result img {
  width: 100%;
  max-height: 360px;
  object-fit: cover;
  border-radius: 12px;
  margin-top: 14px;
}
.title {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.title h2 {
  margin: 0;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
li {
  margin-bottom: 8px;
  line-height: 1.6;
}
.nutrition {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  background: #f3f7f5;
  padding: 14px;
  border-radius: 10px;
}
.el-alert {
  margin: 8px 0;
}
.analyzing-hint {
  text-align: center;
  padding: 40px 20px;
  color: #909399;
}
.analyzing-hint p {
  margin-top: 12px;
}
.image-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.image-actions .full {
  margin-top: 0;
}
@media (max-width: 800px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .hero {
    align-items: flex-start;
    flex-direction: column;
  }
  .hero h1 {
    font-size: 27px;
  }
}
</style>
