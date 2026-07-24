<template>
  <div class="recipe-image" :class="{ compact }">
    <img v-if="src && !failed" :src="src" :alt="alt" loading="lazy" @error="failed = true" />
    <div v-else class="fallback"><span>🍲</span><small>暂无菜谱图片</small></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
const props = defineProps<{ src?: string; alt: string; compact?: boolean }>();
const failed = ref(false);
watch(() => props.src, () => { failed.value = false; });
</script>

<style scoped>
.recipe-image{width:100%;height:380px;overflow:hidden;background:linear-gradient(135deg,#eef5f1,#e8edf4);
display:flex;align-items:center;justify-content:center}.recipe-image.compact{height:170px}
img{width:100%;height:100%;object-fit:cover;display:block}.fallback{display:flex;flex-direction:column;
align-items:center;gap:8px;color:#87928e}.fallback span{font-size:64px}.compact .fallback span{font-size:44px}
</style>
