<template>
  <div class="recipe-form-page">
    <div class="form-header">
      <el-button text @click="goBack">← 返回</el-button>
      <h2>{{ isEdit ? "编辑菜谱" : "新建菜谱" }}</h2>
    </div>

    <el-card class="form-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="菜名" prop="name">
              <el-input v-model="form.name" placeholder="例如：红烧肉" @input="markDirty" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="菜系">
              <el-input v-model="form.cuisine" placeholder="例如：中式、西式" @input="markDirty" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="简短的描述..."
            @input="markDirty"
          />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="准备时间（分钟）">
              <el-input-number
                v-model="form.prep_time"
                :min="0"
                style="width: 100%"
                @change="markDirty"
              />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="烹饪时间（分钟）">
              <el-input-number
                v-model="form.cook_time"
                :min="0"
                style="width: 100%"
                @change="markDirty"
              />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="难度 (1-5)">
              <el-input-number
                v-model="form.difficulty"
                :min="1"
                :max="5"
                style="width: 100%"
                @change="markDirty"
              />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="图片">
              <!-- Image URL preview -->
              <img
                v-if="form.image_url"
                :src="form.image_url"
                class="form-image-preview"
                alt="菜谱图片预览"
                @error="onImageError"
              />
              <el-upload
                :show-file-list="false"
                :auto-upload="false"
                accept="image/jpeg,image/png,image/webp"
                :on-change="uploadImage"
                :before-upload="validateFile"
              >
                <el-button :loading="uploading" style="margin-top: 8px">
                  {{ form.image_url ? "更换图片" : "上传图片" }}
                </el-button>
              </el-upload>
              <el-button
                v-if="form.image_url"
                text
                type="danger"
                size="small"
                style="margin-top: 4px"
                @click="removeImage"
              >
                移除图片
              </el-button>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="标签">
          <el-select
            v-model="form.tags"
            multiple
            filterable
            allow-create
            placeholder="添加标签..."
            style="width: 100%"
            @change="markDirty"
          >
            <el-option v-for="t in form.tags" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>

        <!-- Ingredients -->
        <div class="array-section">
          <div class="array-header">
            <h4>🥬 食材</h4>
            <el-alert
              v-if="nutritionStale"
              type="info"
              :closable="false"
              title="食材已修改，保存后需重新分析营养"
              show-icon
            />
          </div>
          <div v-for="(ing, i) in form.ingredients" :key="i" class="array-row">
            <el-input v-model="ing.name" placeholder="食材名" style="flex: 2" @input="markDirty" />
            <el-input-number
              v-model="ing.amount"
              :min="0"
              placeholder="数量"
              style="flex: 1"
              @change="markDirty"
            />
            <el-input v-model="ing.unit" placeholder="单位" style="flex: 1" @input="markDirty" />
            <el-button
              type="default"
              :icon="'↑'"
              text
              :disabled="i === 0"
              @click="moveIngredient(i, -1)"
            />
            <el-button
              type="default"
              :icon="'↓'"
              text
              :disabled="i === form.ingredients.length - 1"
              @click="moveIngredient(i, 1)"
            />
            <el-button type="danger" text @click="removeIngredient(i)">✕</el-button>
          </div>
          <el-button @click="addIngredient">+ 添加食材</el-button>
        </div>

        <!-- Steps -->
        <div class="array-section">
          <h4>📝 步骤</h4>
          <div v-for="(step, i) in form.steps" :key="i" class="array-row step-row">
            <span class="step-order">{{ i + 1 }}</span>
            <el-input
              v-model="step.description"
              placeholder="步骤描述..."
              style="flex: 1"
              @input="markDirty"
            />
            <el-button
              type="default"
              :icon="'↑'"
              text
              :disabled="i === 0"
              @click="moveStep(i, -1)"
            />
            <el-button
              type="default"
              :icon="'↓'"
              text
              :disabled="i === form.steps.length - 1"
              @click="moveStep(i, 1)"
            />
            <el-button type="danger" text @click="removeStep(i)">✕</el-button>
          </div>
          <el-button @click="addStep">+ 添加步骤</el-button>
        </div>

        <div class="form-actions">
          <el-button @click="goBack">取消</el-button>
          <el-button
            type="primary"
            native-type="submit"
            :loading="submitting"
            data-testid="btn-submit-recipe"
          >
            {{ isEdit ? "保存修改" : "创建菜谱" }}
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox, type FormInstance, type UploadFile } from "element-plus";
import apiClient from "@/api/client";
import { useRecipeStore } from "@/stores/recipe";

