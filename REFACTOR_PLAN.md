# Recipelity Web 项目重构计划书

> 本文是面向 AI 智能体的执行规格。除非任务明确要求，不得删除旧版 PyQt 代码或破坏 `data/recipes.db`；每个阶段必须可独立运行、测试和回滚。
>
> 后续实施顺序与数据库选型以 `NEXT_PHASE_PLAN.md` 为准：目标数据库已确定为 MySQL，图像识别延期到其他页面和核心功能稳定之后。

## 1. 项目现状

当前项目是 Python 3.9+、PyQt6、SQLAlchemy、SQLite 的桌面应用：

- `main.py` / `main_en.py`：中英文启动入口。
- `ui/main_window*.py`：约千行的界面、线程和交互逻辑。
- `core/models*.py`：菜谱、食材、步骤、营养、标签模型。
- `core/recipe_manager*.py`：CRUD、搜索、网页导入、营养分析和图像分析。

需保留的核心业务是菜谱管理、关键词/标签/时间/难度/菜系筛选、网页导入、营养分析。当前图像分析仅随机生成食材，并非真实识别。主要问题还包括中英文代码重复、全局数据库 Session、启动时自动建表和写入样例数据、领域/数据/UI 强耦合、中文文件疑似编码异常、无测试与数据库迁移、无 Web API 和部署配置。`Recipe.total_time` 是普通 Python 属性，不能可靠用于 SQL 查询过滤。

## 2. 目标与非目标

### 目标

1. 使用 Vue 3 网站替换 PyQt 前端，支持桌面端与移动端响应式访问。
2. 使用 Python Web API 承载原有菜谱、搜索和营养能力，不再保留 URL 导入。
3. 增加“上传菜品图片 → 生成菜谱与营养估算 → 用户确认”和“菜谱文字 → 生成配图”闭环。
4. 保留并安全迁移现有 SQLite 数据，提供可重复部署方案。

### 首期非目标

不做社交、支付、复杂权限、营养医疗建议或自训练视觉模型。识别结果必须标记置信度和数据来源，未经用户确认不得直接保存为正式菜谱。

## 3. 目标架构与技术选型

```text
Vue 3 + TypeScript + Vite
        │ REST / OpenAPI
FastAPI + Pydantic + SQLAlchemy 2
        ├── MySQL（生产）/ SQLite（旧数据迁移来源）
        ├── 菜谱导入与营养计算服务
        └── 可替换 ImageRecognitionProvider
```

- 前端：Vue 3、TypeScript、Vite、Vue Router、Pinia、Axios、Element Plus、ECharts、Vitest。
- 后端：FastAPI、Pydantic v2、SQLAlchemy 2、Alembic、httpx、BeautifulSoup4、pytest。
- 工程：Docker Compose、Nginx、环境变量、Ruff、Black、mypy、ESLint、Prettier。
- 图像 MVP：定义统一 Provider 接口。优先接入能返回结构化 JSON 的多模态视觉服务；没有密钥时使用本地 CLIP 对受控菜品/食材词表做 Top-K 匹配。接口不得返回随机结果。

建议新目录：

```text
backend/app/{api,core,db,models,schemas,services,providers}
backend/tests/{unit,integration}
frontend/src/{api,assets,components,layouts,router,stores,types,views}
deploy/{nginx,Dockerfile.*}
scripts/
```

## 4. 分阶段执行计划

### P0：基线、数据保护与契约

- 修复 README/源码的 UTF-8 编码并记录原始数据库备份方式。
- 为旧数据库编写只读审计脚本，统计各表行数、孤儿记录和空字段。
- 输出 OpenAPI 领域契约：`Recipe`、`Ingredient`、`Step`、`Nutrition`、`Tag`、分页和统一错误体。
- 建立后端/前端工程、`.env.example`、格式化和测试配置。

验收：旧应用文件未删除；审计脚本不修改数据；空项目测试和 lint 全部通过。

### P1：后端 API 与数据迁移

- 将模型合并为唯一语言无关版本；展示文本通过前端 i18n 处理。
- 使用请求级 Session 和依赖注入，禁止全局 Session；通过 Alembic 管理表结构。
- 实现 `/api/v1/recipes` CRUD、分页搜索、标签/菜系筛选和营养详情。
- 将 `total_time` 改为 SQL hybrid property 或以 `prep_time + cook_time` 表达式过滤。
- 编写幂等迁移工具，将 `data/recipes.db` 复制迁移；迁移前后核对数量、关联及关键字段。
- 拆分网页导入器为站点适配器，设置超时、User-Agent、响应大小限制，并阻止内网地址访问。

验收：API 文档可访问；迁移重复执行不产生重复数据；CRUD、筛选、回滚和导入适配器均有测试。

