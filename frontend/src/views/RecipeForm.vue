<template>
  <div class="recipe-form-page">
    <div class="form-header">
      <el-button text @click="$router.back()">← 返回</el-button>
      <h2>{{ isEdit ? '编辑食谱' : '添加食谱' }}</h2>
    </div>

    <el-card class="form-card">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top"
               @submit.prevent="handleSubmit">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="菜名" prop="name">
              <el-input v-model="form.name" placeholder="例如：红烧肉" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="菜系">
              <el-input v-model="form.cuisine" placeholder="例如：中式、西式" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2"
                    placeholder="简短的描述..." />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="准备时间（分钟）">
              <el-input-number v-model="form.prep_time" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="烹饪时间（分钟）">
              <el-input-number v-model="form.cook_time" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="难度 (1-5)">
              <el-input-number v-model="form.difficulty" :min="1" :max="5" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="图片 URL">
              <el-input v-model="form.image_url" placeholder="图片 URL（可选）" clearable />
              <img v-if="form.image_url" :src="form.image_url" class="form-image-preview"
                alt="菜谱图片预览" />
              <el-upload :show-file-list="false" :auto-upload="false"
                accept="image/jpeg,image/png,image/webp" :on-change="uploadImage">
                <el-button :loading="uploading" style="margin-top:8px">
                  {{ form.image_url ? "更换图片" : "上传图片" }}
                </el-button>
              </el-upload>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple filterable allow-create
                     placeholder="添加标签..." style="width:100%">
            <el-option v-for="t in form.tags" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>

        <!-- Ingredients -->
        <div class="array-section">
          <h4>🥬 食材</h4>
          <div v-for="(ing, i) in form.ingredients" :key="i" class="array-row">
            <el-input v-model="ing.name" placeholder="食材名" style="flex:2" />
            <el-input-number v-model="ing.amount" :min="0" placeholder="数量" style="flex:1" />
            <el-input v-model="ing.unit" placeholder="单位 (g/ml)" style="flex:1" />
            <el-button type="danger" text @click="form.ingredients.splice(i, 1)">✕</el-button>
          </div>
          <el-button @click="form.ingredients.push({ name: '', amount: undefined, unit: '' })">
            + 添加食材
          </el-button>
        </div>

        <!-- Steps -->
        <div class="array-section">
          <h4>📝 步骤</h4>
          <div v-for="(step, i) in form.steps" :key="i" class="array-row step-row">
            <span class="step-order">{{ i + 1 }}</span>
            <el-input v-model="step.description" placeholder="步骤描述..." style="flex:1" />
            <el-button type="danger" text @click="form.steps.splice(i, 1)">✕</el-button>
          </div>
          <el-button @click="form.steps.push({ order: form.steps.length + 1, description: '' })">
            + 添加步骤
          </el-button>
        </div>

        <div class="form-actions">
          <el-button @click="$router.back()">取消</el-button>
          <el-button type="primary" native-type="submit" :loading="submitting">
            {{ isEdit ? '保存修改' : '创建食谱' }}
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, type UploadFile } from "element-plus";
import apiClient from "@/api/client";
import { useRecipeStore } from "@/stores/recipe";

const route = useRoute();
const router = useRouter();
const recipeStore = useRecipeStore();

const isEdit = route.name === "recipe-edit";
const submitting = ref(false);
const uploading = ref(false);

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
  nutrition: undefined as {
    calories?: number; protein?: number; fat?: number; carbohydrates?: number;
    fiber?: number; sugar?: number; sodium?: number;
  } | undefined,
});

const rules = {
  name: [{ required: true, message: "请输入菜名", trigger: "blur" }],
};

async function uploadImage(file: UploadFile) {
  if (!file.raw) return;
  uploading.value = true;
  try {
    const body = new FormData();
    body.append("file", file.raw);
    const response = await apiClient.post<{ image_url: string }>("/media/images", body, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 30000,
    });
    form.image_url = response.data.image_url;
    ElMessage.success("图片上传成功");
  } catch (error) {
    ElMessage.error((error as { message?: string }).message || "图片上传失败");
  } finally {
    uploading.value = false;
  }
}

onMounted(async () => {
  if (isEdit) {
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
          name: i.name, amount: i.amount, unit: i.unit || "",
        })),
        steps: recipe.steps.map((s) => ({
          order: s.order, description: s.description,
        })),
        tags: recipe.tags.map((t) => t.name),
      });
    } catch {
      ElMessage.error("加载食谱失败");
      router.push("/");
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
          ingredients: draft.ingredients || [],
          steps: draft.steps || [],
          tags: draft.tags || [],
          nutrition: draft.nutrition,
        });
        sessionStorage.removeItem("aiRecipeDraft");
        ElMessage.warning("这是 AI 草稿，请核对所有内容后再保存");
      } catch {
        sessionStorage.removeItem("aiRecipeDraft");
      }
    }
  }
});

async function handleSubmit() {
  submitting.value = true;
  try {
    const payload = {
      ...form,
      ingredients: form.ingredients.filter((i) => i.name),
      steps: form.steps.filter((s) => s.description).map((s, i) => ({
        order: i + 1, description: s.description,
      })),
    };

    if (isEdit) {
      await recipeStore.updateRecipe(Number(route.params.id), payload);
      ElMessage.success("食谱已更新");
      router.push(`/recipes/${route.params.id}`);
    } else {
      const recipe = await recipeStore.createRecipe(payload);
      ElMessage.success("食谱已创建");
      router.push(`/recipes/${recipe.id}`);
    }
  } catch (e: unknown) {
    const msg = (e as { message?: string })?.message || "操作失败";
    ElMessage.error(msg);
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.recipe-form-page { max-width: 800px; margin: 0 auto; }
.form-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.form-header h2 { margin: 0; }
.array-section { margin: 20px 0; }
.array-section h4 { margin: 0 0 10px; }
.array-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.step-order { width: 28px; height: 28px; border-radius: 50%; background: #409eff;
              color: #fff; display: flex; align-items: center; justify-content: center;
              font-size: 13px; flex-shrink: 0; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 24px;
                padding-top: 16px; border-top: 1px solid #e4e7ed; }
.form-image-preview { width: 100%; height: 100px; object-fit: cover; border-radius: 8px;
                      margin-top: 8px; background: #f0f2f5; }
</style>
