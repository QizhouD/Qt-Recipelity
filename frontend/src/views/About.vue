<template>
  <div class="about-page">
    <el-card class="about-hero" data-testid="about-hero">
      <h1 data-testid="about-heading">关于 Recipelity</h1>
      <p>
        Recipelity 是一款智能食谱管理系统，帮助您收集、整理和创作美味食谱。
      </p>
    </el-card>

    <div class="about-grid">
      <el-card>
        <template #header><h3>📖 菜谱管理</h3></template>
        <p>创建、编辑、搜索和筛选您的私人食谱库。支持食材清单、烹饪步骤、标签分类和菜系管理。</p>
      </el-card>

      <el-card>
        <template #header><h3>📸 图片上传</h3></template>
        <p>为每道菜谱上传实拍图片，支持 JPEG、PNG、WebP 格式。图片会自动优化方向并调整尺寸。</p>
      </el-card>

      <el-card>
        <template #header><h3>🥗 营养估算</h3></template>
        <p>基于食材名称与用量进行营养成分估算，支持常见中英文食材。估算结果仅供参考，不构成医学或专业膳食建议。</p>
        <el-alert
          type="warning"
          :closable="false"
          show-icon
          title="营养值为估算数据，实际含量因食材品种、产地和烹饪方式而异。"
        />
      </el-card>

      <el-card>
        <template #header><h3>🤖 AI 创作</h3></template>
        <p>
          上传食物照片，AI 自动识别食材并生成可编辑的菜谱草稿与营养估算。也可将菜谱文字转换为精美的菜品配图。
        </p>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="AI 生成的内容需人工审核确认。AI 功能需要配置 OpenAI API Key。"
        />
      </el-card>
    </div>

    <el-card class="tech-card">
      <template #header><h3>技术栈</h3></template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="前端框架">Vue 3 + TypeScript + Element Plus</el-descriptions-item>
        <el-descriptions-item label="后端框架">FastAPI (Python 3.12+)</el-descriptions-item>
        <el-descriptions-item label="数据库">MySQL 8.4 (生产) / SQLite (开发与测试)</el-descriptions-item>
        <el-descriptions-item label="AI 服务">OpenAI API</el-descriptions-item>
        <el-descriptions-item label="容器化">Docker Compose (MySQL + Backend + Nginx)</el-descriptions-item>
        <el-descriptions-item label="迁移工具">Alembic + migrate_db.py</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<style scoped>
.about-page {
  max-width: 960px;
  margin: 0 auto;
}
.about-hero {
  margin-bottom: 24px;
  text-align: center;
}
.about-hero h1 {
  margin: 0 0 8px;
  font-size: 28px;
  color: #2f6d62;
}
.about-hero p {
  color: #606266;
  font-size: 16px;
}
.about-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}
.about-grid h3 {
  margin: 0;
  font-size: 16px;
}
.about-grid p {
  color: #606266;
  line-height: 1.7;
}
.about-grid .el-alert {
  margin-top: 12px;
}
.tech-card h3 {
  margin: 0;
  font-size: 16px;
}
@media (max-width: 640px) {
  .about-grid {
    grid-template-columns: 1fr;
  }
}
</style>
