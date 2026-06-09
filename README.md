# Omni-Agent-Hub

> 多智能体协作引擎 — 可视化编排、流水线执行、长篇小说 AI 写作

## 特性

- **三阶段流水线**：大纲创作 → 分批写作 → 全局审校，自动按 `_N` 后缀分阶段
- **Manager-Worker-Reviewer 三角色**：指挥→执行→审查反馈循环，Manager 决定何时退出
- **5 层守卫体系**：Reviewer 拒绝守卫 / 大纲产出守卫 / 章数守卫 / Stale 检测 / 幻觉检测
- **全局记忆系统**：`[MEMORY:]` + `[SUMMARY:]` 标签，跨章节保持连贯性
- **体裁感知**：融合 webnovel-writer 追读力分类学 + InkOS 33维审计体系 + Anti-AI 写作规范
- **断点续跑**：checkpoint 持久化 + 已完成阶段跳过，支持 manual 大纲审核
- **三模式适配**：standard / compatible / full，适配不同能力模型
- **60+ 内置角色**：工程/设计/产品/测试/专业领域，.md 格式可扩展
- **40+ API 端点**：任务管理 / 预设CRUD / 文件操作 / 终端测试 / SSE 实时日志
- **项目中心（Project Center）**：以项目为主体，SQLite 元数据 + 文件系统大内容，章节/记忆/大纲实时同步
- **项目模型预设持久化**：每个项目保存三角色（manager/worker/reviewer）API 配置，启动阶段自动读取，无需每次输入
- **AI 对话助理**：项目上下文感知，读取大纲/章节/记忆后生成分析建议，引擎暂停时仍可使用
- **manual 大纲审核**：大纲阶段结束后暂停，人工确认后进入写作阶段

## 快速开始

### 环境

- Python 3.8+
- Node.js 18+

### 启动

```bash
# 后端
cd backend
pip install -r requirements.txt
python main.py          # → http://127.0.0.1:8000

# 前端（新终端）
cd frontend
npm install
npm run dev             # → http://localhost:5173
```

## 架构

```
┌──────────────────────────────────────────────────────┐
│                   Frontend (React)                     │
│  App.jsx → Sidebar + Workbench + NewTaskModal         │
│  Workbench → TaskDetailModal + NovelWorkspace          │
│  Hooks: usePreset / useTask / useNovelTask / useSkill  │
└──────────────────────┬───────────────────────────────┘
                       │ SSE / REST API
┌──────────────────────▼───────────────────────────────┐
│                  Backend (FastAPI)                      │
│  main.py — 40+ API 端点                                │
│  executor.py — GraphExecutor 核心引擎                   │
│  agent_loader.py — 角色 .md 加载器                      │
│  skill_loader.py — 技能加载器                           │
│  test_runner.py — 终端测试执行器                        │
│  memory_manager.py — 记忆管理器                         │
│  hallucination_guard.py — 幻觉守卫                     │
│  genre_data/ — 体裁数据                                 │
└───────────────────────────────────────────────────────┘
```

## 核心引擎：GraphExecutor

```
execute()
  │
  ├─ _detect_pipeline_stages()  ← 按 _N 后缀分阶段
  │   m_1/w_1/r_1 → stage 1 (outline)
  │   m_2/w_2/r_2 → stage 2 (writing)
  │   m_3/w_3/r_3 → stage 3 (polish)
  │
  └─ _execute_pipeline(stages)
       │
       for each stage:
       │  ├─ 跳过已完成阶段 (resume 支持)
       │  ├─ 创建子 GraphExecutor
       │  │   _auto_connect() → M→W, W→R, R→M
       │  └─ sub._execute_phase_graph()
       │       │
       │       _compute_phases() → BFS 拓扑排序
       │       │
       │       for round 1..MAX_ROUNDS:
       │         ├─ 并发执行当前 Phase 节点
       │         ├─ 退出检查:
       │         │   ├─ Reviewer 拒绝守卫 (需修改/不通过 → 强制继续)
       │         │   ├─ Outline 产出守卫 (outline.md + characters.md)
       │         │   ├─ Writing 章数守卫 (N chapters 未达标 → 强制继续)
       │         │   └─ Manager [EXIT_LOOP] → break
       │         └─ stale_rounds ≥ 3 → break
       │
       ├─ 记录 _completed_stages
       └─ manual 模式 → paused + return
```

## 小说写作流程