const route = useRoute();
const router = useRouter();
const recipeStore = useRecipeStore();
const formRef = ref<FormInstance>();

const isEdit = computed(() => route.name === "recipe-edit");
const submitting = ref(false);
const uploading = ref(false);
const dirty = ref(false);
const nutritionStale = ref(false);
const imageError = ref(false);

const form = reactive({
  name: "",
  description: "",
  prep_time: undefined as number | undefined,
  cook_time: undefined as number | undefined,
  difficulty: undefined as number | undefined,
  cuisine: "",
  image_url: "",
  ingredients: [] as { name: string; amount?: number; unit?: string }[],
  steps: [] as { order: number; description: string }[],
  tags: [] as string[],
  nutrition: undefined as
    | {
        calories?: number;
        protein?: number;
        fat?: number;
        carbohydrates?: number;
        fiber?: number;
        sugar?: number;
        sodium?: number;
      }
    | undefined,
});

const rules = {
  name: [
    { required: true, message: "请输入菜名", trigger: "blur" },
    { max: 200, message: "菜名不能超过 200 个字符", trigger: "blur" },
  ],
};

function markDirty() {
  dirty.value = true;
  nutritionStale.value = true;
}

// ── Image ──────────────────────────────────────────────────────────────
function validateFile(file: UploadFile) {
  const validTypes = ["image/jpeg", "image/png", "image/webp"];
  if (file.raw && !validTypes.includes(file.raw.type)) {
    ElMessage.error("仅支持 JPEG、PNG、WebP 格式的图片");
    return false;
  }
  if (file.raw && file.raw.size > 10 * 1024 * 1024) {
    ElMessage.error("图片大小不能超过 10 MB");
    return false;
  }
  return true;
}

async function uploadImage(file: UploadFile) {
  if (!file.raw) return;
  if (!validateFile(file)) return;
  uploading.value = true;
  try {
    const body = new FormData();
    body.append("file", file.raw);
    const response = await apiClient.post<{ image_url: string }>("/media/images", body, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 30000,
    });
    form.image_url = response.data.image_url;
    imageError.value = false;
    ElMessage.success("图片上传成功");
    markDirty();
  } catch (error) {
    ElMessage.error((error as { message?: string }).message || "图片上传失败");
  } finally {
    uploading.value = false;
  }
}

function removeImage() {
  form.image_url = "";
  imageError.value = false;
  markDirty();
}

function onImageError() {
  imageError.value = true;
}

// ── Ingredients ────────────────────────────────────────────────────────
function addIngredient() {
  form.ingredients.push({ name: "", amount: undefined, unit: "" });
  markDirty();
}
function removeIngredient(i: number) {
  form.ingredients.splice(i, 1);
  markDirty();
}
function moveIngredient(i: number, dir: number) {
  const target = i + dir;
  if (target < 0 || target >= form.ingredients.length) return;
  const tmp = form.ingredients[i];
  form.ingredients[i] = form.ingredients[target];
  form.ingredients[target] = tmp;
  markDirty();
}

// ── Steps ──────────────────────────────────────────────────────────────
function addStep() {
  form.steps.push({ order: form.steps.length + 1, description: "" });
  markDirty();
}
function removeStep(i: number) {
  form.steps.splice(i, 1);
  markDirty();
}
function moveStep(i: number, dir: number) {
  const target = i + dir;
  if (target < 0 || target >= form.steps.length) return;
  const tmp = form.steps[i];
  form.steps[i] = form.steps[target];
  form.steps[target] = tmp;
  markDirty();
}

