# StoryCAD 全面改造设计文档

## 概述

对 StoryCAD 进行安全修复、功能补全、代码质量提升和 UI 重新设计，使其达到生产可用水平。共 4 个梯队、16 项任务。

---

## P0 — 安全修复

### 0.1 JWT 密钥强制配置

**现状：** `config.py` 中 `jwt_secret_key` 默认空字符串，Token 可伪造。

**方案：** `main.py` 启动时检查 `settings.jwt_secret_key` 是否为空，空则抛 `ValueError` 退出。必须在 `.env` 或环境变量中配置。

**文件：** `backend/app/main.py` + `backend/.env`

### 0.2 实体归属交叉校验

**现状：** 通用 CRUD 路由只校验 `project_id` 属于当前用户，不校验 `entity_id` 实体实际属于该 `project_id`。恶意用户可传入自己项目 ID + 他人实体的 ID 进行跨项目访问。

**方案：** `routes_storycad.py` 中 `get_entity`/`put_entity`/`delete_entity` 在获取实体后，断言 `entity.project_id == project_id`。

**文件：** `backend/app/api/routes_storycad.py`

### 0.3 注册输入校验

**现状：** 仅检查空字符串和密码长度 >= 8。

**方案：** 新增 `RegisterRequest` Pydantic model：邮箱正则校验、用户名 3-20 字符（字母数字下划线）、密码 >= 8。

**文件：** `backend/app/api/routes_auth.py`

---

## P1 — 功能修复

### 1.1 Rhythm 数据模型 + API

**现状：** 无 rhythm 数据模型，前端 `normalizeApiData` 硬编码 `rhythms: []`。

**方案：**
- 新增 `ChapterRhythm` ORM 模型（`storycad/models.py`）
  - `chapter_id: UUID FK -> chapters.id`（唯一约束）
  - `project_id: UUID FK -> projects.id`
  - `action: int` 0-10, default 5
  - `suspense: int` 0-10, default 5
  - `emotion: int` 0-10, default 5
  - `humor: int` 0-10, default 5
  - `intensity: int` 0-10, default 5
  - `created_at`, `updated_at`
- 注册到 `entity_map.py`（rhythms -> ChapterRhythm）
- 更新 `sync_editor_data` 支持 rhythm 实体
- `normalizeApiData` 映射 rhythms
- 新增 migration 0008

### 1.2 Rhythm 前端编辑 UI

**交互方案：** A — 点击立柱弹出滑块面板

- 点击 RhythmView 中柱状图的任一章节 → 弹出 RhythmEditPanel（侧边栏或对话框）
- 面板包含 4 个范围滑块（0-10），分别控制 action/suspense/emotion/humor
- intensity 根据 4 值加权计算
- 保存时通过 `syncEditorData` 推送到后端
- 折线覆盖层：连接各章 intensity，形成节奏曲线

### 1.3 Theme 前端 CRUD

**现状：** 后端已有通用 CRUD API，但前端无新增/编辑/删除 UI。

**方案：**
- Theme 卡片悬停显示 ✎ 编辑 / ✕ 删除 按钮
- "添加主题"按钮 → 弹出对话框（名称、颜色色盘、命题）
- 删除 → 确认弹窗
- ThemeDetail 中笔记保存 → 调用后端 `updateEntity` API（当前是 `onSaveNote={() => {}}`）
- 编辑主题 → 弹出侧边栏或行内编辑

### 1.4 Layout 按钮

**现状：** `onLayout={() => {}}` 空函数。

**方案：** 实现基于 Force-Directed 或 Dagre 的自动布局。点击布局按钮 → 使用 `dagre` 库根据拓扑排序重新计算节点位置。

### 1.5 项目列表真实数据

**现状：** `enrichProject()` 生成假数据（`words: "—"`、随机模板、假时间）。

**方案：** 后端 `GET /api/projects` 增加统计字段：
- `total_words`：chapters 表 SUM total_words
- `total_chapters`：chapters 表 COUNT
- `total_scenes`：scenes 表 COUNT
- `template_type`：来自 project_configs
- `genre`：来自 projects 表

---

## P2 — 代码质量

### 2.1 提取共享工具函数

**现状：** 5 个 project_creator nodes 文件各有一份 `_parse_json()` 和 `_load()` 重复代码。

**方案：** 提取到 `app/agent/project_creator/utils.py`，4 个节点文件改为 import。

### 2.2 删除死代码

- `user/repository.py:76-78`：`return True` 后不可达的重复代码
- `scenes.py:74-95`：`generate_scene_chapter()` 未使用的死函数
- `requirements.txt`：删除 `passlib[bcrypt]`（直接使用 `bcrypt`）

### 2.3 版本快照优化

**现状：** 每次 `syncEditorData` 都创建新 `ProjectVersion`，包括无数据变化的同步。

**方案：** 对比 `sync_editor_data` 的输入数据与当前 DB 状态，只有实际发生变化时才创建快照。

### 2.4 asyncio.gather 节流

**现状：** `generate_all_scenes` 对所有章节同时发起 LLM 调用，无节流。

**方案：** 使用 `asyncio.Semaphore(5)` 限制并发数为 5。

### 2.5 移除 create_all

**现状：** `database.py` 启动时执行 `Base.metadata.create_all`，可能与 migration 状态漂移。

**方案：** 删除 `init_db()` 中的 `create_all` 调用。依赖 migration 管理 schema。

---

## P3 — 缺失 API

### 3.1 Project Config API

**现状：** 无独立端点，config 仅在 AI 创建项目时内联写入。

**方案：**
- `GET /api/projects/{id}/config` 返回 `ProjectConfig`
- `PUT /api/projects/{id}/config` 更新 `ProjectConfig`

### 3.2 服务端搜索

**现状：** 项目列表仅客户端过滤。

**方案：**
- `GET /api/projects?search=&status=&genre=&page=&size=`
- 后端 SQL 过滤：`title ILIKE %search%`、`status=`、`genre=`

---

## 实施顺序

```
P0 安全     →  P1 功能     →  P2 代码质量  →  P3 API
(3 tasks)      (5 tasks)      (5 tasks)       (2 tasks)
```

每梯队内并行实施。每完成一个梯队跑测试验证，再进入下一梯队。

## 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Rhythm 交互 | A — 滑块面板 | 直观、低实现成本、与现有侧面板模式一致 |
| 节奏曲线 | intensity 折线叠加 | 视觉对比强烈，一眼看出节奏起伏 |
| Theme 保存 | blur 时自动保存 + 后端 API | 与现有场景内容保存模式一致 |
| Layout 布局 | 引入 dagre 库 | 轻量、纯前端、有向图布局成熟方案 |
| 版本快照 | 对比数据差异 | 避免无用快照膨胀，同时不丢失变更历史 |
| LLM 并发 | Semaphore(5) | 平衡速度与 API 限流防护 |