### P2：Vue 3 前端重构

- 页面：菜谱列表/筛选、菜谱详情、新增编辑、营养分析、URL 导入、图片识别。
- 将筛选状态同步到 URL；列表支持分页、加载态、空态和错误重试。
- 表单使用结构化食材/步骤编辑器，进行必填、数值范围和图片格式校验。
- 使用 ECharts 展示热量、蛋白质、脂肪、碳水、纤维、糖和钠；明确“估算值”。
- 首期实现中文界面，文案集中管理，为后续 `vue-i18n` 预留键值。

验收：核心流程可在 360px 和 1440px 宽度使用；组件测试覆盖关键表单与筛选；无 TypeScript/ESLint 错误。

### P3：真实图像识别 MVP

- API：`POST /api/v1/image-recognition`，仅接受 JPEG/PNG/WebP，限制文件大小、像素和处理时长。
- 返回 `dish_candidates[]`、`ingredients[]`、`confidence`、`provider`、`warnings[]`，并用候选名称/食材查询已有菜谱。
- 前端允许用户删除、改名和补充识别项，再生成可编辑菜谱草稿。
- Provider 超时或不可用时返回明确降级提示，不伪造识别结果；上传文件处理后删除，不默认持久化。
- 建立至少 20 张授权测试图片的小型评估集，记录 Top-3 菜品命中率、食材召回率和平均耗时；阈值由评估结果确定。

验收：同一 Provider 对同一图片结果可复现；低置信度明确提示；恶意扩展名、超大文件和超时均被安全处理。

### P4：营养、质量与部署

- 将营养数据从硬编码字典迁移为可追溯数据表；统一食材别名和 g/ml/份等单位换算。
- 保存总量与每份营养，记录 `source`、`calculated_at` 和无法匹配的食材。
- 增加 Docker Compose（前端、API、MySQL、Nginx）、健康检查、日志和迁移启动步骤。
- CI 顺序：后端 lint/typecheck/test → 前端 lint/test/build → 容器构建。

验收：新环境一条命令启动；API/静态资源刷新正常；数据库使用持久卷；密钥不进入镜像、日志或 Git。

## 5. API 最小范围

- `GET/POST /api/v1/recipes`
- `GET/PATCH/DELETE /api/v1/recipes/{id}`
- `GET /api/v1/tags`，`GET /api/v1/cuisines`
- `POST /api/v1/ai/recipe-from-image`
- `POST /api/v1/ai/image-from-recipe`
- `POST /api/v1/recipes/{id}/nutrition:calculate`
- `POST /api/v1/image-recognition`
- `GET /health/live`，`GET /health/ready`

所有写接口使用 Pydantic 校验；错误体统一为 `{code, message, details, request_id}`。列表默认分页，禁止返回 ORM 对象或泄露内部异常。

## 6. 测试与完成定义

- 后端：业务单元测试、SQLite/MySQL 迁移测试、MySQL 集成测试、API 契约测试；新增核心代码覆盖率目标不低于 80%。
- 前端：Vitest 组件测试；Playwright 覆盖“搜索 → 查看 → 编辑”和“上传 → 确认 → 草稿”。
- 每个任务完成前运行：

```bash
cd backend && ruff check . && black --check . && mypy app && pytest
cd frontend && npm run lint && npm run test:unit && npm run build
docker compose config
```

“完成”要求：代码、测试、迁移、配置和文档同时提交；不得以 mock/随机数据宣称功能完成；不得修改无关文件。

## 7. AI 智能体执行规则

1. 按 `P0 → P4` 顺序工作，每次只领取一个可验收任务，并先检查现有改动。
2. 修改前列出影响文件、数据风险和验证命令；优先小提交，提交格式使用 `feat:`, `fix:`, `refactor:`, `test:`, `docs:`。
3. 数据模型或 API 变更必须同时更新 Alembic、Pydantic、OpenAPI、前端类型和测试。
4. 不直接覆盖 `data/recipes.db`；迁移必须先备份并提供 dry-run。
5. 外部视觉/营养服务必须封装 Provider，设置超时、重试上限和可观测日志，密钥只从环境变量读取。
6. 若 README 与代码冲突，以可运行代码为事实并在变更说明中记录差异；遇到产品取舍或不可逆迁移时暂停并请求确认。

## 8. 建议优先优化项

优先级从高到低：数据备份与迁移、消除随机图像结果、API/Session 解耦、筛选查询修复、自动化测试、重复中英文代码合并、导入器安全、营养数据可信度、容器化部署。用户账户可在网站 MVP 稳定后增加；届时再引入所有权、认证、收藏与分享，避免首期扩大范围。