```
用户输入："写一个100章的玄幻小说"
    │
    ▼
阶段1: 大纲创作 (outline)
    架构师 → 撰写者(outline.md + characters.md) → 审查者 → 架构师
    │  审查不通过 → 强制修改，直到通过
    │  manual模式 → 暂停等待人工确认
    ▼
阶段2: 分批写作 (writing)
    创作总指挥 → 小说作家(每次1章) → 章节审查者 → 创作总指挥
    │  未达100章 → 系统强制替换 [EXIT_LOOP] 为 [CONTINUE]
    │  上下文注入: 大纲 + 人物设定 + 最近3章结尾 + 全局记忆
    ▼
阶段3: 全局审校 (polish)
    主编 → 修订编辑 → 终审者 → 主编
    │
    ▼
完成 → 全部章节生成 + 审校通过
```

## 5 层守卫体系

| 层级 | 守卫 | 机制 |
|------|------|------|
| 1 | Reviewer 拒绝守卫 | "需修改"/"不通过"/"❌" → 替换 `[EXIT_LOOP]` 为 `[CONTINUE]` |
| 2 | Outline 产出守卫 | outline.md + characters.md 未产出 → 不准退出 |
| 3 | Writing 章数守卫 | 实际章数 < 目标章数 → 不准退出 |
| 4 | Stale 检测 | 3轮无新文件产出 → 自动退出 |
| 5 | 幻觉检测 | HallucinationGuard 独立模块 |

## 三模式配置

| 参数 | Standard | Compatible | Full |
|------|----------|------------|------|
| Manager max_tokens | 2000 | 3000 | 4000 |
| Worker max_tokens | 16000 | 24000 | 32000 |
| Reviewer max_tokens | 2000 | 3000 | 4000 |
| 超时 | 300s | 450s | 600s |
| Prompt 版本 | 压缩版 | 兼容版 | 原版 |
| 适用模型 | Claude/GPT-4 | GLM/Llama/Qwen | 高级模型 |

## 体裁数据融合

### webnovel-writer 追读力分类学

- 5种钩子类型（悬念/情感/冲突/反转/信息差）
- 8种爽点模式（逆袭/打脸/装逼/金手指/升级/夺宝/复仇/认亲）
- Hard Invariants（可读性底线/承诺兑现/节奏灾难/冲突真空）
- 14种体裁裁决规则（风格优先级/爽点/毒点/禁忌）

### InkOS 33维审计体系

- 5种体裁配置（玄幻/仙侠/都市/恐怖/通用）
- 疲劳词列表（"冷笑/蝼蚁/倒吸凉气/瞳孔骤缩"等 AI 高频词）
- 33维审计维度（人物一致性/情节因果链/OOC检测/战力一致性/信息泄露/AI痕迹检测/伏笔管理...）

### Anti-AI 写作规范

- 对抗 LLM 8大倾向（重复/模板化/过度解释/情感泛滥...）
- 核心创作铁律 + 爽点三段式结构
- Strand 三线节奏管理（Quest 60% / Fire 20% / Constellation 20%）

## 全局记忆系统

```
run_xxx/memory/
└── novel_memory.md   ← 累积式全局记忆
```

- **`[MEMORY: ...]`**：Manager 每5章更新，记录角色状态、主线进展、伏笔
- **`[SUMMARY: ...]`**：Manager 每10章输出，快速剧情摘要
- Worker 写新章前自动注入全局记忆(最近4000字) + 前文摘要
- 断点续跑不丢失

## API 端点

### 项目中心 v2 (`/api/v2/projects/*`)

| 类别 | 端点 | 方法 | 说明 |
|------|------|------|------|
| 项目 | `/api/v2/projects` | GET | 项目列表 |
| | `/api/v2/projects` | POST | 创建项目 |
| | `/api/v2/projects/{name}` | GET | 项目详情 |
| | `/api/v2/projects/{name}` | DELETE | 删除项目 |
| 模型预设 | `/api/v2/projects/{name}/presets` | GET | 读取三角色 API 预设 |
| | `/api/v2/projects/{name}/presets` | PUT | 保存/部分更新三角色预设 |
| 章节 | `/api/v2/projects/{name}/chapters` | GET | 章节列表 |
| | `/api/v2/projects/{name}/chapters/{idx}` | GET | 读取章节内容 |
| | `/api/v2/projects/{name}/chapters/{idx}` | PATCH | 更新章节内容 |
| 记忆 | `/api/v2/projects/{name}/memory` | GET | 记忆列表 |
| | `/api/v2/projects/{name}/memory` | POST | 新增记忆 |
| 大纲审核 | `/api/v2/projects/{name}/confirm-outline` | POST | 人工确认大纲通过 |
| | `/api/v2/projects/{name}/reject-outline` | POST | 人工拒绝大纲（带修改意见） |
| 阶段执行 | `/api/v2/projects/run-stage` | POST | 启动阶段(SSE) outline/writing/polish |
| | `/api/v2/projects/{name}/stop` | POST | 停止当前阶段 |
| AI 对话 | `/api/v2/projects/{name}/assistant-chat` | POST | 项目上下文感知对话 |
| 文件 | `/api/v2/projects/{name}/files/{path}` | GET/POST/DELETE | 项目内文件操作 |

