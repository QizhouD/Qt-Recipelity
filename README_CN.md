# 智能食谱管理系统

一个功能强大的食谱管理软件，支持智能搜索筛选、营养分析和 AI 辅助创作。

![食谱管理系统截图](https://p3-flow-imagex-sign.byteimg.com/tos-cn-i-a9rns2rl98/rc/pc/super_tool/f2fe70d696674ccba18f9906fe656c7b~tplv-a9rns2rl98-image.image?rcl=202510291704299827E18D95DA8D8EC834&rk3s=8e244e95&rrcfp=f06b921b&x-expires=1764320746&x-signature=dkqeAt%2FHuq1BYXBJPXUcj%2FzFuEg%3D)

## 功能特点

### 基础功能

1. **食谱收集与管理**
   - 手动添加和编辑食谱
   - 支持结构化食谱数据导入
   - 数据库存储，安全可靠

2. **智能搜索与筛选**
   - 基于关键词的全文搜索
   - 多维度筛选（标签、烹饪时间、难度、菜系等）
   - 快速定位所需食谱

3. **营养分析**
   - 自动计算食谱的营养成分
   - 可视化展示营养构成
   - 支持多种食材的营养数据

### 亮点功能

1. **AI 辅助创作**
   - 上传食物图片自动生成菜谱草稿与营养估算
   - 根据菜谱文字生成成品菜配图

2. **食物图像分析**（规划中）
   - 食物图像分割与食材识别
   - 基于图像自动生成食谱

## 技术栈

- **前端框架**: Vue 3 + TypeScript + Element Plus
- **后端框架**: FastAPI (Python 3.12+)
- **数据库**: MySQL 8.4（Docker / 生产环境）；SQLite 用于本地开发、测试和旧数据迁移来源
- **ORM**: SQLAlchemy 2.0 (async) + Alembic
- **AI**: OpenAI (GPT vision + DALL·E / GPT image)
- **容器化**: Docker Compose (MySQL + Backend + Nginx)

## 安装与运行

### 前提条件

- Python 3.12 或更高版本
- Node.js 20+
- MySQL 8.4（生产环境）或 SQLite（本地开发）

### 本地开发（SQLite）

```bash
# 后端
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env  # 编辑 .env 使用 SQLite URL
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

### Docker 部署（MySQL）

```bash
cp .env.example .env  # 编辑 .env 设置密码
docker compose up -d
```

## 数据说明

生产环境使用 MySQL 8.4 数据库。本地开发和测试可使用 SQLite。

主要数据模型包括：
- Recipe: 食谱基本信息
- Ingredient: 食材信息
- Step: 烹饪步骤
- Nutrition: 营养成分
- Tag: 标签

### 从 SQLite 迁移到 MySQL

#### 推荐路径 A：全新空库 + 数据导入

```bash
# ⚠️ 第一步：备份原始 SQLite 文件！
cp data/recipes.db data/recipes.db.bak

# 1. 使用 Alembic 在目标 MySQL 中创建表结构
cd backend
DATABASE_URL=mysql+asyncmy://recipelity:password@localhost:3306/recipelity?charset=utf8mb4 \
  alembic upgrade head

# 2. 迁移数据（dry-run 预览，不写入）
cd ..
python scripts/migrate_db.py data/recipes.db \
  --target mysql+asyncmy://recipelity:password@localhost:3306/recipelity?charset=utf8mb4 \
  --dry-run

# 3. 正式迁移（幂等，可重复运行）
python scripts/migrate_db.py data/recipes.db \
  --target mysql+asyncmy://recipelity:password@localhost:3306/recipelity?charset=utf8mb4

# 4. 验证
python scripts/audit_db.py data/recipes.db  # 源库统计
```

#### 路径 B：已有验证一致的数据库

仅当目标数据库的 schema 已与 Alembic head 完全一致时使用：

```bash
DATABASE_URL=mysql+asyncmy://... alembic stamp head
```

> **⚠️ 重要警告**：不要对已有数据的 `data/recipes.db` 直接执行 `alembic upgrade head`。如果表已存在，Alembic 会报 "table already exists" 错误。请先备份，然后使用上述推荐路径。

## 测试

```bash
# 后端测试
cd backend
python -m ruff check app tests
python -m pytest tests -q

# 前端单元测试
cd frontend
npm run test:unit

# 前端 E2E 测试
npm run test:e2e           # headless
npm run test:e2e:headed    # 显示浏览器
```

## 未来计划

- 添加用户账户系统，支持多用户使用
- 实现食谱分享功能
- 优化食物图像识别算法，提高准确性
- 添加移动端支持

## 许可证

MIT License