// ── Navigation guard ────────────────────────────────────────────────────
function goBack() {
  if (dirty.value) {
    ElMessageBox.confirm(
      "表单已修改，离开后将丢失所有更改。确定离开吗？",
      "未保存的更改",
      { type: "warning", confirmButtonText: "确定离开", cancelButtonText: "继续编辑" },
    )
      .then(() => router.back())
      .catch(() => {});
  } else {
    router.back();
  }
}

// Browser back/forward guard
function beforeUnload(e: BeforeUnloadEvent) {
  if (dirty.value) {
    e.preventDefault();
    e.returnValue = "";
  }
}

onMounted(async () => {
  window.addEventListener("beforeunload", beforeUnload);

  if (isEdit.value) {
    try {
      const recipe = await recipeStore.fetchRecipe(Number(route.params.id));
      Object.assign(form, {
        name: recipe.name,
        description: recipe.description || "",
        prep_time: recipe.prep_time,
        cook_time: recipe.cook_time,
        difficulty: recipe.difficulty,
        cuisine: recipe.cuisine || "",
        image_url: recipe.image_url || "",
        ingredients: recipe.ingredients.map((i) => ({
          name: i.name,
          amount: i.amount,
          unit: i.unit || "",
        })),
        steps: recipe.steps.map((s) => ({
          order: s.order,
          description: s.description,
        })),
        tags: recipe.tags.map((t) => t.name),
      });
      dirty.value = false;
      nutritionStale.value = false;
    } catch {
      ElMessage.error("加载菜谱失败");
      router.push("/recipes");
    }
  } else if (route.query.from === "ai") {
    const raw = sessionStorage.getItem("aiRecipeDraft");
    if (raw) {
      try {
        const draft = JSON.parse(raw);
        Object.assign(form, {
          name: draft.name || "",
          description: draft.description || "",
          prep_time: draft.prep_time,
          cook_time: draft.cook_time,
          difficulty: draft.difficulty,
          cuisine: draft.cuisine || "",
          image_url: draft.image_url || "",
          ingredients: draft.ingredients || [],
          steps: draft.steps || [],
          tags: draft.tags || [],
          nutrition: draft.nutrition,
        });
        sessionStorage.removeItem("aiRecipeDraft");
        dirty.value = true;
        ElMessage.warning("这是 AI 生成的草稿，请核对所有内容后再保存");
      } catch {
        sessionStorage.removeItem("aiRecipeDraft");
      }
    }
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", beforeUnload);
});

// ── Submit ─────────────────────────────────────────────────────────────
async function handleSubmit() {
  submitting.value = true;
  try {
    // Re-number steps consecutively
    const steps = form.steps
      .filter((s) => s.description.trim())
      .map((s, i) => ({ order: i + 1, description: s.description.trim() }));

    const ingredients = form.ingredients.filter((i) => i.name.trim());

    // Validate at least one ingredient and one step
    if (!ingredients.length) {
      ElMessage.warning("请至少添加一项食材");
      submitting.value = false;
      return;
    }
    if (!steps.length) {
      ElMessage.warning("请至少添加一个步骤");
      submitting.value = false;
      return;
    }

    const payload = {
      ...form,
      ingredients,
      steps,
    };

    if (isEdit.value) {
      await recipeStore.updateRecipe(Number(route.params.id), payload);
      ElMessage.success("菜谱已更新");
      router.push(`/recipes/${route.params.id}`);
    } else {
      const recipe = await recipeStore.createRecipe(payload);
      ElMessage.success("菜谱已创建");
      router.push(`/recipes/${recipe.id}`);
    }
    dirty.value = false;
  } catch (e: unknown) {
    const msg = (e as { message?: string })?.message || "操作失败";
    ElMessage.error(msg);
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.recipe-form-page {
  max-width: 800px;
  margin: 0 auto;
}
.form-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.form-header h2 {
  margin: 0;
}
.array-section {
  margin: 20px 0;
}
.array-header h4 {
  margin: 0 0 10px;
}
.array-header .el-alert {
  margin-bottom: 10px;
}
.array-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.step-order {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  flex-shrink: 0;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}
.form-image-preview {
  width: 100%;
  height: 100px;
  object-fit: cover;
  border-radius: 8px;
  margin-top: 8px;
  background: #f0f2f5;
}
</style>