### 传统 v1 端点

| 类别 | 端点 | 方法 | 说明 |
|------|------|------|------|
| 任务 | `/api/run-task` | POST | 启动任务(SSE) |
| | `/api/tasks/{folder}/resume` | POST | 恢复任务(SSE) |
| | `/api/stop-task` | POST | 停止任务 |
| | `/api/tasks` | GET | 任务列表 |
| | `/api/tasks/{folder}` | GET/PATCH/DELETE | 查看/更新/删除 |
| | `/api/run-task/feedback` | POST | 中途反馈 |
| 预设 | `/api/presets` | GET/POST/PUT/DELETE | CRUD |
| 文件 | `/api/workspace/files/{path}` | GET/POST/DELETE | 文件操作 |
| 角色 | `/api/agent-catalog` | GET | 角色目录 |
| 技能 | `/api/skills` | GET/POST/PUT/DELETE | CRUD |
| 测试 | `/api/test/exec` | POST | 执行测试 |
| | `/api/test/terminal/ws` | WebSocket | 终端实时交互 |
| 连接 | `/api/test-connection` | POST | 测试 API 连接 |

## 项目结构

```
omni-agent-hub/
├── backend/
│   ├── executor.py              # 核心引擎 (GraphExecutor)
│   ├── main.py                  # FastAPI 入口 (v1 + v2 共40+端点)
│   ├── project_db.py            # 项目元数据数据库 (SQLite + JSON)
│   ├── project_executor.py      # 项目级执行器 (ProjectExecutor)
│   ├── assistant.py             # 项目上下文感知 AI 对话助理
│   ├── migration.py             # 旧 run_* 目录迁移到新项目结构
│   ├── agent_loader.py          # 角色 .md 加载器
│   ├── skill_loader.py          # 技能加载器
│   ├── test_runner.py           # 测试执行引擎
│   ├── memory_manager.py        # 记忆管理器
│   ├── hallucination_guard.py   # 幻觉守卫
│   ├── genre_data/              # 体裁数据
│   ├── agents/                  # 60+ 角色 .md
│   ├── workspace/               # 文件输出 + 任务文件夹
│   └── projects/                # 项目保存 (SQLite + 内容文件)
├── frontend/
│   └── src/
│       ├── App.jsx              # 入口组件 (Project Center)
│       ├── App.css              # 全局样式
│       ├── translations.js      # 中/英 i18n
│       ├── styles/              # 设计系统
│       ├── hooks/               # 自定义 hooks
│       │   ├── usePreset.js     # 预设管理
│       │   ├── useTask.js       # 任务执行
│       │   ├── useNovelTask.js  # 小说任务
│       │   ├── useSkill.js      # 技能管理
│       │   └── useProjectV2.js  # 项目中心 v2
│       └── components/
│           ├── ProjectCenter.jsx # 项目中心 (主界面)
│           ├── Workbench.jsx    # 核心工作区
│           ├── Sidebar.jsx      # 侧边栏
│           ├── TaskDetailModal.jsx # 任务编辑
│           └── Novel/           # 小说专用组件
└── README.md
```

## 技术栈

- **前端**：React 19 + Vite，CSS 变量双主题，SSE + WebSocket
- **后端**：FastAPI + AsyncOpenAI，BFS 拓扑排序，异步并发，checkpoint 序列化
- **AI 集成**：OpenAI 兼容 API / Anthropic Claude 原生 API / thinking_mode
- **设计**：Noto Serif SC 衬线字体，"文人书斋"暖色调主题

## 致谢

- [webnovel-writer](https://github.com/EricZhu-42/webnovel-writer) — 追读力分类学、体裁裁决规则
- [InkOS](https://github.com/Narcooo/inkos) — 33维审计体系、疲劳词列表、语言铁律
