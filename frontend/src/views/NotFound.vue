<template>
  <div class="not-found-page">
    <el-result icon="warning" title="404" sub-title="页面未找到">
      <template #extra>
        <el-button type="primary" @click="$router.push('/recipes')">
          返回菜谱列表
        </el-button>
      </template>
    </el-result>
  </div>
</template>

<style scoped>
.not-found-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}
</style>
