# Novel Forge — 改动说明文档

> 版本：v2.0.0 | 日期：2026-06-09

---

## 目录

1. [本次改了什么](#1-本次改了什么)
2. [新增文件说明](#2-新增文件说明)
3. [修改文件说明](#3-修改文件说明)
4. [数据库设计](#4-数据库设计)
5. [API 接口](#5-api-接口)
6. [前端项目中心](#6-前端项目中心)
7. [三阶段执行流程](#7-三阶段执行流程)
8. [测试结果](#8-测试结果)
9. [如何运行](#9-如何运行)

---

## 1. 本次改了什么

### 旧架构的问题

- 所有项目共用一个目录（`run_时间戳`），数据散落在文件系统和日志里，没有统一管理
- 没有阶段概念：大纲、正文、审校混在一起，没有暂停/恢复机制
- 侧边栏的章节、记忆、大纲各自独立，没有和项目绑定
- AI 助理只能在引擎运行时使用，暂停时无法分析项目状态

### 新架构做了什么

| 改进点 | 说明 |
|--------|------|
| **一个项目一个目录** | `workspace/projects/{name}/` + `project.db`，元数据在数据库，大内容在文件系统 |
| **三阶段可拆分执行** | 大纲制作 → 正文写作 → 整体润色，每个阶段独立运行、单独控制 |
| **人工审核机制** | 大纲生成后停止，等用户确认"继续写作"或"驳回重写" |
| **SQLite 数据库** | projects / chapters / memory_items / chat_messages / stage_runs 五张表 |
| **项目中心 UI** | 前端新增"项目中心"视图，三列布局（项目列表 + 编辑器 + 阶段控制） |
| **AI 助理常驻** | 引擎暂停时也能基于项目上下文（大纲/章节/记忆）给出建议和分析 |
| **旧项目迁移** | 一键把 `run_*` 目录迁移到新项目结构 |
| **全流程测试** | 19 个测试用例覆盖所有核心功能，100% 通过 |

---

## 2. 新增文件说明

### 后端

| 文件 | 作用 |
|------|------|
| `backend/project_db.py` | SQLite 项目数据库封装，核心 CRUD 操作 |
| `backend/project_executor.py` | 阶段执行管理器，接管大纲/写作/审校三个阶段的启动和文件同步 |
| `backend/assistant.py` | 项目 AI 助理，收集项目上下文供 LLM 使用 |
| `backend/migration.py` | 旧 `run_*` 目录迁移脚本 |
| `backend/test_all.py` | 全流程功能测试（19 个用例） |

### 前端

| 文件 | 作用 |
|------|------|
| `frontend/src/hooks/useProjectV2.js` | v2 API hook，包含项目 CRUD、阶段启动、AI 对话、文件读写 |
| `frontend/src/components/ProjectCenter.jsx` | 项目中心主界面组件 |
| （样式）`frontend/src/App.css` | 项目中心的 CSS 样式（571 行新增） |

---

## 3. 修改文件说明

### `backend/main.py`

新增 `/api/v2/projects/*` 一组端点：

```
POST   /api/v2/projects                           创建项目
GET    /api/v2/projects                           列出所有项目
GET    /api/v2/projects/{name}                    项目详情
DELETE /api/v2/projects/{name}                    删除项目
PATCH  /api/v2/projects/{name}                    更新项目设置
GET    /api/v2/projects/{name}/chapters           章节列表
GET    /api/v2/projects/{name}/chapters/{idx}     单章详情
PATCH  /api/v2/projects/{name}/chapters/{idx}    更新章节
GET    /api/v2/projects/{name}/memory             记忆列表
POST   /api/v2/projects/{name}/memory             添加记忆
GET    /api/v2/projects/{name}/chat              对话历史
POST   /api/v2/projects/{name}/assistant/chat     AI 助理对话
POST   /api/v2/projects/{name}/confirm-outline    确认大纲，推进到写作
POST   /api/v2/projects/{name}/reject-outline     驳回大纲，重写
POST   /api/v2/projects/{name}/stop               停止当前运行
POST   /api/v2/projects/run-stage                 启动阶段（SSE 流式）
GET    /api/v2/projects/{name}/file/{fname}       读取项目文件
PUT    /api/v2/projects/{name}/file/{fname}       写入项目文件
POST   /api/v2/projects/migrate-old               迁移旧项目
```

### `frontend/src/App.jsx`

- 导入 `useProjectV2` hook 和 `ProjectCenter` 组件
- 新增 `currentView` 状态，默认进入项目中心
- 右上角加入视图切换按钮：「项目中心」/「Workbench」

---

## 4. 数据库设计

项目数据库位于 `workspace/projects/{name}/project.db`，共 5 张表：

### projects

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| name | TEXT | 项目名（唯一） |
| title | TEXT | 小说标题 |
| genre | TEXT | 题材（玄幻/科幻/都市等） |
| total_chapters | INTEGER | 目标章节数 |
| current_stage | TEXT | 当前阶段：outline / writing / polish / completed |
| execution_mode | TEXT | 执行模式：lite / standard / full |
| outline_review_mode | TEXT | 审核模式：auto / manual |
| ai_preset | TEXT | 使用的 AI preset 名称 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### chapters

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| project_id | INTEGER | 所属项目 |
| chapter_index | INTEGER | 章节序号 |
| title | TEXT | 章节标题 |
| summary | TEXT | 章节摘要 |
| content_path | TEXT | 正文文件路径（磁盘上） |
| status | TEXT | 状态：not_started / in_progress / drafted / revised / reviewed / final |
| word_count | INTEGER | 字数 |
| prev_text | TEXT | 前情提要 |

### memory_items

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| project_id | INTEGER | 所属项目 |
| type | TEXT | 类型：summary / character / outline / hook / world 等 |
| content | TEXT | 记忆内容 |
| chapter_ref | INTEGER | 关联章节（0 为全局） |

### chat_messages

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| project_id | INTEGER | 所属项目 |
| role | TEXT | 角色：user / assistant / system |
| content | TEXT | 消息内容 |
| context | TEXT | 当前阶段上下文 |
| created_at | TEXT | 时间 |

### stage_runs

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| project_id | INTEGER | 所属项目 |
| stage | TEXT | 阶段：outline / writing / polish |
| status | TEXT | 状态：pending / running / completed / paused / failed |
| started_at | TEXT | 开始时间 |
| finished_at | TEXT | 结束时间 |
| message | TEXT | 结果信息 |

---

## 5. API 接口

### 创建项目

```
POST /api/v2/projects
Body: { "name": "my_novel", "title": "星辰大海", "genre": "玄幻", "total_chapters": 30 }
```

### 启动阶段（支持 SSE 流式）

```
POST /api/v2/projects/run-stage
Body: {
  "project_name": "my_novel",
  "stage": "outline",        // outline | writing | polish
  "task": "主角性格坚毅",
  "execution_mode": "standard",
  "outline_review_mode": "manual",
  "presets": [...]
}
```

返回是 SSE 流式事件，每产出内容时发送一条 `data: {...}` 行，包含 `status`、`role`、`message` 字段。阶段结束时发送 `status: finished` 或 `status: paused`（manual 模式）。

### 大纲人工审核

```
POST /api/v2/projects/{name}/confirm-outline   → 推进到 writing 阶段
POST /api/v2/projects/{name}/reject-outline    → 保持 outline 状态，等重写
```

### AI 助理对话

```
POST /api/v2/projects/{name}/assistant/chat
Body: { "message": "我现在写到第5章，后面剧情怎么推进？", "presets": [...] }
```

助理会读取项目的大纲、已写章节、记忆，给出建议。

---

## 6. 前端项目中心

打开应用默认进入「项目中心」视图，右上角可切换回旧「Workbench」。

### 布局

```
┌─────────────────────────────────────────────────────────────────┐
│  📚 项目中心      [新建项目] [导入旧项目] [删除] [启动阶段] [停止]  │
├──────────┬──────────────────────────────┬────────────────────────┤
│ 项目列表  │      主编辑区                  │    阶段控制栏           │
│          │                              │                        │
│ 星辰大海  │  章节编辑器 / 大纲编辑器 /     │  🎯 当前阶段            │
│ 都市奇缘  │  人物设定 / AI 对话           │  章节进度：3/30        │
│ 星际漫游  │                              │  总字数：5,300         │
│          │  从左侧选择章节后开始编辑       │  [重新生成大纲]         │
│ ──────── │  点击保存将内容写入数据库       │  [继续写作] [整体润色]  │
│ 📖 章节  │                              │                        │
│ 💡 记忆  │                              │  📝 大纲等待审核        │
│ 📋 大纲  │                              │  [确认→写作] [驳回重写]  │
│ 🧑 人物  │                              │                        │
│ 🤖 AI 助理│                              │  🟢 执行中...           │
└──────────┴──────────────────────────────┴────────────────────────┘
```

### 功能清单

- **项目列表**：展示所有项目卡片（标题/阶段/章节进度/题材）
- **创建项目**：输入名称、标题、题材、目标章节数
- **导入旧项目**：一键迁移 `workspace/run_*` 目录到 v2 格式
- **章节编辑**：修改标题/摘要/正文，保存到数据库+磁盘
- **大纲编辑**：可视化编辑 `outline.md`，保存
- **人物设定**：可视化编辑 `characters.md`，保存
- **AI 助理对话**：基于项目上下文问问题，获得建议
- **阶段启动**：选择阶段（大纲/写作/审校）和模式，开始执行
- **大纲审核**：大纲完成后右侧显示审核卡片，支持"确认推进"或"驳回重写"
- **阶段进度**：实时显示章节完成数和总字数

---

## 7. 三阶段执行流程

```
┌─────────────────────────────────────────────────────────┐
│                    创建项目                              │
└──────────────────────┬──────────────────────────────────┘
                       ▼
         ┌───────────────────────────┐
         │   1. 大纲制作 (outline)    │
         │   生成 outline.md          │
         │   生成 characters.md        │
         │   生成 memory/novel_...    │
         └────────────┬───────────────┘
                      │
          ┌───────────┴───────────┐
          │ outline_review_mode    │
          │                       │
          ├─ auto ──→ 直接推进到 writing ────┤
          │                       │
          └─ manual ──→ ⏸ 暂停等待审核 ──┐
                                      │
                              用户点击"确认大纲"     用户点击"驳回重写"
                                      │              │
                                      ▼              ▼
                       ┌───────────────────────────┐
                       │   2. 正文写作 (writing)    │
                       │   逐章生成章节 .txt 文件   │
                       │   同步到 chapters/ 目录   │
                       └────────────┬───────────────┘
                                    │
                                    ▼
                       ┌───────────────────────────┐
                       │   3. 整体润色 (polish)     │
                       │   读取所有章节             │
                       │   统一风格、修复一致性      │
                       └────────────┬───────────────┘
                                    │
                                    ▼
                          ✅ 项目完成 (completed)
```

每个阶段完成后，数据自动同步到项目目录和数据库，前端刷新后可见。

---

## 8. 测试结果

测试文件：`backend/test_all.py`

```
======================================================================
  Novel Forge 全流程测试 (19 用例)
======================================================================
  ✅ 01. 创建项目
  ✅ 02. 项目列表
  ✅ 03. 写入章节
  ✅ 04. 读取单章
  ✅ 05. 更新章节
  ✅ 06. 记忆条目
  ✅ 07. 项目详情 & 进度
  ✅ 08. 阶段推进
  ✅ 09. 文件系统读写
  ✅ 10. 大纲文件
  ✅ 11. 人物设定文件
  ✅ 12. 章节文件落盘
  ✅ 13. Executor 初始化
  ✅ 14. Assistant 上下文
  ✅ 15. 多项目隔离
  ✅ 16. 大章节写入
  ✅ 17. 对话历史
  ✅ 18. 大纲确认→写作
  ✅ 19. 删除项目

======================================================================
  结果:  19 通过 / 0 失败
======================================================================
```

---

## 9. 如何运行

### 前置依赖

```bash
# Python 依赖
pip install fastapi uvicorn sse-starlette sqlite3

# Node 依赖
cd frontend && npm install
```

### 启动后端

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

后端地址：`http://localhost:8000`  
API 文档：`http://localhost:8000/docs`

### 启动前端

```bash
cd frontend
npm run dev
```

前端地址：`http://localhost:5173`（默认进入项目中心）

### 运行测试

```bash
cd backend
python test_all.py
```

### 运行迁移（把旧项目迁移到 v2）

访问前端 → 点击「导入旧项目」  
或通过 API：

```bash
curl -X POST http://localhost:8000/api/v2/projects/migrate-old
```

---

## 附录：本次修复的 Bug

| Bug | 修复内容 |
|-----|---------|
| `ProjectDB` 缺少 `get_stage()` 方法 | 补充了 `get_stage()` 方法，返回 `current_stage` 字段 |
| `get_progress()` 把 `revised` 状态排除在外 | 把 `"revised"` 加入已完成状态统计 |
| `get_chapter_count()` SQL 同样问题 | 同上，`revised` 计入已完成章节数 |
