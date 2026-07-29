<template>
  <div class="filter-panel">
    <h3>筛选条件</h3>
    <el-input v-model="local.keyword" placeholder="搜索菜名或食材..." clearable
              @input="onKeywordInput" @clear="onKeywordClear">
      <template #prefix><span>🔍</span></template>
    </el-input>

    <div class="filter-group">
      <label>菜系</label>
      <el-select v-model="local.cuisine" placeholder="全部" clearable
                 style="width:100%" @change="emitChange">
        <el-option v-for="c in cuisines" :key="c" :label="c" :value="c" />
      </el-select>
    </div>

    <div class="filter-group">
      <label>标签</label>
      <el-checkbox-group v-model="local.tags" @change="emitChange">
        <el-checkbox v-for="t in tagOptions" :key="t" :label="t" :value="t" />
      </el-checkbox-group>
    </div>

    <div class="filter-group">
      <label>难度</label>
      <div class="range-row">
        <el-input-number v-model="local.min_difficulty" :min="1" :max="5"
                         size="small" placeholder="最低" @change="emitChange" />
        <span>—</span>
        <el-input-number v-model="local.max_difficulty" :min="1" :max="5"
                         size="small" placeholder="最高" @change="emitChange" />
      </div>
    </div>

    <div class="filter-group">
      <label>总时间（分钟）</label>
      <div class="range-row">
        <el-input-number v-model="local.min_time" :min="0" size="small"
                         placeholder="最少" @change="emitChange" />
        <span>—</span>
        <el-input-number v-model="local.max_time" :min="0" size="small"
                         placeholder="最多" @change="emitChange" />
      </div>
    </div>

    <el-button type="default" style="width:100%" @click="$emit('reset')">
      重置筛选
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import type { RecipeSearchFilters } from "@/types";
import apiClient from "@/api/client";

const props = defineProps<{ filters: RecipeSearchFilters }>();
const emit = defineEmits<{ change: []; reset: [] }>();

const tagOptions = ref<string[]>([]);
const cuisines = ref<string[]>([]);

const local = reactive({ ...props.filters });

// Debounce timer for keyword search (300ms)
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

watch(() => props.filters, (f) => Object.assign(local, f), { deep: true });

function emitChange() {
  Object.assign(props.filters, local);
  emit("change");
}

function onKeywordInput() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    emitChange();
  }, 300);
}
function onKeywordClear() {
  if (debounceTimer) clearTimeout(debounceTimer);
  emitChange();
}

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer);
});

onMounted(async () => {
  try {
    const [t, c] = await Promise.all([
      apiClient.get("/tags"),
      apiClient.get("/cuisines"),
    ]);
    tagOptions.value = t.data.map((x: { name: string }) => x.name);
    cuisines.value = c.data;
  } catch { /* filters will be empty */ }
});
</script>

<style scoped>
.filter-panel h3 { margin: 0 0 12px; font-size: 16px; }
.filter-panel > * { margin-bottom: 16px; }
.filter-group label { display: block; font-size: 13px; color: #606266; margin-bottom: 6px; }
.range-row { display: flex; align-items: center; gap: 8px; }
.range-row span { color: #909399; }
</style>
