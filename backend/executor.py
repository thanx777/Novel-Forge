"""Execution engine: prompts, models, LLM calls, and the GraphExecutor orchestrator.

Extracted from main.py. Contains:
- MODE_CONFIG, framework prompts, novel stage prompts
- LLM calling (call_llm)
- GraphExecutor: BFS topology-based pipeline execution
- File extraction and workspace utilities
"""

import asyncio
import json
import os
import re
import shutil
import time
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Callable
from collections import defaultdict
from openai import AsyncOpenAI
from genre_data import detect_genre, build_genre_guide, get_strand_rules, get_reviewer_dimensions
from agent_loader import load_all_agents, build_role_catalog, get_agent_by_name
from skill_loader import load_all_skills, load_skill_content, save_skill, delete_skill, search_skills
from test_runner import parse_test_instructions, execute_test, terminal_executor_stream, is_dangerous
from memory_manager import MemoryManager
from hallucination_guard import HallucinationGuard

# ============================================
# Global agent and skill catalog
# ============================================
ALL_AGENTS = load_all_agents()
ALL_SKILLS = load_all_skills()
ROLE_CATALOG = build_role_catalog(ALL_AGENTS)

# ============================================
# Workspace configuration
# ============================================
def _load_workspace_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("workspace_dir", ""), data.get("projects_dir", "")
    except:
        pass
    return "", ""

def _resolve_workspace_dir(cfg_dir, default_subdir):
    if cfg_dir and cfg_dir.strip():
        d = os.path.abspath(cfg_dir.strip())
        os.makedirs(d, exist_ok=True)
        return d
    d = os.path.abspath(os.path.join(os.path.dirname(__file__), default_subdir))
    os.makedirs(d, exist_ok=True)
    return d

_ws_dir, _pj_dir = _load_workspace_config()
WORKSPACE_DIR = _resolve_workspace_dir(_ws_dir, "workspace")
PROJECTS_DIR = _resolve_workspace_dir(_pj_dir, "projects")

DEFAULT_STAGE_TIMEOUT_SECONDS = 600
MAX_TOKENS_BY_TYPE = {
    "manager": 2000,
    "worker": 16000,
    "reviewer": 2000,
}
DEFAULT_MAX_TOKENS = 16000
REQUEST_TIMEOUT = 300.0


# 框架指令（节点类型决定 HOW）+ 角色知识（agent .md 决定 WHAT）
# ============================================

FRAMEWORK_PROMPTS = {
    "manager": """你是【调度者】（节点类型: Manager）。你的职责：理解任务 → 分配角色 → 下达指令 → 看反馈决定继续或退出。

【铁律 — 违反任何一条都是严重失职】
1. 你不产出文件，只指挥。禁止说"我先做设计/蓝图/准备"——直接让执行者开工
2. 数量铁律：用户要 N 个就指令产出 N 个。用户说"写一个贪吃蛇"= 1 个文件，不是 5 个不是 10 个
3. 审查通过且测试通过 → 立即输出 [EXIT_LOOP]。审查说通过但测试失败 → 以测试为准，指令修复。禁止继续找事
4. 禁止要求执行者产出：清理脚本、检查报告、确认书、总结、文件列表、测试报告等元文件
5. 文件清理是你自己的职责，用 [DELETE: 文件名] 删除冗余文件，不要让执行者写清理脚本
6. 用 [ROLE: 节点ID = 角色名] 为下游节点指派角色身份
7. 用 [SKILL: 技能名] 启用 Skill
8. 用 [TEST:CMD: 命令] 等测试指令验证产出
9. 全部完成输出 [EXIT_LOOP]

【典型错误 — 绝对禁止】
❌ "请产出5个不同版本" → 用户只要1个就产出1个
❌ "请写一个文件清理脚本" → 你自己用 [DELETE:] 删
❌ "请产出测试报告/检查报告" → 不需要，审查者会测试
❌ 审查通过后继续迭代 → 通过就退出""",

    "worker": """你是【执行者】（节点类型: Worker）。你的职责：按指令产出实际文件，不聊天。

【铁律 — 违反任何一条都是严重失职】
1. 禁止说"收到/等待/准备好了"。直接干活，产出文件
2. 数量铁律：指令要几个就产几个。没有明确数量要求时，默认 1 个
3. 禁止产出元文件：不产出清理脚本、检查报告、测试报告、总结、确认书、文件列表
4. 禁止产出多版本：不要 v1/v2/v3，只产出最终版
5. 上游指令模糊就自己拿主意，别反问

【文件格式】
---FILE: 文件名.txt---
完整内容（禁止占位符、大纲、摘要）
---ENDFILE---

【典型错误 — 绝对禁止】
❌ 一次产出 5 个版本 → 除非指令明确要求 5 个
❌ 产出 file_cleanup.py / test_report.txt → 这些不是你的活
❌ 产出 snake_v1.py + snake_v2.py + ... → 只产出最终版""",

    "reviewer": """你是【审查者】（节点类型: Reviewer）。你的职责：验证产出质量，给出审查结论。

【铁律 — 违反任何一条都是严重失职】
1. 审查结论+1-2句理由即可，50字以内
2. 四种结论：通过 ✅ / 通过（附带建议）/ 需修改（指出1个关键问题）/ 不通过
3. 合格就放行，不吹毛求疵。代码能跑 = 通过
4. 审查代码/脚本/程序 → 先只输出 [TEST:CMD:] 测试指令（不要在同一句里加"通过"/"✅"），等结果返回后再单独给结论。否则被系统拦截
5. 不要建议"优化版"、"改进版"、"配置版"——审查通过就通过
6. 系统会检查你的输出：有"通过"/"✅"但没有 [TEST:] 标记 → 自动追加重审指令

【测试能力】
- [TEST:CMD: shell命令]          执行终端命令
- [TEST:CODE:python: 代码]       运行 Python 代码
- [TEST:CODE:node: 代码]         运行 Node.js 代码
- [TEST:API:GET: URL]            测试 API 接口
- [TEST:PW: 测试描述]            Playwright Web 测试（需安装）

典型用法：
- 语法检查: [TEST:CMD: python -m py_compile worker_n1/文件名.py]
- 运行测试: [TEST:CMD: python worker_n1/文件名.py]
- 依赖检查: [TEST:CMD: python -c "import 模块名"]
- 文件检查: [TEST:CMD: ls -la worker_n1/]
- Web项目: [TEST:PW: 打开 worker_n1/index.html 验证页面加载]
⚠️ HTML+JS项目禁止用 node 测浏览器代码，会报 ReferenceError 误判。
测试结果会自动返回给你，基于真实结果做判断更可靠。

【典型错误 — 绝对禁止】
❌ "建议产出优化版" → 审查通过就通过，不要建议更多工作
❌ "建议将硬编码改为可配置" → 除非用户明确要求，否则这是吹毛求疵
❌ 只凭阅读判断代码说"通过" → 没 [TEST:] 标记会被系统拦截""",
}

# ============================================
# 三模式配置：标准 / 兼容 / 满血
# ============================================

MODE_CONFIG = {
    "standard": {
        "max_tokens": {"manager": 2000, "worker": 16000, "reviewer": 2000},
        "timeout": 300,
        "reviewer_truncate": True,
        "manager_truncate_files": 30,
        "manager_prev_output": 500,
        "history_count": 5,
        "history_chars": 200,
        "role_catalog": "compact",
        "strict_exit": True,
    },
    "compatible": {
        "max_tokens": {"manager": 3000, "worker": 24000, "reviewer": 3000},
        "timeout": 450,
        "reviewer_truncate": True,
        "manager_truncate_files": 20,
        "manager_prev_output": 400,
        "history_count": 4,
        "history_chars": 150,
        "role_catalog": "compact",
        "strict_exit": False,
        "force_test": False,
    },
    "full": {
        "max_tokens": {"manager": 4000, "worker": 32000, "reviewer": 4000},
        "timeout": 600,
        "reviewer_truncate": False,
        "manager_truncate_files": 0,
        "manager_prev_output": 800,
        "history_count": 8,
        "history_chars": 300,
        "role_catalog": "full",
        "strict_exit": True,
    },
}

# 标准版 Framework Prompt（~50% 压缩，适合 Claude/GPT-4）
FRAMEWORK_PROMPTS_STANDARD = {
    "manager": """你是调度者(Manager)。分析任务→分派角色→看反馈决定退出。

规则：
1. 不写文件只指挥，直接让执行者开工
2. 用户要N个就产N个，不擅自增减
3. 审查+测试均通过→[EXIT_LOOP]。测试失败则以测试为准指令修复
4. 用[ROLE:节点ID=角色]指派，[SKILL:技能名]启用技能
5. 用[DELETE:文件名]清理冗余，用[TEST:CMD:命令]验证
6. 全部完成→[EXIT_LOOP]""",

    "worker": """你是执行者(Worker)。按指令产文件。

规则：
1. 直接干活不反问。要几个产几个，默认1个
2. 不产元文件（报告/总结/清理脚本/.sh/.bat）
3. 不产多版本(v1/v2/v3)
4. 指令模糊自己拿主意

文件格式：
---FILE: 文件名---
内容（禁止占位符）
---ENDFILE---""",

    "reviewer": """你是审查者(Reviewer)。三步：读代码→[TEST:CMD:]实测→给结论。

结论四种：通过✅/通过(附带建议)/需修改(指1个关键问题)/不通过

规则：
1. 结论+1句理由，50字内
2. 代码能跑=通过，不吹毛求疵
3. 先输出测试指令，等结果返回后再给结论。禁止在测试指令后面直接写"通过"
4. 不建议"优化版/改进版"

正确做法：只输出 [TEST:CMD: python worker_n2/文件.py]，不要加"通过✅"
错误做法：[TEST:CMD: python 文件.py] 通过✅ ← 会被系统拦截

⚠️ Web项目(HTML+JS)：禁止用 node 测浏览器代码，document/window 在 Node 下不存在会误报。用 [TEST:PW: 打开 index.html] 或无头浏览器测试。""",
}

# 兼容版 Framework Prompt（超简、全肯定句式，适合 GLM/Llama/Qwen）
FRAMEWORK_PROMPTS_COMPATIBLE = {
    "manager": """你是项目调度者。你要做三件事：
1. 根据用户需求，告诉执行者具体做什么
2. 检查审查者的反馈
3. 审查通过且测试通过后输出[EXIT_LOOP]。测试失败就指令修复

重要规则：
- 用户要几个文件就安排几个文件
- 用[ROLE:节点ID=角色名]给每个节点分配角色
- 文件都生成好了就输出[EXIT_LOOP]结束任务""",

    "worker": """你是执行者。按照指令创建文件。

规则：
- 安排几个文件就写几个文件
- 不要写：报告、总结、测试文件、清理脚本
- 不要写多个版本

文件格式：
---FILE: 文件名---
文件内容
---ENDFILE---""",

    "reviewer": """你是审查者。检查执行者的代码质量。

请这样做：
1. 先看代码理解逻辑
2. 用[TEST:CMD:命令]实际运行测试
3. 根据测试结果说"通过✅"或"需要修改"

代码能正常运行就是通过。结论要简短。""",
}

# ============================================
# 小说流水线专用 Prompt（纯文学创作，不使用测试指令）
# ============================================

NVL_STAGE_PROMPTS = {
    "outline": {
        "manager": """你是小说架构师(阶段1:大纲)。指挥 Worker 产出大纲和人物设定。

铁律：
1. 你自己不写文件！你只下达指令给 Worker，让 Worker 写
2. 从用户任务中提取：章节总数、小说类型/风格（玄幻/都市/科幻等）、世界观设定要求
3. 指令 Worker 产出 outline.md（每章1-2句梗概）+ characters.md
4. 要求包含：故事主线、主要冲突、人物关系、伏笔规划、符合用户指定的类型风格
5. 审查通过后输出 [EXIT_LOOP]，否则指令 Worker 修改
6. 你没有测试能力，禁止 [TEST:CMD:]""",

        "worker": """你是大纲撰写者(阶段1)。按架构师指令写出大纲和人物设定。

规则：
1. 产出 outline.md + characters.md 两份文件
2. 按指令中要求的章数为每章写1-2句梗概
3. 人物设定：姓名、性格、说话习惯、核心动机、角色关系
4. 严格遵循用户指定的类型和风格（如玄幻、科幻、都市等）
5. 用 ---FILE: 文件名--- / ---ENDFILE--- 格式
6. 只写大纲，不写正文""",

        "reviewer": """你是大纲审查者(阶段1)。纯文学审查。

🔴 铁律：你没有任何测试能力。禁止输出 [TEST:CMD:]、---TEST:CMD:--- 或任何形式的测试指令。你只需阅读文本给结论。

检查项：
1. 章数是否与用户任务要求一致
2. 主线是否清晰
3. 人物设定是否冲突
4. 人物关系网是否合理

结论四种：通过 ✅ / 通过（附带建议）/ 需修改（指出1个具体问题）/ 不通过
结论1-2句话。""",
    },

    "writing": {
        "manager": """你是创作总指挥(阶段2:写作)。你是监工，不是写手。

你的唯一职责：1. 看进度 2. 派任务给 Worker 3. 根据审查结果决定继续还是修改。

铁律：
1. 🔴 你绝不写文件！你只给 Worker 下指令
2. 每轮先报告进度：「当前进度：第X章/共Y章」，然后派下一章（一次只写一章，保证质量）
3. 每轮指令包含：该章大纲要点 + 上一章结尾
4. 🔴 审查说"通过"且未达总章数 → 继续下一章，绝不 [EXIT_LOOP]
5. 🔴 审查说"不通过/需修改" → 指令 Worker 修改问题章节，绝不 [EXIT_LOOP]
6. 🔴 只有全部章节完成且审查通过 → 才能 [EXIT_LOOP]
7. 大纲是创作基础，除非发现明显矛盾否则不轻易修改
8. 你没有测试能力，禁止 [TEST:CMD:]
9. 每10章左右输出 [SUMMARY: 前文摘要...] 帮 Worker 了解全貌
10. 🎯 Strand节奏管理：给每章标注类型
   ---STRAND: Quest（主线推进，占60%）| Fire（爽点高潮，占20%）| Constellation（世界观展开，占20%）
   主线断档≤5章 | 爽点断档≤10章 | 世界观断档≤15章""",

        "worker": """你是小说作家(阶段2)。按总指挥指令写章节。

铁律：
1. 只写总指挥指定的章节，每章 800-1500 字
2. 文件命名: 第N章.txt（N为章节号）
3. 一章一个文件
4. 每章开头标注：
---PREV: [上一章结尾最后一段]---
---CAST: [当前活跃角色及状态]---
---THREAD: [本章推进的情节线]---
5. 围绕大纲写，不擅自引入新角色/新情节线
6. 用 ---FILE: 第N章.txt--- 内容 ---ENDFILE--- 格式

🔄 每章写完后维护真相文件：
7. 更新 chapter_summaries.md — 追加本章1-2句摘要
8. 如有新伏笔 → 追加到 pending_hooks.md（标注章节号）
9. 如有角色状态变化 → 更新 character_state.md""",

        "reviewer": """你是章节审查者(阶段2)。纯文学审查。

🔴 铁律：你没有任何测试能力。禁止输出 [TEST:CMD:]、---TEST:CMD:--- 或任何形式的测试指令。你只需阅读文本给结论。

审查方法：
1. 本章是否按要求完成
2. 字数检查：字数800-1500
3. 衔接检查：PREV 标注与上一章结尾是否一致
4. 大纲一致性：内容是否符合大纲对应梗概
5. 幻觉检查：是否有大纲中没有的新角色出现

审查标准：
- PREV/CAST/THREAD 缺失 → 不通过
- 章节数不足 → 需修改
- 字数严重偏离(<500或>2000) → 需修改
- 衔接断裂(PREV与实际不符) → 需修改
- 大纲外新角色/新情节 → 不通过

结论四种：通过 ✅ / 通过（附带建议）/ 需修改（指哪章什么问题）/ 不通过
结论1-2句话。""",
    },

    "polish": {
        "manager": """你是主编(阶段3:审校)。指挥 Worker 修改问题章节。

铁律：
1. 你自己不写文件！你只下达修改指令给 Worker
2. 全局检查：前后矛盾（人名/地名/时间线）、伏笔回收、文风统一
3. 指定要修改的具体章节和具体问题，交给 Worker
4. 全部问题修复且审查通过 → [EXIT_LOOP]
5. 你没有测试能力，禁止 [TEST:CMD:]""",

        "worker": """你是修订编辑(阶段3)。按主编要求修改指定章节。

规则：
1. 只修改主编指定的章节，不动其他章节
2. 保持字数在800-1500字
3. 保持 PREV/CAST/THREAD 标注更新
4. 修改后标注修改内容
5. 如果修改涉及人物状态变化，更新 character_state.md
6. 如果新增/回收了伏笔，更新 pending_hooks.md
7. 修改后更新 chapter_summaries.md 中对应章节的摘要""",

        "reviewer": """你是终审者(阶段3)。纯文学审查。

🔴 铁律：你没有任何测试能力。禁止输出 [TEST:CMD:]、---TEST:CMD:--- 或任何形式的测试指令。你只需阅读文本给结论。

审查维度（逐项检查，不可跳过）：
1. 人物一致性 — 名字无错字、性格行为不OOC、能力体系不崩坏
2. 情节连贯性 — 事件因果链完整、无逻辑跳脱、时间线正确
3. 伏笔管理 — 已埋伏笔是否回收、新伏笔标记是否清晰
4. AI痕迹检测 — 重复句式/段落模板/万能形容词滥用/"说道"滥用超过2次
5. 章节节奏 — 起承转合是否完整、高潮分布是否合理、有无灌水段落
6. 世界观一致 — 力量体系/设定规则不前后矛盾
7. 信息泄露 — 角色不会知道未亲身经历的事、不会预知未来
8. 对话真实感 — 符合角色性格和身份、不过度解释、口语化自然
9. 情感逻辑 — 角色行为动机合理、情感转变有铺垫
10. 字数质量 — 正文800-1500字、标注行不计入、无凑字灌水

11. Hook追踪 — 章末是否有悬念钩子？本章是否承接了上章的钩子？
12. 爽点密度 — 本章是否包含爽点？每10章是否有里程碑式胜利？
13. 微兑现 — 小伏笔是否按时回收？之前章节的承诺是否在本章兑现？
14. 节奏灾难 — 是否连续多章无实质剧情推进？是否出现水章灌水？

结论: 通过 ✅ / 需修改（指出第几章、第几维度、什么问题）""",
    },
}

# 兼容版小说流水线 Prompt（适合 GLM/Llama/Qwen 等低级模型）
# 特点：指令极其明确、分步指导、全肯定句式、减少抽象概念
NVL_STAGE_PROMPTS_COMPATIBLE = {
    "outline": {
        "manager": """你是小说架构师。你要做一件事：让执行者写出大纲和人物设定。

你需要做的：
1. 从用户任务中提取：章节总数、小说类型/风格（玄幻/都市/科幻等）
2. 告诉执行者写出 outline.md（每章一句话概括）和 characters.md（人物介绍）
3. 章数从用户任务里找。用户说多少章就写多少章，严格按照用户要求
4. 检查产出：章数对不对？人物有没有冲突？类型风格是否符合？
5. 检查没问题就输出 [EXIT_LOOP]

重要提醒：
- 你自己不写文件，只下指令
- 不要输出测试指令
- 检查通过就 [EXIT_LOOP]""",

        "worker": """你是大纲撰写者。按照要求写出两个文件。

要写的文件：
1. outline.md — 每章一句话梗概，共N章
2. characters.md — 人物名字、性格、说话方式、动机、和其他人的关系

文件写法：
---FILE: outline.md---
大纲内容
---ENDFILE---

---FILE: characters.md---
人物设定
---ENDFILE---

注意：
- 只写这两个文件
- 不要写正文""",

        "reviewer": """你是大纲审查者。请检查两个文件的质量。

检查什么：
1. 章数够不够（用户说多少章就是多少章）
2. 故事主线是否清楚
3. 人物之间有没有矛盾
4. 人物关系合不合理

结论说一种：
- 通过 ✅ — 没问题
- 需修改 — 说出具体哪里要改
- 不通过 — 说出严重问题

不要输出测试指令。只需要阅读后给结论。""",
    },

    "writing": {
        "manager": """你是创作总指挥。你的工作是告诉执行者写哪些章，然后检查。

你需要这样做：
第一步：看大纲和已写章节，确定接下来写哪一章
第二步：告诉创作作家写第N章，给出该章的大纲要点
第三步：等初审结果。通过且还没写完 → 回到第一步继续
第四步：初审通过后，让润色作家打磨这一章
第五步：全部写完了 → 输出 [EXIT_LOOP]

重要规则：
- 你自己绝对不写文件，只下指令给执行者
- 一次只写一章，保证每章质量
- 每次先报进度：「进度：第X章/共Y章已完成」
- 不到最后一章绝不 [EXIT_LOOP]
- 初审说"需修改"或"不通过" → 让创作作家改
- 终审说"需修改" → 让润色作家打磨
- 不要输出测试指令
- 每5章输出一次 [MEMORY: 更新全局记忆，记录：(1)角色状态变化 (2)主线推进 (3)新伏笔或伏笔回收 (4)关键事件] 让所有 agent 了解整部小说进展
- 每10章输出一次 [SUMMARY: 最近剧情的简明摘要] 让创作作家快速了解前文
- 🎯 每章指定类型（三选一）：Quest主线推进 | Fire爽点高潮 | Constellation世界观展开
  主线不断档超过5章，爽点不断档超过10章，世界观不断档超过15章""",

        "w_a": """你是创作作家。按总指挥的指令写章节初稿。

每章的要求：
- 字数：800到1500字
- 文件名：第N章.txt
- 一章一个文件

每章开头要写三个标注：
---PREV: [上一章结尾最后一段]---
---CAST: [当前出场角色及状态]---
---THREAD: [本章推进的故事线]---

文件写法：
---FILE: 第N章.txt---
---PREV: ...
---CAST: ...
---THREAD: ...
正文内容
---ENDFILE---

注意：
- 只写总指挥指定的章
- 严格按大纲写，不自己加新人物、新故事线
- 不写报告、不写总结

写完每章后维护三个文件：
- chapter_summaries.md — 追加本章1-2句摘要
- pending_hooks.md — 如有新伏笔就追加进去（标注章节号）
- character_state.md — 如有角色状态变化就更新""",

        "r_a": """你是内容审查者。只检查内容是否正确，不检查格式和衔接。

检查的项目：
1. 本章是否按要求完成
2. 字数检查：800到1500字吗？
3. 内容和大纲的梗概是否一致？
4. 有没有大纲里没出现过的新角色或新情节？（这是幻觉！）
5. 人物性格和说话方式是否符合设定？

结论说一种：
- 通过 ✅ — 内容合格，可以交给润色
- 需修改 — 指出哪章有什么内容问题（只讲内容，不讲格式）
- 不通过 — 出现不该有的新角色或严重偏离大纲

5. 本章最后有没有留下悬念钩子？读者看了会不会想继续看下一章？
6. 有没有爽点（打脸/碾压/逆袭）？本章会不会让读者觉得平淡？

不要输出测试指令。只需要阅读后给结论。""",

        "w_b": """你是润色作家。内容审查通过后，你来打磨章节的文笔。

你要做的事：
1. 读一遍章节内容，保持情节不变
2. 改善文笔：对话更自然、描写更生动、节奏更流畅
3. 检查并更新 ---PREV:---、---CAST:---、---THREAD:--- 标注
4. 修改后字数保持在800到1500字

文件写法（重写润色后的章节）：
---FILE: 第N章.txt---
---PREV: ...
---CAST: ...
---THREAD: ...
润色后的正文
---ENDFILE---

注意：
- 不改变情节和人物设定
- 不新增角色和事件
- 只打磨已有内容，不做大改""",

        "r_b": """你是终审者。润色完成后做最终检查，确保衔接和格式都正确。

检查的项目：
1. 每章 ---PREV:---、---CAST:---、---THREAD:--- 标注都正确吗？
3. PREV标注和上一章结尾能接上吗？（衔接检查）
4. 人名、地名、时间线前后一致吗？
5. 字数在800到1500字吗？

结论说一种：
- 通过 ✅ — 全部合格
- 需修改 — 指出具体章和问题（格式或衔接）

不要输出测试指令。只需要阅读后给结论。""",
    },

    "polish": {
        "manager": """你是主编。找出章节里的问题，让执行者修改。

你要做的事：
1. 全局检查所有章节：前后矛盾？人名地名时间线？伏笔回收？文风统一？
2. 指出具体哪章哪有问题，让修订编辑改
3. 修订完成后，让精修编辑做最后打磨
4. 问题都修好就输出 [EXIT_LOOP]

注意：
- 你自己不写文件
- 不要输出测试指令""",

        "w_a": """你是修订编辑。按主编的要求修改指定章节。

你要做的事：
1. 只改主编指定的章节
2. 修复主编指出的具体问题（矛盾、漏洞、不一致）
3. 修改后字数保持在800到1500字
4. 保持 ---PREV:---、---CAST:---、---THREAD:--- 标注正确
5. 改完后说明改了哪里

注意：
- 不创建新文件，只修改已有章节
- 不动主编没指定的章节""",

        "r_a": """你是初审编辑。逐项检查主编指出的问题是否都修好了。

检查什么：
1. 主编说的问题修好了吗？一条条对照
2. 修改有没有引入新问题？（人物OOC、情节矛盾、时间线错乱）
3. 主角性格和说话风格前后一致吗？
4. 字数在800-1500字吗？
5. AI痕迹（重复句式、万能形容词、过多"说道"）

结论：
- 通过 ✅ — 问题都修好了，交给精修
- 需修改 — 指出还有哪些内容问题

不要输出测试指令。""",

        "w_b": """你是精修编辑。问题修复完成后，做最后的文字打磨。

你要做的事：
1. 通读修订后的章节
2. 精修文笔：统一文风、优化对话、润色描写、调整节奏
3. 检查 ---PREV:---、---CAST:---、---THREAD:--- 标注是否需要更新
4. 确保字数在800到1500字

文件写法（重写精修后的章节）：
---FILE: 第N章.txt---
---PREV: ...
---CAST: ...
---THREAD: ...
精修后的正文
---ENDFILE---

注意：
- 不改变情节结构和人物设定
- 只做文字层面的提升""",

        "r_b": """你是终审编辑。精修完成后做最终检查。

检查什么：
1. 全文一致性：主角性格、说话风格前后统一吗？
2. 伏笔都回收了吗？有没有断掉的线索？
3. 人名地名时间线全部一致吗？
4. 所有章节格式正确吗？

结论：
- 通过 ✅ — 全部合格
- 需修改 — 指出具体问题

不要输出测试指令。""",
    },
}

# 节点类型（Manager/Worker/Reviewer）决定框架行为（HOW）
# 角色身份（代码审查员/创意作家 等）决定领域知识（WHAT）
# 角色身份由 Manager 通过 [ROLE: 节点ID = 角色名] 分配，未分配时回退到通用助手
DEFAULT_ROLE_BY_TYPE = {
    "manager": "通用助手",
    "worker": "通用助手",
    "reviewer": "通用助手",
}


# 模型
# ============================================

class AgentConfig(BaseModel):
    api_key: str
    base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    model: str = "glm-4-flash"
    api_format: str = "openai"
    chat_template_kwargs: Optional[dict] = None
    thinking_mode: Optional[str] = None  # "enabled" | "disabled" | None (仅 DeepSeek 等支持思考模式的模型)

class NodeInfo(BaseModel):
    id: str
    type: str  # manager, worker, reviewer
    config: dict = {}

class ConnectionInfo(BaseModel):
    id: str
    from_node: str = Field(default="", alias="from")
    from_port: str = Field(default="", alias="fromPort")
    to_node: str = Field(default="", alias="to")
    to_port: str = Field(default="", alias="toPort")
    annotation: str = ""

    model_config = {"populate_by_name": True}

class OptimizePromptRequest(BaseModel):
    task: str
    preset: dict

class GraphTaskRequest(BaseModel):
    task: str
    nodes: List[NodeInfo]
    connections: List[ConnectionInfo]
    presets: List[dict] = []
    skills: List[str] = []
    conversation_history: List[dict] = []
    stage_timeout_seconds: int = DEFAULT_STAGE_TIMEOUT_SECONDS
    execution_mode: str = "standard"  # "standard" | "compatible" | "full"
    outline_review_mode: str = "auto"  # "auto" | "manual"

class WorkspaceConfig(BaseModel):
    path: str

class FolderStructure(BaseModel):
    folders: List[str]

# ============================================

# ============================================
# 系统提示词解析
# ============================================

def resolve_system_prompt(node_type: str, config: dict, skills: List[str] = None, execution_mode: str = "standard", novel_stage: str = "", node_id: str = "") -> tuple:
    """解析节点的系统提示词。
    框架指令（节点类型决定 HOW）+ 角色知识（agent .md 决定 WHAT）+ Skill（领域规范）
    优先级: custom_prompt > agent_role > 默认角色
    Skill 始终追加（即使在 custom_prompt 模式下）
    三模式：standard=压缩版, compatible=兼容版, full=原版
    novel_stage="outline"/"writing"/"polish" 时使用小说流水线专用 prompt
    node_id 用于兼容版识别 w_a/w_b/r_a/r_b 变体

    Returns: (system_prompt, icon, role_name)
    """
    custom_prompt = config.get("custom_prompt", "").strip()
    if custom_prompt:
        full_prompt = custom_prompt
        icon, role_name = "✨", "自定义"
    else:
        # 小说流水线模式：使用阶段专用 prompt（按执行模式选 standard/compatible 版本）
        # 角色已内置在 prompt 中，无需从 agent 目录加载
        if novel_stage and novel_stage in NVL_STAGE_PROMPTS:
            prompt_key = node_type  # default: "manager", "worker", "reviewer"
            if execution_mode in ("compatible", "full") and novel_stage in NVL_STAGE_PROMPTS_COMPATIBLE:
                stage_prompts = NVL_STAGE_PROMPTS_COMPATIBLE[novel_stage]
                # 检测润色变体节点：w_2a→w_a, w_2b→w_b, r_2a→r_a, r_2b→r_b
                if node_id and node_type in ("worker", "reviewer"):
                    import re as _nvl_re
                    m = _nvl_re.match(r'^([wr])_\d+([ab])$', node_id)
                    if m:
                        prompt_key = m.group(1) + "_" + m.group(2)  # "w_a", "r_b"
                framework = stage_prompts.get(prompt_key, stage_prompts.get(node_type, stage_prompts.get("worker", "")))
            else:
                stage_prompts = NVL_STAGE_PROMPTS[novel_stage]
                framework = stage_prompts.get(node_type, stage_prompts.get("worker", ""))
            full_prompt = framework
            # 小说流水线固定角色名和图标
            novel_icons = {
                ("outline", "manager"): ("📐", "小说架构师"),
                ("outline", "worker"): ("✍️", "大纲撰写者"),
                ("outline", "reviewer"): ("🔍", "大纲审查者"),
                ("writing", "manager"): ("🎬", "创作总指挥"),
                ("writing", "worker"): ("✍️", "小说作家"),
                ("writing", "reviewer"): ("🔍", "章节审查者"),
                ("writing", "w_a"): ("✍️", "创作作家"),
                ("writing", "r_a"): ("🔍", "内容审查者"),
                ("writing", "w_b"): ("🖋️", "润色作家"),
                ("writing", "r_b"): ("✅", "终审者"),
                ("polish", "manager"): ("📰", "主编"),
                ("polish", "worker"): ("✏️", "修订编辑"),
                ("polish", "reviewer"): ("✅", "终审者"),
                ("polish", "w_a"): ("✏️", "修订编辑"),
                ("polish", "r_a"): ("🔍", "初审编辑"),
                ("polish", "w_b"): ("🖋️", "精修编辑"),
                ("polish", "r_b"): ("✅", "终审编辑"),
            }
            icon, role_name = novel_icons.get((novel_stage, prompt_key), novel_icons.get((novel_stage, node_type), ("🤖", node_type)))
        else:
            # 按执行模式选择 framework prompt
            if execution_mode == "compatible":
                prompts = FRAMEWORK_PROMPTS_COMPATIBLE
            elif execution_mode == "full":
                prompts = FRAMEWORK_PROMPTS
            else:
                prompts = FRAMEWORK_PROMPTS_STANDARD
            framework = prompts.get(node_type, prompts.get("worker", ""))

            # 获取 agent 角色知识（通用模式）
            agent_role = config.get("agent_role", "").strip()
            if agent_role:
                agent = get_agent_by_name(ALL_AGENTS, agent_role)
                if agent:
                    full_prompt = framework + "\n\n---\n\n" + agent["content"]
                    icon, role_name = agent["emoji"], agent["name"]
                else:
                    full_prompt = framework
                    icon, role_name = "🤖", agent_role
            else:
                default_name = DEFAULT_ROLE_BY_TYPE.get(node_type, "通用助手")
                agent = get_agent_by_name(ALL_AGENTS, default_name)
                if agent:
                    full_prompt = framework + "\n\n---\n\n" + agent["content"]
                    icon, role_name = agent["emoji"], agent["name"]
                else:
                    full_prompt = framework
                    icon, role_name = "🤖", node_type

    # === 注入 Skill（追加到 system prompt，不影响 icon/role_name）===
    if skills:
        skill_blocks = []
        for skill_name in skills:
            skill_data = load_skill_content(skill_name)
            if skill_data and skill_data.get("apply_to"):
                if node_type in skill_data["apply_to"] or "all" in skill_data["apply_to"]:
                    # 提取该角色专属内容 + 共享内容
                    content = extract_role_content(skill_data["content"], node_type)
                    if content:
                        skill_blocks.append(f"【Skill: {skill_data['name']}】\n{content}")
        if skill_blocks:
            full_prompt += "\n\n" + "\n\n".join(skill_blocks)

    
    return full_prompt, icon, role_name


def extract_role_content(skill_content: str, node_type: str) -> str:
    """从 Skill 内容中提取该节点类型对应的部分。
    约定：## [worker] / ## [manager] / ## [reviewer] 标记角色段。
    无标记内容对所有角色可见。旧格式无任何角色标记时，全部内容返回。"""
    import re as _re
    # 检查是否有角色标记
    role_sections = _re.split(r'^##\s*\[(worker|manager|reviewer)\]\s*$', skill_content, flags=_re.MULTILINE)
    if len(role_sections) == 1:
        # 无角色标记 → 旧格式，全部返回
        return skill_content.strip()

    # role_sections 结构: [前置共享文本, role1, content1, role2, content2, ...]
    shared = role_sections[0].strip()
    parts = [shared] if shared else []

    for i in range(1, len(role_sections), 2):
        role = role_sections[i]
        content = role_sections[i + 1] if i + 1 < len(role_sections) else ""
        if role == node_type:
            parts.append(content.strip())

    return "\n\n".join(p for p in parts if p) if parts else skill_content.strip()
# ============================================
# 工作区工具函数
# ============================================

def _count_chapters(file_list):
    """从文件列表中提取章节号集合。支持 '第N章.txt' 和 'chapterN.txt' 格式。"""
    ch_nums = set()
    for f in file_list:
        bn = os.path.basename(f)
        m = re.match(r'第(\d+)章', bn)
        if m:
            ch_nums.add(int(m.group(1)))
        elif 'chapter' in bn.lower():
            digits = ''.join(c for c in bn if c.isdigit())
            if digits:
                ch_nums.add(int(digits))
    return ch_nums


def get_safe_path(filename: str):
    filepath = os.path.abspath(os.path.join(WORKSPACE_DIR, filename))
    workspace_norm = os.path.normpath(WORKSPACE_DIR)
    filepath_norm = os.path.normpath(filepath)
    if not filepath_norm.startswith(workspace_norm + os.sep) and filepath_norm != workspace_norm:
        raise HTTPException(status_code=400, detail=f"Invalid path: {filename}")
    return filepath

def get_full_path(filename: str):
    return os.path.abspath(os.path.join(WORKSPACE_DIR, filename))

class FileContent(BaseModel):
    content: str

# ============================================
# LLM 调用
# ============================================

async def call_llm(
    config: AgentConfig,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    request_timeout_seconds: float,
):
    api_key = config.api_key.strip()
    base_url = config.base_url.strip().strip("`").strip()
    model = config.model.strip()
    api_format = getattr(config, "api_format", "openai")

    if not api_key:
        return "Error: API Key 未配置"
    if not base_url or not model:
        return "Error: Base URL 或模型名未配置"
    try:
        if api_format == "claude":
            import httpx

            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

            payload = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}
                ],
                "temperature": 0.7
            }

            async with httpx.AsyncClient(timeout=request_timeout_seconds) as client:
                response = await client.post(base_url, json=payload, headers=headers)

            if response.status_code != 200:
                return f"Error: {response.status_code} - {response.text[:500]}"

            result = response.json()
            full_content = result.get("content", [{}])[0].get("text", "")

        else:
            client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=request_timeout_seconds, max_retries=0)
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": max_tokens
            }

            if config.chat_template_kwargs:
                kwargs["extra_body"] = {"chat_template_kwargs": config.chat_template_kwargs}
            elif "nvidia.com" in base_url:
                kwargs["extra_body"] = {"chat_template_kwargs": {"thinking": False}}
            elif "deepseek.com" in base_url:
                # DeepSeek V4 思考模式：默认关闭（写小说不需要），可通过 thinking_mode 开关
                mode = getattr(config, "thinking_mode", None) or "disabled"
                kwargs["extra_body"] = {"thinking": {"type": mode}}
            kwargs["stream"] = False

            response = await client.chat.completions.create(**kwargs)

            full_content = ""
            if response.choices and response.choices[0].message:
                msg = response.choices[0].message
                full_content = msg.content or ""
                # DeepSeek 思考模式下 content 可能为空，用 reasoning_content 兜底
                if not full_content.strip() and getattr(msg, "reasoning_content", None):
                    full_content = msg.reasoning_content or ""

        if not full_content.strip():
            return "Error: 模型返回为空，可能是当前模型不支持该请求格式"
        return full_content
    except Exception as e:
        error_msg = str(e)
        if "timed out" in error_msg.lower():
            if "nvidia.com" in base_url:
                return f"Error: NVIDIA API 超时。建议尝试更快的模型或减少任务复杂度"
            return f"Error: 请求超时"
        elif "401" in error_msg or "api_key" in error_msg.lower():
            return f"Error: API Key 无效或认证失败"
        elif "403" in error_msg:
            return f"Error: 访问被拒绝"
        elif "404" in error_msg or "not found" in error_msg.lower():
            return f"Error: 模型不存在"
        elif "429" in error_msg or "rate" in error_msg.lower():
            return f"Error: 请求频率过高"
        return f"Error: {error_msg[:300]}"


def is_llm_error(text: str) -> bool:
    return text.strip().startswith("Error:")

def _strip_markdown_fences(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        start_idx = 0
        end_idx = len(lines)
        if lines[0].strip().startswith("```"):
            start_idx = 1
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end_idx = i
                break
        if end_idx <= start_idx:
            end_idx = len(lines)
        content = "\n".join(lines[start_idx:end_idx]).strip()
    return content

def extract_and_save_files(text: str, subfolder: str = "") -> list:
    """从LLM输出中提取文件并保存。支持多种格式。"""
    patterns = [
        r"---FILE:\s*([^\-]+?)---\n(.*?)\n---ENDFILE---",
        r"----FILE:\s*([^\-]+?)----\n(.*?)\n----ENDFILE----",
        r"```file:\s*([^\n]+)\n(.*?)```",
        r"```(\w+)\s+(?:#\s*(?:file(?:name)?|文件名?)[=:]\s*(\S+))\n(.*?)```",
    ]
    saved_files = []
    placeholder_names = {"文件名.txt", "filename.txt", "file.txt", "output.txt", "untitled.txt",
                         "文件名.md", "filename.md", "file.md", "output.md"}
    meta_keywords = ['清理', '报告', '检查', '确认', '总结', '清单', '验证', '退出条件',
                     '列表', '任务状态', '状态分析', '继续决策', '状态卡', '要点',
                     '指令', '写作指令', '审校指令', '任务完成',
                     'cleanup', 'report', 'summary', 'check', 'verify', 'confirm', 'review',
                     'file_list', 'task_status', 'cleanup_report', 'story_notes', 'plan']
    meta_extensions = {'.sh', '.bat', '.cmd', '.ps1'}
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            for m in matches:
                if len(m) == 2:
                    filename, content = m[0], m[1]
                elif len(m) == 3:
                    filename = m[1] if m[1] else f"output.{m[0]}"
                    content = m[2]
                else:
                    continue
                filename = filename.strip()
                content = _strip_markdown_fences(content.strip())
                if filename.lower() in placeholder_names:
                    continue
                bn = os.path.basename(filename).lower()
                if any(kw in bn for kw in meta_keywords):
                    continue
                _, ext = os.path.splitext(bn)
                if ext in meta_extensions:
                    continue
                if len(content) < 50:
                    continue
                if subfolder:
                    filename = os.path.join(subfolder, filename)
                try:
                    filepath = get_safe_path(filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    saved_files.append(filename)
                except Exception:
                    pass
            if saved_files:
                break

    if not saved_files:
        fence_pattern = r"```(\w+)\n(.*?)```"
        fence_matches = re.findall(fence_pattern, text, re.DOTALL)
        for lang, code in fence_matches:
            code = code.strip()
            if len(code) < 50:
                continue
            ext_map = {"python": ".py", "py": ".py", "javascript": ".js", "js": ".js",
                       "typescript": ".ts", "ts": ".ts", "html": ".html", "css": ".css",
                       "java": ".java", "c": ".c", "cpp": ".cpp", "go": ".go",
                       "rust": ".rs", "ruby": ".rb", "php": ".php", "sh": ".sh",
                       "bash": ".sh", "sql": ".sql", "json": ".json", "yaml": ".yaml",
                       "xml": ".xml", "markdown": ".md", "md": ".md"}
            ext = ext_map.get(lang.lower())
            if not ext:
                continue
            first_line = code.split("\n")[0] if code else ""
            fn_match = re.match(r'#\s*(?:file(?:name)?|文件名?)[=:]\s*(\S+)', first_line, re.IGNORECASE)
            if fn_match:
                filename = fn_match.group(1).strip()
            else:
                continue
            content = _strip_markdown_fences(code)
            if len(content) < 50:
                continue
            bn = os.path.basename(filename).lower()
            if any(kw in bn for kw in meta_keywords):
                continue
            _, ext = os.path.splitext(bn)
            if ext in meta_extensions:
                continue
            if subfolder:
                filename = os.path.join(subfolder, filename)
            try:
                filepath = get_safe_path(filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                saved_files.append(filename)
            except Exception:
                pass

    return saved_files

# ============================================
# 图谱执行引擎（核心）
# ============================================

class GraphExecutor:
    """基于节点连接图谱的任务执行引擎。

    按照图谱的拓扑顺序执行节点：
    - 第一阶段：入口节点（Manager 或无输入连线的节点）接收用户任务

    _current_executor = None  # 模块级引用，供 /api/stop-task 取消
    _active_executors = set()  # 所有活跃的 executor（含子 executor），用于递归取消
    - 后续阶段：节点接收上游输出后执行
    - 同阶段节点并发执行
    - 每个节点是独立的 LLM 调用，使用自己的系统提示词和 API 配置
    - 消息沿连线传递，连线标注提供上下文
    """

    def __init__(self, nodes: List[NodeInfo], connections: List[ConnectionInfo],
                 task: str, presets: List[dict], skills: List[str] = None,
                 conversation_history: List[dict] = None, execution_mode: str = "standard",
                 prev_stage_files: List[str] = None, run_subfolder: str = "",
                 outline_review_mode: str = "auto"):
        GraphExecutor._current_executor = self
        self.cancelled = False
        self._current_llm_task = None  # 用于 stop 端点取消正在进行的 LLM 调用
        self.feedback_queue = asyncio.Queue()  # 用户中途反馈消息队列
        self.pending_feedback = []  # 待 Manager 处理的反馈
        self.nodes = {n.id: n for n in nodes}
        self.connections = connections
        self.task = task
        self.presets = {p.get("name", ""): p for p in presets}
        self.skills = skills or []
        self.active_skills = []
        self.conversation_history = conversation_history or []
        self.execution_mode = execution_mode
        self.mode_cfg = MODE_CONFIG.get(execution_mode, MODE_CONFIG["standard"])
        self.prev_stage_files = prev_stage_files or []
        self.run_subfolder = run_subfolder
        self._guard_override = ''
        self._novel_summary = ''  # 前文摘要，由 Manager 的 [SUMMARY:] 标签更新
        self._completed_stages = []  # 流水线已完成的阶段名列表
        self._novel_memory = ''   # 全局记忆（累积式），由 Manager 的 [MEMORY:] 标签更新
        self._memory_loaded = False
        self.outline_review_mode = outline_review_mode

        if not connections and len(self.nodes) > 1:
            self.connections = self._auto_connect()

        self.outgoing = defaultdict(list)
        self.incoming = defaultdict(list)
        for conn in self.connections:
            fid = conn.from_node
            tid = conn.to_node
            self.outgoing[fid].append(conn)
            self.incoming[tid].append(conn)

        # 执行状态
        self.outputs = {}
        self.saved_files = []
        self.node_icons = {}
        self.node_roles = {}
        self._consecutive_approvals = 0

    def _auto_connect(self) -> List[ConnectionInfo]:
        managers = [nid for nid, n in self.nodes.items() if n.type == "manager"]
        workers = [nid for nid, n in self.nodes.items() if n.type == "worker"]
        reviewers = [nid for nid, n in self.nodes.items() if n.type == "reviewer"]
        conns = []
        idx = 0
        for mgr in managers:
            for w in workers:
                conns.append(ConnectionInfo(id=f"auto_{idx}", from_node=mgr, to_node=w, annotation=""))
                idx += 1
        for w in workers:
            for r in reviewers:
                conns.append(ConnectionInfo(id=f"auto_{idx}", from_node=w, to_node=r, annotation=""))
                idx += 1
        for r in reviewers:
            for mgr in managers:
                conns.append(ConnectionInfo(id=f"auto_{idx}", from_node=r, to_node=mgr, annotation=""))
                idx += 1
        return conns

    def _get_config(self, node: NodeInfo) -> AgentConfig:
        """从节点配置解析 API 配置"""
        preset_name = node.config.get("preset_name", "")
        preset = self.presets.get(preset_name, {})
        if not preset and self.presets:
            preset = list(self.presets.values())[0]
        return AgentConfig(
            api_key=preset.get("api_key", ""),
            base_url=preset.get("base_url", "https://integrate.api.nvidia.com/v1"),
            model=preset.get("model", "meta/llama-4-maverick-17b-128e-instruct"),
            api_format=preset.get("api_format", "openai"),
            chat_template_kwargs=preset.get("chat_template_kwargs"),
            thinking_mode=preset.get("thinking_mode"),
        )

    def _compute_phases(self):
        """计算执行阶段。基于拓扑排序，确保依赖关系。
        回边（形成循环的连线）会被标记但不会阻塞阶段计算。"""
        phases = []
        completed = set()

        # 入口节点：Manager 类型 或 无输入连线
        entry_ids = set()
        for nid, node in self.nodes.items():
            if node.type == "manager":
                entry_ids.add(nid)
            elif nid not in self.incoming or len(self.incoming[nid]) == 0:
                entry_ids.add(nid)

        if not entry_ids and self.nodes:
            # 所有节点都有入边（全是循环），选第一个Manager或第一个节点
            for nid, node in self.nodes.items():
                if node.type == "manager":
                    entry_ids = {nid}
                    break
            if not entry_ids:
                entry_ids = {list(self.nodes.keys())[0]}

        # BFS 计算阶段（跳过回边避免无限循环）
        current = entry_ids
        while current:
            phases.append(list(current))
            completed.update(current)
            next_phase = set()
            for nid in current:
                for conn in self.outgoing.get(nid, []):
                    tid = conn.to_node
                    if tid in completed:
                        continue  # 回边，跳过
                    if tid not in self.nodes:
                        continue
                    # 检查 tid 的所有非回边输入是否都已完成
                    tid_incoming = self.incoming.get(tid, [])
                    all_done = all(
                        inc.from_node in completed or inc.from_node not in self.nodes
                        for inc in tid_incoming
                    )
                    if all_done:
                        next_phase.add(tid)
            current = next_phase

        return phases

    async def _execute_node(self, node: NodeInfo, phase_inputs: List[dict],
                            round_context: dict = None, yield_func=None) -> str:
        """执行单个节点：收集输入 → 构建提示词 → 调用LLM → 提取文件 → 返回输出
        round_context: 多轮迭代的进度上下文 {round, files, has_loop}"""
        nid = node.id
        round_num = round_context.get("round", 1) if round_context else 1

        # 解析系统提示词
        # 合并用户手动选的 Skill + Manager 自动分配的 Skill（去重）
        merged_skills = list(dict.fromkeys(self.skills + self.active_skills))
        novel_stage = getattr(self, '_novel_stage', '')
        system_prompt, icon, role_name = resolve_system_prompt(node.type, node.config, merged_skills, self.execution_mode, novel_stage, nid)
        self.node_icons[nid] = icon
        self.node_roles[nid] = role_name

        # === 体裁模板注入（按节点类型分配不同数据）===
        genre_info = detect_genre(self.task)
        if novel_stage in ("writing", "polish"):
            genre_guide = build_genre_guide(genre_info, novel_stage)
            if genre_guide:
                system_prompt += genre_guide
            # 按节点类型注入 InkOS 节点特定数据
            if genre_info.get("name", "通用") != "通用":
                from genre_data.inkos_data import get_inkos_genre, get_fatigue_words, get_chapter_types
                inkos = None
                for ink_name in ["玄幻", "仙侠", "都市", "恐怖"]:
                    if ink_name in genre_info.get("name", ""):
                        inkos = get_inkos_genre(ink_name)
                        break
                fw = (inkos or {}).get("fatigueWords", [])[:4]
                ct = (inkos or {}).get("chapterTypes", [])
                rp = genre_info.get("rhythm_strategy", "")
                sp = genre_info.get("style_priority", [])

                if node.type == "manager":
                    # Manager: 节奏策略 + Strand + 章节分类
                    strand_rules = get_strand_rules()
                    system_prompt += f"\n\n{strand_rules}"
                    yield_func({
                        "status": "info", "role": "📖 体裁",
                        "message": f"{genre_info['name']} | 风格: {'>'.join(sp[:2])} | {rp[:30]}"
                    })
                    if ct:
                        yield_func({
                            "status": "info", "role": "📋 章型",
                            "message": f"{'/'.join(ct)} | 裁决: {genre_info.get('conflict_verdict','')[:40]}"
                        })

                elif node.type == "worker":
                    # Worker: 语言规则 + 疲劳词 + 叙事指导 + 爽点
                    if inkos:
                        rules = inkos.get("languageRules", [])
                        sat = inkos.get("satisfactionTypes", [])
                        guidance = inkos.get("narrativeGuidance", "")
                        if rules:
                            system_prompt += "\n\n【语言铁律】\n" + "\n".join(f"- {r}" for r in rules[:3])
                        if guidance:
                            system_prompt += f"\n\n【叙事指导】\n{guidance[:300]}"
                    yield_func({
                        "status": "info", "role": "📖 体裁",
                        "message": f"{genre_info['name']} | {'/'.join(ct[:3]) if ct else ''}"
                    })
                    if fw:
                        yield_func({
                            "status": "info", "role": "InkOS",
                            "message": f"禁词: {'/'.join(fw)} | 爽点: {'/'.join((inkos or {}).get('satisfactionTypes',[])[:3])}"
                        })

                elif node.type == "reviewer":
                    # Reviewer: 审计维度 + 禁忌 + 追读力
                    dims = (inkos or {}).get("auditDimensions", []) if inkos else []
                    taboos = (inkos or {}).get("taboos", []) if inkos else genre_info.get("anti_patterns", [])
                    if taboos:
                        system_prompt += "\n\n【体裁禁忌】\n" + "\n".join(f"- {t}" for t in taboos[:4])
                    yield_func({
                        "status": "info", "role": "📖 体裁",
                        "message": f"{genre_info['name']} | 节奏: {rp[:25]}"
                    })
                    if dims:
                        yield_func({
                            "status": "info", "role": "🔍 审计",
                            "message": f"InkOS {len(dims)}维度 | Hard-001~004 | 禁忌: {'/'.join(taboos[:2]) if taboos else ''}"
                        })

        preset_name = node.config.get("preset_name", "") or "默认"
        node_config = self._get_config(node)
        model_name = node_config.model if node_config else ""
        yield_func({
            "status": "info",
            "role": f"{icon} {role_name}",
            "node_id": nid,
            "message": f"激活: {role_name}",
            "preset": preset_name,
            "model": model_name,
        })

        # 构建用户提示词（包含上游输出）
        user_prompt_parts = []

        # === 多轮进度上下文（Manager 后续轮次 + resume 首轮）===
        if node.type == "manager" and (round_num > 1 or (round_num == 1 and self.outputs)):
            ctx_parts = [f"【📌 第 {round_num} 轮迭代】"]

            ctx_parts.append(f"【原始用户任务】\n{self.task}")

            files = round_context.get("files", [])
            if files:
                file_lines = []
                basenames = {}
                file_limit = self.mode_cfg.get("manager_truncate_files", 30)
                for f in (files[-file_limit:] if file_limit > 0 else files):
                    try:
                        fpath = get_safe_path(f)
                        size = os.path.getsize(fpath) if os.path.exists(fpath) else 0
                        kb = f"{size/1024:.1f}KB" if size >= 1024 else f"{size}B"
                    except:
                        kb = "?"
                    bn = os.path.basename(f)
                    basenames.setdefault(bn, []).append(f)
                    file_lines.append(f"  📄 {f} ({kb})")
                dup_note = ""
                dup_files = {k: v for k, v in basenames.items() if len(v) > 1}
                if dup_files:
                    dup_names = ", ".join(dup_files.keys())
                    dup_note = f"\n⚠️ 检测到重复文件名: {dup_names}，用 [DELETE: 文件名] 删除冗余版本"
                file_list = "\n".join(file_lines)
                ctx_parts.append(f"【当前已生成的文件（共 {len(files)} 个）】\n{file_list}{dup_note}")
            else:
                ctx_parts.append("【当前还没有生成任何文件】")

            if nid in self.outputs:
                prev = self.outputs[nid]
                prev_limit = self.mode_cfg.get("manager_prev_output", 500)
                prev_tail = prev[-prev_limit:] if len(prev) > prev_limit else prev
                ctx_parts.append(f"【你上一轮的输出】\n{prev_tail}")

            # === 直接展示各 Worker 产出（Manager 直接看工人做了什么）===
            worker_views = []
            for out_nid, out_text in self.outputs.items():
                out_node = self.nodes.get(out_nid)
                if out_node and out_node.type == "worker" and out_text:
                    role = self.node_roles.get(out_nid, "执行者")
                    # 首部：看开头在做什么
                    head = out_text[:200].replace("\n", " ").strip()
                    # 尾部：找最后一个完整段落
                    tail = out_text[-600:]
                    paras = tail.split("\n\n")
                    tail = paras[-1].strip() if len(paras) >= 2 else tail.strip()
                    for marker in ["---FILE:", "---ENDFILE---", "```"]:
                        tail = tail.split(marker)[-1]
                    tail = tail.strip()[-300:]
                    # 列出该 Worker 产出的文件
                    w_files = [f for f in self.saved_files if f.startswith(f"worker_{out_nid}")]
                    file_str = ", ".join([f.split("/")[-1].split("\\")[-1] for f in w_files[:10]])
                    if len(w_files) > 10:
                        file_str += f" ... 共{len(w_files)}个"
                    worker_views.append(
                        f"### {role}({out_nid})\n"
                        f"文件: {file_str or '无'}\n"
                        f"开头: {head}...\n"
                        f"结尾: ...{tail}"
                    )
            if worker_views:
                ctx_parts.append(
                    "【各 Worker 上一轮产出概览】\n\n"
                    + "\n\n".join(worker_views) +
                    "\n\n🔴 给后续 Worker 下指令时，直接引用前面 Worker 的文件路径，"
                    "例如：「请参考 worker_n2/chapter17.txt 的结尾，从那里接着写第18章。」"
                    "系统会自动把引用文件的内容加载给该 Worker，无需你手动复制粘贴。"
                )

            if phase_inputs:
                ctx_parts.append("【本轮需要你审阅的反馈/产出】")
            else:
                ctx_parts.append("【本轮任务】继续推进上述未完成的工作。")

            # 小说模式：注入进度追踪 + 监工退出规则
            novel_ctx = getattr(self, '_novel_stage', '')
            # 守卫强制继续消息（跨轮持久）
            guard_msg = getattr(self, '_guard_override', '')
            if guard_msg:
                ctx_parts.insert(0, guard_msg)
                self._guard_override = ''  # 只显示一次，避免干扰后续轮次
            if novel_ctx:
                ch_nums = _count_chapters(self.saved_files)
                done = len(ch_nums)
                # 从用户任务中提取目标章数（如 "500章小说" → 500）
                task_text = (self.task or "") + " " + " ".join(o[-500:] if len(o) > 500 else o for o in self.outputs.values() if o)
                ch_match = re.search(r'(\d+)\s*[章章]|(\d+)\s*chapters?', task_text)
                target = int(ch_match.group(1)) if ch_match else 0
                batch_size = 1
                sorted_nums = sorted(ch_nums) if ch_nums else []
                gap_info = ""
                if sorted_nums and len(sorted_nums) < target:
                    gaps = []
                    for i in range(1, sorted_nums[-1] + 1):
                        if i not in ch_nums:
                            gaps.append(i)
                    if gaps:
                        gap_info = f"，缺失: {gaps[:10]}{'...' if len(gaps) > 10 else ''}"

                is_enhanced = self.execution_mode in ("compatible", "full")
                if is_enhanced:
                    if novel_ctx == "outline":
                        if target > 0:
                            ctx_parts.insert(0, f"【📊 任务参数】用户要求总章数: {target}。请据此安排大纲。")
                        else:
                            ctx_parts.insert(0, "【📊 任务参数】请根据故事内容自行判断合适的大纲长度。")
                    elif novel_ctx == "writing":
                        next_start = max(sorted_nums) + 1 if sorted_nums else 1
                        if target > 0:
                            if done > 0:
                                ctx_parts.insert(0, (
                                    f"【📊 进度追踪】目标: {target} 章 | 已完成: {done} 章\n"
                                    f"下一章: 第{next_start}章。一次只写一章，保证质量。\n"
                                    f"审查通过且未到 {target} 章 → 继续下一章。到达 {target} 章 → [EXIT_LOOP]。"
                                ))
                            else:
                                ctx_parts.insert(0, (
                                    f"【📊 进度追踪】目标: {target} 章 | 已产出: 0 章\n"
                                    f"从第1章开始，一次只写一章，保证每章质量。审查通过后继续下一章。"
                                ))
                        else:
                            ctx_parts.insert(0, (
                                f"【📊 进度追踪】已产出: {done} 章。请自行判断故事何时完成。完成后输出 [EXIT_LOOP]。"
                            ))
                    elif novel_ctx == "polish":
                        if target > 0:
                            ctx_parts.insert(0, f"【📊 审校阶段】全部 {target} 章已产出。检查矛盾、伏笔、文风一致性。")
                        else:
                            ctx_parts.insert(0, f"【📊 审校阶段】全部 {done} 章已产出。检查矛盾、伏笔、文风一致性。")
                else:
                    if target > 0:
                        ctx_parts.insert(0, f"【📊 进度追踪】目标: {target} 章 | 已产出: {done} 章{gap_info}。不到 {target} 章绝不下班。")
                    else:
                        ctx_parts.insert(0, f"【📊 进度追踪】已产出: {done} 章。请自行判断何时完成。")
                    if done > 0 and target > 0:
                        ctx_parts.append(f"🔴 监工规则：审查通过但未达 {target} 章 → 继续派下一批。审查不通过 → 指令修改。全部 {target} 章达标 → [EXIT_LOOP]。")
                    elif done > 0:
                        ctx_parts.append("🔴 监工规则：审查通过且故事自然结束 → 输出 [EXIT_LOOP]。审查不通过 → 指令修改。")
            else:
                ctx_parts.append("⚠️ 判断规则：审查和测试都通过 → [EXIT_LOOP]；审查说通过但测试失败 → 以测试为准，指令修复；文件已满足需求 → [EXIT_LOOP]。")

            user_prompt_parts.append("\n\n".join(ctx_parts))

        # === 上游输入（按节点类型智能路由，防止上下文污染）===
        if phase_inputs:
            for inp in phase_inputs:
                from_id = inp.get("from_id", "")
                from_node = self.nodes.get(from_id)
                from_type = from_node.type if from_node else ""
                output = inp.get("output", "")
                from_name = inp.get("from_name", "")
                annotation = inp.get("annotation", "")

                if node.type == "worker":
                    if from_type == "reviewer":
                        # 修订模式：审查者要求修改 → 加载被修改的原文 + 审查意见
                        novel_ctx_stage = getattr(self, '_novel_stage', '')
                        if novel_ctx_stage:
                            # 找到最新章文件 → 这就是需要修改的章
                            ch_nums_map = _count_chapters(self.saved_files)
                            if not ch_nums_map and self.saved_files:
                                # 无章节号但有文件 → 列出文件供 Worker 参考
                                user_prompt_parts.insert(0,
                                    f"【修订任务 — 请根据审查意见修改相关文件】\n"
                                    f"当前文件: {', '.join(os.path.basename(f) for f in self.saved_files[:20])}")
                            if ch_nums_map:
                                latest_ch = max(ch_nums_map)
                                # 在 saved_files 中找到该章文件路径
                                target_file = None
                                for sf in self.saved_files:
                                    bn = os.path.basename(sf)
                                    m = re.match(r'第(\d+)章', bn)
                                    if m and int(m.group(1)) == latest_ch:
                                        target_file = sf
                                        break
                                if target_file:
                                    full_path = os.path.join(WORKSPACE_DIR, target_file) if not target_file.startswith(WORKSPACE_DIR) else target_file
                                    if os.path.isfile(full_path):
                                        try:
                                            with open(full_path, "r", encoding="utf-8", errors="replace") as ref_f:
                                                ch_content = ref_f.read()
                                            user_prompt_parts.insert(0,
                                                f"【🔴 修订任务 — 修改以下章节，不要写新章节！】\n"
                                                f"待修改文件: {os.path.basename(target_file)}\n\n"
                                                f"--- 原文内容 ---\n{ch_content}\n"
                                                f"--- 原文结束 ---\n\n"
                                                f"下面是审查者的修改意见，请根据意见修改上面的原文，用 ---FILE: {os.path.basename(target_file)}--- 输出修改后的版本。"
                                            )
                                        except Exception:
                                            pass
                        user_prompt_parts.append(f"【审查意见 — 请根据以下反馈修改上面的章节】\n{output}")
                    elif from_type == "manager":
                        clean = output.strip()
                        if clean == "[EXIT_LOOP]" or clean == "[APPROVED_EXIT]" or len(clean) < 20:
                            continue
                        user_prompt_parts.append(f"【任务指令 — 请立即执行并产出文件】\n{output}")
                        # 检测 Manager 指令中引用的其他 Worker 文件，自动加载内容
                        refs = re.findall(r'worker_(n\d+|[\w-]+)/([\w./-]+\.\w+)', output)
                        if refs:
                            ref_parts = []
                            seen = set()
                            for ref_dir, ref_file in refs:
                                ref_path = f"{ref_dir}/{ref_file}"
                                if ref_path in seen:
                                    continue
                                seen.add(ref_path)
                                full_path = os.path.join(WORKSPACE_DIR, ref_path)
                                if os.path.isfile(full_path):
                                    try:
                                        with open(full_path, "r", encoding="utf-8", errors="replace") as ref_f:
                                            ref_content = ref_f.read()[:2000]
                                        ref_parts.append(f"【引用文件: {ref_path}】\n{ref_content}")
                                    except Exception:
                                        ref_parts.append(f"【引用文件: {ref_path}】(无法读取)")
                                else:
                                    # 列出该目录的文件
                                    ref_dir_path = os.path.join(WORKSPACE_DIR, ref_dir)
                                    if os.path.isdir(ref_dir_path):
                                        files = [f for f in os.listdir(ref_dir_path) if os.path.isfile(os.path.join(ref_dir_path, f))]
                                        ref_parts.append(f"【引用目录: {ref_dir}/】文件列表: {', '.join(files[:20])}")
                            if ref_parts:
                                user_prompt_parts.append("【Manager 引用的其他 Worker 文件内容 — 可直接参考续写】\n" + "\n\n".join(ref_parts))
                        # 小说 Worker 上下文注入：大纲 + 前文
                        novel_ctx_stage = getattr(self, '_novel_stage', '')
                        if novel_ctx_stage == "writing":
                            all_known = self.prev_stage_files + self.saved_files
                            outline_path = None
                            chars_path = None
                            for f in all_known:
                                bn = os.path.basename(f)
                                if bn == "outline.md" and not outline_path:
                                    outline_path = os.path.join(WORKSPACE_DIR, f)
                                if bn == "characters.md" and not chars_path:
                                    chars_path = os.path.join(WORKSPACE_DIR, f)
                            if not outline_path and os.path.isfile(os.path.join(WORKSPACE_DIR, "outline.md")):
                                outline_path = os.path.join(WORKSPACE_DIR, "outline.md")
                            if not chars_path and os.path.isfile(os.path.join(WORKSPACE_DIR, "characters.md")):
                                chars_path = os.path.join(WORKSPACE_DIR, "characters.md")
                            if outline_path and os.path.isfile(outline_path):
                                try:
                                    with open(outline_path, "r", encoding="utf-8", errors="replace") as of:
                                        oc = of.read()[:3000]
                                    user_prompt_parts.insert(0, f"【小说大纲 — 必须严格围绕大纲写作，禁止偏离】\n{oc}")
                                except Exception:
                                    pass
                            if chars_path and os.path.isfile(chars_path):
                                try:
                                    with open(chars_path, "r", encoding="utf-8", errors="replace") as cf:
                                        cc = cf.read()[:2000]
                                    user_prompt_parts.append(f"【人物设定 — 禁止擅自新增角色】\n{cc}")
                                except Exception:
                                    pass
                            # 全局记忆（Manager 通过 [MEMORY:] 标签维护，累积式）
                            novel_memory = getattr(self, '_novel_memory', '')
                            if novel_memory:
                                user_prompt_parts.insert(0,
                                    f"【🧠 全局记忆 — 整部小说的角色状态、主线、伏笔】\n"
                                    f"{novel_memory[-4000:] if len(novel_memory) > 4000 else novel_memory}\n\n"
                                    f"请确保新章节与全局记忆一致，角色状态连贯，不遗漏已揭示的伏笔。")
                        # 前文摘要（Manager 通过 [SUMMARY:] 标签维护）
                            novel_summary = getattr(self, '_novel_summary', '')
                            if novel_summary:
                                user_prompt_parts.insert(0,
                                    f"【📋 前文概要 — 之前发生的所有重要事件】\n{novel_summary}\n\n"
                                    f"请确保新章节与前文概要一致，不重复已有情节，自然推进故事发展。")
                            # 找最新/待处理的章节文件（用章节号排序）
                            all_known += [f for f in os.listdir(WORKSPACE_DIR)
                                         if os.path.isfile(os.path.join(WORKSPACE_DIR, f))]
                            _txt_files = set(f for f in all_known if f.endswith('.txt'))
                            _ch_with_nums = []
                            for _f in _txt_files:
                                _bn = os.path.basename(_f)
                                _m = re.match(r'第(\d+)章', _bn)
                                if _m:
                                    _ch_with_nums.append((int(_m.group(1)), _f))
                            _ch_with_nums.sort(key=lambda x: x[0])
                            ch_files = [f for _, f in _ch_with_nums]
                            # 判断当前 Worker 是创作(w_a)还是润色(w_b)
                            is_polish_worker = nid.endswith('b') if nid else False
                            if ch_files:
                                last_path = os.path.join(WORKSPACE_DIR, ch_files[-1]) if not ch_files[-1].startswith(WORKSPACE_DIR) else ch_files[-1]
                                if is_polish_worker:
                                    # 润色作家：加载完整最新章节 + 审查反馈，进行润色
                                    if os.path.isfile(last_path):
                                        try:
                                            with open(last_path, "r", encoding="utf-8", errors="replace") as lf:
                                                full_ch = lf.read()
                                            ch_name = os.path.basename(last_path)
                                            user_prompt_parts.insert(0, (
                                                f"【🔴 润色任务 — 请润色以下章节，不要写新章节！】\n"
                                                f"待润色文件: {ch_name}\n\n"
                                                f"--- 原文内容 ---\n{full_ch}\n"
                                                f"--- 原文结束 ---\n\n"
                                                f"请根据审查意见修改润色此章节，用 ---FILE: {ch_name}--- 格式输出版本。"
                                            ))
                                        except Exception:
                                            pass
                                else:
                                    # 创作作家：注入最近几章的结尾，保证长篇连贯性
                                    recent_n = min(5, len(ch_files))
                                    recent_files = ch_files[-recent_n:] if recent_n > 0 else []
                                    # 最近3章的结尾（用于衔接）
                                    context_parts = []
                                    for rf in recent_files[-3:]:
                                        rf_path = os.path.join(WORKSPACE_DIR, rf) if not rf.startswith(WORKSPACE_DIR) else rf
                                        if os.path.isfile(rf_path):
                                            try:
                                                with open(rf_path, "r", encoding="utf-8", errors="replace") as rf_f:
                                                    rfc = rf_f.read()
                                                context_parts.append(
                                                    f"【{os.path.basename(rf)} 结尾】...{rfc[-300:]}")
                                            except Exception:
                                                pass
                                    # 章节列表概览
                                    ch_list = [os.path.basename(f).replace('.txt', '') for f in recent_files]
                                    ch_overview = f"【已完成章节】{', '.join(ch_list)}" if ch_list else ""
                                    if ch_overview:
                                        user_prompt_parts.append(ch_overview)
                                    if context_parts:
                                        user_prompt_parts.append("【最近章节结尾 — 必须自然衔接】\n" + "\n".join(context_parts))
                        elif novel_ctx_stage == "polish":
                            all_known = self.prev_stage_files + self.saved_files
                            ch_files = [f for f in all_known
                                       if (os.path.basename(f).startswith("第") or os.path.basename(f).startswith("chapter"))
                                       and f.endswith(".txt")]
                            if ch_files:
                                user_prompt_parts.append(
                                    f"【已有{len(ch_files)}章 — 检查前后矛盾和衔接】\n"
                                    f"文件: {', '.join(os.path.basename(f) for f in ch_files[:20])}"
                                )

                elif node.type == "reviewer":
                    if from_type == "worker":
                        worker_subfolder = f"worker_{from_id}"
                        file_hint = ""
                        novel_stage = getattr(self, '_novel_stage', '')
                        if novel_stage:
                            # 小说模式：纯文学审查，展示所有文件，不提示测试
                            task_files = list(self.saved_files)
                            if task_files:
                                clean_names = [os.path.basename(f) for f in task_files]
                                txt_files = [f for f in clean_names if f.endswith(('.txt', '.md'))]
                                file_hint += f"\n📝 写作产出: {len(txt_files)} 个文件"
                                file_hint += f"\n📄 {', '.join(clean_names[:20])}"
                                file_hint += f"\n💡 直接阅读以上文件内容判断文学质量，不使用任何测试指令"
                            output_display = output  # 完整展示，让审查者能读到全部内容
                            test_reminder = "\n\n⚠️ 你只需阅读文本给出文学审查结论。禁止 [TEST:CMD:] 或任何测试指令。"
                        else:
                            # 代码模式：按文件类型提示测试命令
                            task_files = [f for f in self.saved_files if f.startswith(worker_subfolder + "/") or f.startswith(worker_subfolder + "\\")]
                            if task_files:
                                clean_names = [f[len(worker_subfolder)+1:].replace("\\", "/") for f in task_files]
                                py_files = [f for f in clean_names if f.endswith('.py')]
                                cpp_files = [f for f in clean_names if f.endswith(('.cpp', '.c', '.h'))]
                                js_files = [f for f in clean_names if f.endswith(('.js', '.ts', '.jsx', '.tsx'))]
                                html_files = [f for f in clean_names if f.endswith(('.html', '.htm'))]
                                txt_files = [f for f in clean_names if f.endswith(('.txt', '.md'))]
                                is_web = bool(html_files) or (bool(js_files) and not bool(py_files) and not bool(cpp_files))
                                is_writing = bool(txt_files) and not bool(py_files) and not bool(cpp_files) and not bool(js_files)
                                if py_files:
                                    file_hint += f"\n📁 Python 文件: {', '.join(py_files[:10])}"
                                    file_hint += f"\n💡 测试: [TEST:CMD: python {worker_subfolder}/{py_files[0]}]"
                                elif cpp_files:
                                    file_hint += f"\n📁 C++ 文件: {', '.join(cpp_files[:10])}"
                                    file_hint += f"\n💡 编译测试: [TEST:CMD: g++ -std=c++17 {worker_subfolder}/*.cpp -o {worker_subfolder}/a.out]"
                                elif is_web:
                                    file_hint += f"\n🌐 Web 项目: {', '.join(clean_names[:10])}"
                                    file_hint += f"\n💡 测试: [TEST:CMD: dir {worker_subfolder}\\ /b] 确认文件存在"
                                elif is_writing:
                                    file_hint += f"\n📝 写作产出: {len(txt_files)} 个文本文件"
                                    file_hint += f"\n💡 测试: [TEST:CMD: dir {worker_subfolder}\\*.txt /b | find /c /v \"\"] (统计文件数)"
                                elif js_files:
                                    file_hint += f"\n📁 Node.js 文件: {', '.join(js_files[:10])}"
                                    file_hint += f"\n💡 测试: [TEST:CMD: node {worker_subfolder}/{js_files[0]}]"
                                else:
                                    file_hint += f"\n📁 文件列表: {', '.join(clean_names[:15])}"
                                if len(clean_names) > 15:
                                    file_hint += f"\n   ... 还有 {len(clean_names) - 15} 个文件"
                            if self.mode_cfg.get("reviewer_truncate", True):
                                output_preview = output[:400]
                                output_tail = output[-200:] if len(output) > 600 else ""
                                output_display = f"{output_preview}\n\n... [输出过长已截断，请用测试指令验证] ...\n\n{output_tail}"
                                test_reminder = "\n\n🔴 你必须在结论前先输出测试指令（如 [TEST:CMD: python worker_n2/文件名.py]）实际运行验证代码。注意路径从 worker_n2/ 开始，不要加 workspace/ 前缀。"
                            else:
                                output_display = output
                                test_reminder = "\n\n🔴 铁律：不测试 = 严重失职！先输出 [TEST:CMD:] 或 [TEST:CODE:python:] 指令实际运行代码，然后基于测试结果给结论。"
                        user_prompt_parts.append(
                            f"【待审查内容 — 文件保存在 workspace/{worker_subfolder}/ 目录】{file_hint}\n{output_display}{test_reminder}"
                        )

                elif node.type == "manager":
                    if from_type == "reviewer":
                        if "通过" in output or "✅" in output:
                            test_failed = "❌ 失败" in output or "ModuleNotFoundError" in output.lower() or "Traceback" in output.lower()
                            if test_failed:
                                user_prompt_parts.append(
                                    f'【审查反馈 - 审查说通过但测试实际失败了】\n{output}\n\n'
                                    '测试失败优先于审查结论！你必须指令执行者修复问题（缺少依赖就安装、代码报错就修改），'
                                    '修复后重新测试。只有测试真正通过后才能输出 [EXIT_LOOP]。'
                                )
                            else:
                                user_prompt_parts.append(
                                    f'【审查反馈 - 审查已通过】\n{output}\n\n'
                                    '审查通过且测试通过，立即输出 [EXIT_LOOP] 结束任务。'
                                )
                        else:
                            user_prompt_parts.append(f'【审查反馈 - 需要修改】\n{output}\n\n请指示执行者修改关键问题。修改后审查和测试都通过就 [EXIT_LOOP]。')
                    elif from_type == "worker":
                        worker_subfolder = f"worker_{from_id}"
                        w_preview = output[:300].replace("\n", " ")
                        if len(output) > 300:
                            w_preview += "..."
                        user_prompt_parts.append(f"【执行者产出 — 文件保存在 workspace/{worker_subfolder}/ 目录】{w_preview}")
                else:
                    # 其他类型：保留末尾
                    if len(output) > 2000:
                        output = output[-2000:]
                    user_prompt_parts.append(f"【来自「{from_name}」的消息】\n{output}")

        # 每轮注入对话记忆 + 用户任务（Manager 需要知道用户说了什么）
        if self.conversation_history and node.type == "manager":
            hist_count = self.mode_cfg.get("history_count", 5)
            hist_chars = self.mode_cfg.get("history_chars", 200)
            history_parts = []
            for msg in self.conversation_history[-hist_count:]:
                role_label = "用户" if msg.get("role") == "user" else "助手"
                content = msg.get("content", "")
                if len(content) > hist_chars:
                    content = content[:hist_chars] + "..."
                history_parts.append(f"[{role_label}]: {content}")
            if history_parts:
                user_prompt_parts.append(
                    f"【对话记忆 — 用户之前的消息，请据此调整工作】\n" + "\n".join(history_parts))
        if node.type == "manager":
            user_prompt_parts.append(f"【用户任务】\n{self.task}")

        # === 用户中途反馈注入（Manager 专属） ===
        if node.type == "manager":
            fb = round_context.get("user_feedback", []) if round_context else []
            if fb:
                file_list = "\n".join(f"  📄 {f}" for f in (self.saved_files[-30:] if self.saved_files else ["(暂无文件)"]))
                fb_text = "\n---\n".join(f"💬 {f}" for f in fb)
                user_prompt_parts.append(
                    f"【⚠️ 用户中途反馈 — 请仔细阅读并据此调整计划】\n\n"
                    f"用户在查看已生成的内容后，提出了以下反馈：\n\n"
                    f"{fb_text}\n\n"
                    f"📋 当前已生成的文件列表：\n{file_list}\n\n"
                    f"🔧 你可以做的：\n"
                    f"1. 如果反馈要求修改已有内容 → 用 [ROLE: wX = 角色] 指派 Worker 重写特定文件\n"
                    f"2. 如果反馈要求调整方向 → 在后续章节中按新方向写作\n"
                    f"3. 如果反馈要求删除/替换 → 用 [DELETE: 文件名] 删除旧文件，再指派 Worker 重写\n\n"
                    f"请明确回应反馈，然后重新安排工作。"
                )
                # 本轮已注入，清空待处理（同一轮内 Manager 只处理一次）
                self.pending_feedback.clear()

        # 添加上下文：告知节点它的下游连接 + 可用角色库（仅首轮 Manager）
        if round_num == 1:
            downstream = self.outgoing.get(nid, [])
            if downstream and node.type == "manager":
                targets = []
                for conn in downstream:
                    tid = conn.to_node
                    target_node = self.nodes.get(tid)
                    if target_node:
                        type_desc = {"worker": "执行者（产出文件）", "reviewer": "审查者（只审阅，不产出文件）"}
                        desc = type_desc.get(target_node.type, target_node.type)
                        targets.append(f"- {tid} = {desc}  连线: {conn.annotation or '无'}")
                if targets:
                    user_prompt_parts.append(
                        f"【你的下游节点 — 注意每个节点的能力边界】\n" + "\n".join(targets) +
                        "\n\n⚠️ 只有 worker 类型能产出文件。reviewer 只能审阅，不能创建内容。"
                        "\n使用格式指派角色: [ROLE: 节点ID = 角色名]"
                    )
                # 角色库注入：紧凑模式（标准/兼容）vs 完整模式（满血）
                if ROLE_CATALOG:
                    if self.mode_cfg.get("role_catalog") == "full":
                        catalog_lines = ROLE_CATALOG.split('\n')
                        catalog_display = '\n'.join(catalog_lines[:27])
                        if len(catalog_lines) > 27:
                            catalog_display += f"\n... 还有 {len(catalog_lines) - 27} 个角色"
                    else:
                        catalog_display = "通用助手, 代码审查员, 测试工程师, 前端开发者, 后端架构师, 创意作家, 数据工程师, 安全工程师, 运维工程师, UI设计师\n（用角色名直接指派，如 [ROLE: w1 = 前端开发者]）"
                    user_prompt_parts.append(
                        f"【可用角色库】\n{catalog_display}\n\n"
                        "用 [ROLE: 节点ID = 角色名] 为下游指派角色。例如: [ROLE: w1 = 创意作家]"
                    )

        user_prompt = "\n\n".join(user_prompt_parts)

        # 调用 LLM
        config = node_config
        yield_func({
            "status": "working",
            "role": f"{icon} {role_name}",
            "node_id": nid,
            "message": "工作中..."
        })

        mode_max_tokens = self.mode_cfg["max_tokens"].get(node.type, DEFAULT_MAX_TOKENS)
        mode_timeout = self.mode_cfg["timeout"]

        # 检查是否已被用户取消
        if self.cancelled:
            return "[CANCELLED]"

        # 记录当前任务，让 /api/stop-task 可以取消正在进行的 LLM 调用
        self._current_llm_task = asyncio.current_task()
        try:
            result = await call_llm(
                config,
                system_prompt,
                user_prompt,
                mode_max_tokens,
                mode_timeout,
            )
        except asyncio.CancelledError:
            return "[CANCELLED]"
        finally:
            self._current_llm_task = None

        if is_llm_error(result):
            yield_func({
                "status": "error",
                "role": f"{icon} {role_name}",
                "node_id": nid,
                "message": f"执行失败: {result}"
            })
            return f"[ERROR] {result}"

        # 保存原始输出（用于检测 Reviewer 预判）
        original_result = result

        # === 解析并执行测试指令（小说模式跳过） ===
        novel_stage_test = getattr(self, '_novel_stage', '')
        test_instructions = []
        test_results_text = []
        if not novel_stage_test:
            test_instructions = parse_test_instructions(result)
        if test_instructions and not novel_stage_test:
            for instr in test_instructions:
                yield_func({
                    "status": "info",
                    "role": f"{icon} {role_name}",
                    "node_id": nid,
                    "message": f"🧪 执行测试: {instr[:80]}"
                })
                try:
                    # CMD 测试：实时流式输出到终端和 SSE
                    is_cmd = bool(re.match(r'\[TEST:CMD:\s*(.+)\]$', instr, re.IGNORECASE))
                    if is_cmd:
                        cmd = re.match(r'\[TEST:CMD:\s*(.+)\]$', instr, re.IGNORECASE).group(1).strip()
                        if is_dangerous(cmd):
                            yield_func({
                                "status": "warning",
                                "role": f"{icon} {role_name}",
                                "node_id": nid,
                                "message": f"⚠️ 危险命令需确认: {instr[:80]}",
                                "test_confirm": True,
                                "test_instruction": instr,
                            })
                            test_results_text.append(f"【测试结果】\n类型: CMD\n结果: ⚠️ 危险命令需用户确认\n命令: {cmd}")
                            continue
                        # 流式执行 + 广播到终端
                        start_time = time.monotonic()
                        output_lines = []
                        exit_code = None
                        await TerminalManager.broadcast({
                            "type": "prompt", "data": f"$ [Agent] {cmd}", "elapsed": 0
                        })
                        async for chunk in terminal_executor_stream(cmd, WORKSPACE_DIR):
                            await TerminalManager.broadcast(chunk)
                            if chunk["type"] in ("stdout", "error"):
                                output_lines.append(chunk.get("data", ""))
                            if chunk["type"] == "done":
                                exit_code = chunk.get("exit_code", -1)
                                elapsed = chunk.get("elapsed", 0)
                        output_text = "\n".join(output_lines)
                        is_success = exit_code == 0

                        # 检测环境缺失，弹出确认询问用户
                        dep_module = None
                        if not is_success and "ModuleNotFoundError" in output_text:
                            import re as _re2
                            mod_match = _re2.search(r"No module named '(\w+)'", output_text)
                            if mod_match:
                                dep_module = mod_match.group(1)
                        # 也检测其他常见环境缺失
                        if not is_success and not dep_module:
                            if "command not found" in output_text.lower() or "not recognized" in output_text.lower():
                                dep_module = "__cmd__"

                        test_results_text.append(
                            f"【测试结果】\n类型: CMD (实时)\n退出码: {exit_code}\n"
                            f"结果: {'✅ 成功' if is_success else '❌ 失败'}\n"
                            f"输出:\n{output_text[:2000]}\n耗时: {elapsed:.1f}s"
                        )
                        if dep_module:
                            test_results_text.append(
                                f"💡 环境缺失: {dep_module}。可在终端执行 pip install {dep_module} 或点击前端弹窗安装。"
                            )
                            yield_func({
                                "status": "warning",
                                "role": f"{icon} {role_name}",
                                "node_id": nid,
                                "message": f"📦 检测到缺失依赖: {dep_module}",
                                "dep_missing": dep_module,
                                "dep_suggestion": f"pip install {dep_module}" if dep_module != "__cmd__" else "check command path",
                                "test_instruction": instr,
                            })

                        yield_func({
                            "status": "success" if is_success else "warning",
                            "role": f"{icon} {role_name}",
                            "node_id": nid,
                            "message": f"{'✅' if is_success else '❌'} 测试完成: CMD ({elapsed:.1f}s)",
                            "test_output": output_text[:500],
                            "test_error": "",
                            "test_exit_code": exit_code,
                        })
                    else:
                        # 非 CMD 测试（CODE/API/PW）：使用同步执行
                        test_result = await execute_test(instr, WORKSPACE_DIR)
                        if test_result.needs_confirm:
                            yield_func({
                                "status": "warning",
                                "role": f"{icon} {role_name}",
                                "node_id": nid,
                                "message": f"⚠️ 危险命令需确认: {instr[:80]}",
                                "test_confirm": True,
                                "test_instruction": instr,
                            })
                        test_text = test_result.to_text()
                        test_results_text.append(test_text)
                        yield_func({
                            "status": "success" if test_result.success else "warning",
                            "role": f"{icon} {role_name}",
                            "node_id": nid,
                            "message": f"{'✅' if test_result.success else '❌'} 测试完成: {test_result.test_type} ({test_result.duration:.1f}s)",
                            "test_output": test_result.output[:500] if test_result.output else "",
                            "test_error": test_result.error[:500] if test_result.error else "",
                            "test_exit_code": test_result.exit_code,
                        })
                        # 非 CMD 测试结果也广播到终端
                        if test_result.output:
                            await TerminalManager.broadcast({
                                "type": "stdout", "data": test_result.output[:1000], "elapsed": test_result.duration
                            })
                except Exception as te:
                    err_text = f"测试执行异常: {str(te)}"
                    test_results_text.append(f"【测试结果】\n类型: 异常\n结果: ❌ 失败\n错误: {err_text}")
                    yield_func({
                        "status": "warning",
                        "role": f"{icon} {role_name}",
                        "node_id": nid,
                        "message": f"❌ 测试异常: {str(te)[:100]}"
                    })
            if test_results_text:
                result += "\n\n" + "\n\n".join(test_results_text)

        # === Reviewer 测试强制验证（小说模式跳过） ===
        if node.type == "reviewer" and not novel_stage_test:
            has_approval = "通过" in result or "✅" in result
            has_test = bool(test_instructions)
            has_code_worker = any(
                conn.from_node in self.outputs
                for conn in self.connections
                if conn.to_node == nid and self.nodes.get(conn.from_node) and self.nodes[conn.from_node].type == "worker"
            )
            # 检查是否在测试指令的同时给出结论（预判，不等测试结果）
            original_has_approval = "通过" in original_result or "✅" in original_result if test_instructions else False
            premature = has_test and original_has_approval and has_code_worker

            if has_approval and not has_test and has_code_worker:
                # 情况1：完全没有测试指令就批准
                enforcement_msg = (
                    '\n\n【⚠️ 系统拦截：审查者未执行测试即给出"通过"。'
                    '必须先用 [TEST:CMD:] 或 [TEST:CODE:python:] 实际运行代码后再给结论。'
                    '请重新审查，先测试再判断。】'
                )
                result += enforcement_msg
                yield_func({
                    "status": "warning",
                    "role": f"{icon} {role_name}",
                    "node_id": nid,
                    "message": "⚠️ 审查者未执行测试就通过，已注入重审指令"
                })
            elif premature:
                # 情况2：有测试指令但在同一条消息里预判了结论
                enforcement_msg = (
                    '\n\n【⚠️ 系统拦截：审查者在测试执行前就给出了"通过"/"✅"结论。'
                    '不要在输出测试指令的同时预判结果！正确做法：先输出 [TEST:CMD:] 指令等待系统执行，'
                    '在下一条消息中根据实际测试结果给出结论。请重新审查。】'
                )
                result += enforcement_msg
                yield_func({
                    "status": "warning",
                    "role": f"{icon} {role_name}",
                    "node_id": nid,
                    "message": "⚠️ 审查者预判测试结果（在指令中同时给结论），已注入重审指令"
                })

        # 提取并保存文件
        run_prefix = (self.run_subfolder + "/") if self.run_subfolder else ""
        novel_stage_save = getattr(self, '_novel_stage', '')
        if novel_stage_save:
            # 小说模式：只有 Worker 可以产出文件
            if node.type == "worker":
                saved = extract_and_save_files(result, run_prefix)
                self.saved_files.extend(saved)
            else:
                saved = []
        elif node.type != "reviewer":
            # 代码模式：Manager 和 Worker 都可以产出文件
            subfolder = f"{run_prefix}{node.type}_{nid}"
            saved = extract_and_save_files(result, subfolder)
            self.saved_files.extend(saved)
        else:
            saved = []

        if saved:
            yield_func({
                "status": "success",
                "role": f"{icon} {role_name}",
                "node_id": nid,
                "message": f"完成: {', '.join(saved)}"
            })
        else:
            # 没有文件产出，显示输出摘要
            # Manager/Reviewer 输出通常是简短的指令/审查结论，不应截断
            max_preview = 2000 if node.type in ("manager", "reviewer") else 500
            preview = result[:max_preview].replace("\n", " ")
            if len(result) > max_preview:
                preview += "..."
            status = "warning" if node.type == "worker" else "success"
            yield_func({
                "status": status,
                "role": f"{icon} {role_name}",
                "node_id": nid,
                "message": f"{'⚠️ 未产出文件: ' if node.type == 'worker' else ''}{preview}"
            })

        return result

    def _find_back_edges(self) -> List:
        """找出所有回边：从后阶段连回前阶段的连线，形成循环"""
        back_edges = []
        for conn in self.connections:
            fid = conn.from_node
            tid = conn.to_node
            if fid not in self.nodes or tid not in self.nodes:
                continue
            # 检查 tid 是否有路径到达 fid（通过 outgoing 连接）
            visited = set()
            def can_reach(start, target, depth=0):
                if depth > 20 or start in visited:
                    return False
                visited.add(start)
                if start == target:
                    return True
                for c in self.outgoing.get(start, []):
                    if can_reach(c.to_node, target, depth + 1):
                        return True
                return False
            if can_reach(tid, fid):
                back_edges.append(conn)
        return back_edges

    def _find_managers(self) -> List[str]:
        """找到所有 Manager 节点"""
        return [nid for nid, node in self.nodes.items() if node.type == "manager"]

    def _reviewer_approved(self) -> bool:
        """检查所有 Reviewer 是否通过。小说模式只看文本结论；代码模式还要排除测试失败。"""
        novel_stage = getattr(self, '_novel_stage', '')
        for nid, node in self.nodes.items():
            if node.type == "reviewer" and nid in self.outputs:
                output = self.outputs[nid]
                has_approval = "通过" in output or "✅" in output
                if not has_approval:
                    continue
                if novel_stage:
                    return True  # 小说模式：审查说通过就通过
                # 代码模式：检查测试结果是否与审查结论矛盾
                test_failed = ("exit code: 1" in output.lower() or
                              "exit code: 2" in output.lower() or
                              "❌ 失败" in output or
                              "traceback" in output.lower() or
                              "referenceerror" in output.lower() or
                              "modulenotfounderror" in output.lower() or
                              "syntaxerror" in output.lower() or
                              "eoferror" in output.lower())
                if test_failed:
                    continue
                return True
        return False

    def _manager_says_done(self, manager_output: str) -> bool:
        """Manager 决定任务完成时输出标记。
        检查最后 500 字符，标记必须独占一行。"""
        scan_len = 500
        tail = manager_output[-scan_len:] if len(manager_output) > scan_len else manager_output
        for line in tail.split('\n'):
            if line.strip() in ('[EXIT_LOOP]', '[APPROVED_EXIT]', '>>>APPROVED<<<'):
                if len(self.saved_files) > 0:
                    return True
        return False

    def _parse_role_assignments(self) -> int:
        """扫描所有节点输出中的 [ROLE: node_id = 角色名] 标记，动态更新节点配置。
        返回成功指派的角色数。"""
        role_pattern = re.compile(r'\[ROLE:\s*(\S+)\s*=\s*(.+?)\]')
        assigned = 0
        for nid, output in self.outputs.items():
            for m in role_pattern.finditer(output):
                target_nid = m.group(1).strip()
                role_name = m.group(2).strip()
                if target_nid in self.nodes:
                    agent = get_agent_by_name(ALL_AGENTS, role_name)
                    if agent:
                        self.nodes[target_nid].config["agent_role"] = role_name
                        assigned += 1
        return assigned

    def _parse_skill_assignments(self) -> int:
        """扫描所有输出中的 [SKILL: 名称] 和 [UNSKILL: 名称] 标记。
        返回本轮新增/移除的 Skill 数量变化。"""
        skill_pattern = re.compile(r'\[SKILL:\s*(.+?)\]')
        unskill_pattern = re.compile(r'\[UNSKILL:\s*(.+?)\]')
        changed = 0
        for nid, output in self.outputs.items():
            for m in skill_pattern.finditer(output):
                sname = m.group(1).strip()
                if sname and sname not in self.active_skills:
                    self.active_skills.append(sname)
                    changed += 1
            for m in unskill_pattern.finditer(output):
                sname = m.group(1).strip()
                if sname and sname in self.active_skills:
                    self.active_skills.remove(sname)
                    changed -= 1
        return changed

    def _parse_file_operations(self) -> dict:
        """扫描 Manager 输出中的文件操作指令。支持: [DELETE: 文件名]"""
        delete_pattern = re.compile(r'\[DELETE:\s*(.+?)\]')
        deleted = []
        kept = []
        for nid, output in self.outputs.items():
            for m in delete_pattern.finditer(output):
                fname = m.group(1).strip()
                # 安全校验：拒绝路径穿越
                if ".." in fname or "/" in fname or "\\" in fname:
                    continue
                try:
                    filepath = get_safe_path(fname)
                    if os.path.exists(filepath):
                        os.remove(filepath)
                        deleted.append(fname)
                        if fname in self.saved_files:
                            self.saved_files.remove(fname)
                except Exception:
                    pass
        return {"deleted": deleted, "kept": kept}

    def _parse_summary(self):
        """扫描 Manager 输出中的 [SUMMARY: 摘要内容] 标记，更新前文摘要。"""
        summary_pattern = re.compile(r'\[SUMMARY:\s*(.+?)\]', re.DOTALL)
        for nid, output in self.outputs.items():
            for m in summary_pattern.finditer(output):
                summary_text = m.group(1).strip()
                if summary_text and len(summary_text) > 20:
                    self._novel_summary = summary_text

    def _parse_memory(self):
        """扫描 Manager 输出中的 [MEMORY: 记忆内容] 标记，累积追加到全局记忆。
        同时写入 run_xxx/memory/novel_memory.md 文件。"""
        memory_pattern = re.compile(r'\[MEMORY:\s*(.+?)\]', re.DOTALL)
        appended = False
        for nid, output in self.outputs.items():
            for m in memory_pattern.finditer(output):
                mem_text = m.group(1).strip()
                if mem_text and len(mem_text) > 10:
                    # 追加到内存（用时间戳分隔）
                    ts = time.strftime("%Y-%m-%d %H:%M")
                    entry = f"\n\n--- {ts} (round {getattr(self, '_last_round', '?')}) ---\n{mem_text}"
                    self._novel_memory += entry
                    appended = True
        if appended and self.run_subfolder:
            # 确保 memory/ 目录存在
            mem_dir = os.path.join(WORKSPACE_DIR, self.run_subfolder, "memory")
            os.makedirs(mem_dir, exist_ok=True)
            mem_path = os.path.join(mem_dir, "novel_memory.md")
            with open(mem_path, "w", encoding="utf-8") as f:
                f.write(self._novel_memory)

    def _load_memory_from_disk(self):
        """从 memory/novel_memory.md 加载已有记忆（续跑时用）。"""
        if self._memory_loaded or not self.run_subfolder:
            return
        mem_path = os.path.join(WORKSPACE_DIR, self.run_subfolder, "memory", "novel_memory.md")
        if os.path.isfile(mem_path):
            try:
                with open(mem_path, "r", encoding="utf-8") as f:
                    self._novel_memory = f.read()
            except Exception:
                pass
        self._memory_loaded = True

    STAGE_CONFIG = [
        ("outline", "大纲创作", []),
        ("writing", "分批写作", ["长篇小说创作"]),
        ("polish", "全局审校", ["长篇小说创作"]),
    ]

    def _detect_pipeline_stages(self):
        """检测画布节点是否形成流水线（按 _N 后缀分组）。返回分组结果或 None。
        支持润色变体节点如 w_2a, r_3b（a/b 后缀被剥离以提取阶段号）。"""
        id_to_node = self.nodes
        stage_groups = {}
        for nid in self.nodes:
            parts = nid.rsplit("_", 1)
            if len(parts) == 2:
                suffix_str = parts[1]
                # 剥离润色变体后缀 (a/b)：w_2a → stage 2, r_3b → stage 3
                if len(suffix_str) >= 2 and suffix_str[-1] in ('a', 'b') and suffix_str[:-1].isdigit():
                    suffix = int(suffix_str[:-1])
                elif suffix_str.isdigit():
                    suffix = int(suffix_str)
                else:
                    return None  # 非流水线节点
            else:
                return None  # 非流水线节点
            stage_groups.setdefault(suffix, []).append(nid)

        if len(stage_groups) < 2:
            return None  # 只有1个阶段，不启用

        result = []
        for stage_idx in sorted(stage_groups.keys()):
            ids = set(stage_groups[stage_idx])
            stage_nodes = [self.nodes[nid] for nid in ids]
            stage_conns = [c for c in self.connections
                          if c.from_node in ids and c.to_node in ids]
            result.append((stage_idx, stage_nodes, stage_conns))
        return result

    async def _execute_pipeline(self, stages, yield_func):
        """流水线模式：按阶段顺序执行，阶段间传递上下文。"""
        import datetime

        # 为本次流水线运行创建独立子文件夹
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        task_keyword = self.task.strip()[:30].replace("\n", " ").replace("/", "_").replace("\\", "_").strip()
        run_folder = f"run_{ts}_{task_keyword}" if task_keyword else f"run_{ts}"
        run_folder = re.sub(r'[<>:"|?*]', '_', run_folder)
        run_folder = run_folder[:80]
        self.run_subfolder = run_folder
        run_dir = os.path.join(WORKSPACE_DIR, run_folder)
        os.makedirs(run_dir, exist_ok=True)

        named = []
        for i, (suffix, nodes, conns) in enumerate(stages):
            cfg_idx = suffix - 1  # suffix 1→outline, 2→writing, 3→polish
            if cfg_idx < len(self.STAGE_CONFIG):
                sname, slabel, sskills = self.STAGE_CONFIG[cfg_idx]
            else:
                sname, slabel, sskills = f"stage_{suffix}", f"阶段{suffix}", []
            named.append((suffix, sname, slabel, sskills, nodes, conns))

        yield_func({
            "status": "info", "role": "系统",
            "message": f"🚀 流水线模式 — {len(named)} 个阶段, {len(self.nodes)} 个节点: " +
                       " → ".join(f"{slabel}({len(nodes)}节点)" for _, _, slabel, _, nodes, _ in named)
        })

        prev_files = []
        prev_summary = ""

        for order, (suffix, sname, slabel, sskills, nodes, conns) in enumerate(named, 1):
            if self.cancelled:
                yield_func({"status": "warning", "message": "⏹️ 流水线已被用户取消"})
                break

            # 跳过已完成的阶段（resume 时使用）
            if sname in self._completed_stages:
                yield_func({
                    "status": "info", "role": "系统",
                    "message": f"⏭️ 阶段{order}/{len(named)}: {slabel} 已完成，跳过"
                })
                # 从已有文件中恢复 prev_files 和 prev_summary
                prev_files = list(self.saved_files)
                prev_summary = self._novel_summary or ""
                continue

            stage_task = self.task
            if prev_summary:
                stage_task = (
                    f"【原始用户任务】\n{self.task}\n\n"
                    f"【上一阶段产出摘要】\n{prev_summary}\n\n"
                    f"【上一阶段文件】\n" + "\n".join(f"  {f}" for f in prev_files[:30]) +
                    f"\n\n请基于以上产出继续推进当前阶段。"
                )

            yield_func({
                "status": "info", "role": "系统",
                "message": f"📖 阶段{order}/{len(named)}: {slabel} 开始 ({len(nodes)} 个节点)"
            })

            sub = GraphExecutor(
                nodes=nodes, connections=conns, task=stage_task,
                presets=[{"name": k, **v} for k, v in self.presets.items()],
                skills=sskills,
                conversation_history=self.conversation_history,
                execution_mode=self.execution_mode,
                prev_stage_files=list(prev_files),
                run_subfolder=run_folder,
            )
            sub._novel_stage = sname
            # 共享取消状态：父 executor 被取消时子 executor 同步
            sub.cancelled = self.cancelled
            self._active_sub = sub  # 让 stop 端点能找到正在运行的子 executor
            try:
                await sub._execute_phase_graph(yield_func)
            except Exception as e:
                yield_func({"status": "error", "role": "系统", "message": f"阶段 {slabel} 执行异常: {e}"})
                break
            self._active_sub = None
            # 同步回取消状态
            if sub.cancelled:
                self.cancelled = True

            prev_files = list(sub.saved_files)
            self.saved_files.extend(prev_files)

            output_summary = ""
            for nid, out in sub.outputs.items():
                node = sub.nodes.get(nid)
                if node and node.type == "manager" and not out.startswith("[ERROR]"):
                    # 清理退出标记，避免下一阶段 Manager 误判
                    cleaned = out.replace("[EXIT_LOOP]", "").replace("[APPROVED_EXIT]", "").replace(">>>APPROVED<<<", "").strip()
                    output_summary = cleaned[-1000:] if len(cleaned) > 1000 else cleaned
                    break
            prev_summary = output_summary

            # 记录已完成的阶段
            self._completed_stages.append(sname)

            yield_func({
                "status": "info", "role": "系统",
                "message": f"✅ 阶段{order}/{len(named)}: {slabel} 完成 (产出 {len(sub.saved_files)} 个文件)"
            })

            # Manual outline review: pause after outline stage for human confirmation
            if self.outline_review_mode == "manual" and sname == "outline":
                yield_func({
                    "status": "paused", "role": "系统",
                    "message": "📋 大纲已生成，等待人工确认。请在任务详情中点击「继续执行」来继续写作。",
                    "novel_stage": "outline_review"
                })
                self._save_checkpoint(round_idx=0, last_file_count=len(self.saved_files), stale_rounds=0, has_loop=False)
                return

        yield_func({
            "status": "done", "role": "系统",
            "message": f"🎉 流水线完成！共生成 {len(self.saved_files)} 个文件。"
        })

    async def execute(self, yield_func):
        """执行图谱任务 — 永远走流水线模式。

        节点按 _N 后缀分组为阶段，顺序执行，阶段间传递上下文。
        如果没有 _N 后缀，所有节点作为一个阶段执行。
        """
        pipeline_stages = self._detect_pipeline_stages()
        if not pipeline_stages:
            all_ids = list(self.nodes.keys())
            stage_conns = [c for c in self.connections if c.from_node in all_ids and c.to_node in all_ids]
            pipeline_stages = [(1, list(self.nodes.values()), stage_conns)]

        await self._execute_pipeline(pipeline_stages, yield_func)

    async def _execute_phase_graph(self, yield_func):
        """子阶段内执行 BFS 拓扑排序的多轮循环（流水线 sub-executor 的内部引擎）。"""
        phases = self._compute_phases()
        if not phases:
            yield_func({"status": "error", "message": "无法计算执行阶段"})
            return

        back_edges = self._find_back_edges()
        has_loop = len(back_edges) > 0
        manager_ids = set(self._find_managers())

        yield_func({
            "status": "info",
            "message": f"📋 {len(phases)} 个阶段" + (
                "，检测到反馈回路（Manager 决定何时退出）" if has_loop else "，单轮执行"
            )
        })

        # 小说模式：按阶段动态计算最大轮数
        novel_stage_rounds = getattr(self, '_novel_stage', '')
        if novel_stage_rounds:
            task_text = (self.task or "")
            ch_match = re.search(r'(\d+)\s*[章章]|(\d+)\s*chapters?', task_text)
            target = int(ch_match.group(1)) if ch_match else 0
            # 🔧 Bug 3 修复：各阶段独立计算 MAX_ROUNDS
            if novel_stage_rounds == "outline":
                # 大纲阶段：最多 20 轮，避免无限循环
                MAX_ROUNDS = self.mode_cfg.get("outline_max_rounds", 20)
            elif novel_stage_rounds == "writing":
                # 写作阶段：按章节数 × 3 轮（创作+审查+修改），保底100轮
                MAX_ROUNDS = max(target * 3, 100) if target > 0 else self.mode_cfg.get("writing_max_rounds", 300)
            elif novel_stage_rounds == "polish":
                # 审校阶段：章节数 × 2 轮，保底50轮
                MAX_ROUNDS = max(target * 2, 50) if target > 0 else self.mode_cfg.get("polish_max_rounds", 100)
            else:
                MAX_ROUNDS = self.mode_cfg.get("max_rounds", 100)
        else:
            MAX_ROUNDS = self.mode_cfg.get("max_rounds", 100)
        last_file_count = len(self.saved_files)  # resume 时不会误判停滞
        stale_rounds = 0

        async def run_node(nid, round_ctx):
            node = self.nodes.get(nid)
            if not node:
                return nid, None
            phase_inputs = []
            for conn in self.incoming.get(nid, []):
                fid = conn.from_node
                if fid in self.outputs:
                    fn = self.nodes.get(fid)
                    phase_inputs.append({
                        "from_id": fid,
                        "from_name": fn.config.get("agent_role", fn.type) if fn else fid,
                        "annotation": conn.annotation or "",
                        "output": self.outputs[fid]
                    })
            output = await self._execute_node(node, phase_inputs, round_ctx, yield_func)
            return nid, output

        for round_idx in range(1, MAX_ROUNDS + 1):
            self._last_round = round_idx
            if self.cancelled:
                yield_func({"status": "warning", "message": "⏹️ 任务已被用户取消"})
                break

            # 检查用户中途反馈
            new_feedback = []
            while not self.feedback_queue.empty():
                try:
                    msg = self.feedback_queue.get_nowait()
                    new_feedback.append(msg)
                except asyncio.QueueEmpty:
                    break
            if new_feedback:
                self.pending_feedback.extend(new_feedback)
                yield_func({
                    "status": "feedback_processing",
                    "message": f"📨 收到 {len(new_feedback)} 条用户反馈，Manager 正在重新规划..."
                })

            if round_idx > 1:
                yield_func({"status": "info", "message": f"🔄 第 {round_idx} 轮 — 反馈回路激活"})

            round_ctx = {"round": round_idx, "files": list(self.saved_files), "has_loop": has_loop,
                         "user_feedback": list(self.pending_feedback)}

            # 🔧 Bug 1 修复：Manager 已决定退出时，Worker/Reviewer 不再执行
            phase_skip_flag = False
            for phase_nodes in phases:
                if phase_skip_flag:
                    break
                # 在执行该 phase 前检查：上一轮/本轮已有的 Manager 输出是否包含 [EXIT_LOOP]
                manager_exited = False
                for mid in manager_ids:
                    if mid in self.outputs and self._manager_says_done(self.outputs[mid]):
                        manager_exited = True
                        break
                # 如果 Manager 已退出且当前 phase 包含非 Manager 节点 → 跳过
                if manager_exited:
                    has_non_manager = any(nid not in manager_ids for nid in phase_nodes)
                    if has_non_manager:
                        yield_func({
                            "status": "info",
                            "message": "⏹️  Manager 已决定退出，本轮跳过 Worker/Reviewer"
                        })
                        phase_skip_flag = True
                        break
                tasks = [run_node(nid, round_ctx) for nid in phase_nodes]
                results = await asyncio.gather(*tasks)
                for nid, output in results:
                    if output is not None:
                        self.outputs[nid] = output
                # 🔧 每个 phase 后检查：如果刚执行的是 Manager phase 且它输出了 [EXIT_LOOP]，后续 Worker/Reviewer phase 跳过
                if not phase_skip_flag:
                    for mid in manager_ids:
                        if mid in self.outputs and self._manager_says_done(self.outputs[mid]):
                            has_non_manager_left = any(
                                any(nid2 not in manager_ids for nid2 in pn2)
                                for pn2 in phases[phases.index(phase_nodes)+1:]
                            )
                            if has_non_manager_left:
                                phase_skip_flag = True
                                break

            # 解析 Manager 指令
            if not getattr(self, '_novel_stage', ''):
                self._parse_role_assignments()
            self._parse_skill_assignments()
            self._parse_file_operations()
            self._parse_summary()
            self._parse_memory()

            # 退出条件：Manager 说完成 + 小说模式下检查目标章数
            manager_done = False
            for mid in manager_ids:
                if mid in self.outputs and self._manager_says_done(self.outputs[mid]):
                    manager_done = True
                    yield_func({
                        "status": "info",
                        "message": "✅ Manager 判定任务完成，准备退出循环"
                    })
                    break

            if manager_done:
                # 小说模式：Reviewer 未通过时不准退出
                novel_stage = getattr(self, '_novel_stage', '')
                if novel_stage:
                    reviewer_rejected = False
                    for nid, node in self.nodes.items():
                        if node.type == "reviewer" and nid in self.outputs:
                            output = self.outputs[nid]
                            # 🔧 Bug 2 修复：更鲁棒的 Reviewer 结论检测
                            # 1) 先找"结论行"——"通过"或"✅"或"需修改"或"不通过"所在的行
                            # 2) 以"结论行"为准，避免长文中出现的"需修改"字样误判
                            conclusion_line = ""
                            has_approval_word = False
                            has_rejection_word = False
                            for line in output.split('\n'):
                                stripped = line.strip()
                                # 检测明确的"通过"信号（含各种格式）
                                has_approval = (
                                    ('✅' in stripped and '通过' in stripped) or
                                    stripped.startswith('通过') or
                                    stripped.startswith('通过 ✅') or
                                    stripped.startswith('✅ 通过') or
                                    stripped.startswith('通过（') or
                                    stripped.startswith('通过(') or
                                    (stripped == '通过') or
                                    (stripped.startswith('通过') and (len(stripped) < 20))
                                )
                                # 检测明确的"拒绝/需修改"信号
                                has_rejection = (
                                    stripped.startswith('需修改') or
                                    stripped.startswith('不通过') or
                                    stripped.startswith('未通过') or
                                    stripped.startswith('拒绝') or
                                    stripped.startswith('不合格') or
                                    stripped.startswith('❌') or
                                    ('需修改' in stripped and '通过' not in stripped and len(stripped) < 30) or
                                    ('❌' in stripped and '通过' not in stripped and len(stripped) < 30)
                                )
                                if has_approval or has_rejection:
                                    conclusion_line = stripped
                                    has_approval_word = has_approval
                                    has_rejection_word = has_rejection
                                    break
                            # 如果没有明确的"结论行"，再做文本整体扫描兜底判断
                            if not conclusion_line:
                                has_approval_word = (
                                    '通过 ✅' in output or
                                    '✅ 通过' in output or
                                    '通过（附带建议）' in output or
                                    output.strip().endswith('通过') or
                                    output.strip().endswith('通过 ✅') or
                                    output.strip().endswith('✅')
                                )
                                has_rejection_word = (
                                    '需修改' in output and '通过' not in output[:200] or
                                    output.strip().startswith('不通过') or
                                    output.strip().startswith('❌')
                                )
                            # 明确的通过信号 → 不拒绝；明确的拒绝信号 → 拒绝
                            if has_rejection_word and not has_approval_word:
                                reviewer_rejected = True
                                break
                            # 没有通过且没有拒绝 → 默认认为未完成（拒绝）
                            if not has_approval_word and not has_rejection_word and len(output) < 30:
                                reviewer_rejected = True
                                break
                    if reviewer_rejected:
                        for mid in manager_ids:
                            if mid in self.outputs:
                                self.outputs[mid] = self.outputs[mid].replace('[EXIT_LOOP]', '[CONTINUE]').replace('[APPROVED_EXIT]', '[CONTINUE]')
                        self._guard_override = (
                            "🔴🔴🔴 系统警告：审查者明确指出需要修改，你不允许退出！"
                            "请根据审查意见指令 Worker 修改，审查通过后才能退出。"
                            "禁止输出[EXIT_LOOP]！"
                        )
                        yield_func({
                            "status": "warning", "role": "系统",
                            "message": "⚠️ 审查者未通过，Manager 不允许退出。强制继续。"
                        })
                        manager_done = False
                        last_file_count = len(self.saved_files)
                        stale_rounds = 0
                        continue

                # 小说大纲阶段：大纲文件未产出不准退出
                if novel_stage == "outline":
                    has_outline = any("outline" in f.lower() for f in self.saved_files)
                    has_chars = any("character" in f.lower() for f in self.saved_files)
                    if not has_outline or not has_chars:
                        for mid in manager_ids:
                            if mid in self.outputs:
                                self.outputs[mid] = self.outputs[mid].replace('[EXIT_LOOP]', '[CONTINUE]').replace('[APPROVED_EXIT]', '[CONTINUE]')
                        self._guard_override = (
                            "🔴🔴🔴 系统警告：大纲和人物设定文件尚未全部产出！"
                            "请指令 Worker 产出 outline.md 和 characters.md，完成前禁止退出！"
                            "禁止输出[EXIT_LOOP]！"
                        )
                        yield_func({
                            "status": "warning", "role": "系统",
                            "message": "⚠️ 大纲/人物设定文件未产出，Manager 不允许退出。"
                        })
                        manager_done = False
                        last_file_count = len(self.saved_files)
                        stale_rounds = 0
                        continue

                # 小说写作阶段：未达标不准退出
                if novel_stage == "writing":
                    ch_nums = _count_chapters(self.saved_files)
                    current_done = len(ch_nums)
                    task_text = (self.task or "")
                    # 优先匹配 "N chapters"（前端构造的格式），其次匹配 "N章"
                    ch_match = re.search(r'(\d+)\s*chapters?', task_text, re.IGNORECASE)
                    if not ch_match:
                        ch_match = re.search(r'(\d+)\s*章', task_text)
                    target = int(ch_match.group(1)) if ch_match else 0
                    if target > 0 and current_done < target:
                        for mid in manager_ids:
                            if mid in self.outputs:
                                self.outputs[mid] = self.outputs[mid].replace('[EXIT_LOOP]', '[CONTINUE]').replace('[APPROVED_EXIT]', '[CONTINUE]')
                        self._guard_override = (
                            f"🔴🔴🔴 系统警告：你刚才声称任务完成但只写了{current_done}章！"
                            f"目标{target}章，还差{target - current_done}章。现在立刻继续，"
                            f"禁止输出[EXIT_LOOP]！不写完{target}章不许退出！"
                        )
                        yield_func({
                            "status": "warning", "role": "系统",
                            "message": f"⚠️ 仅产出 {current_done}/{target} 章，未达标。强制继续。"
                        })
                        last_file_count = len(self.saved_files)
                        stale_rounds = 0
                        continue
                break

            if not getattr(self, '_novel_stage', ''):
                if round_idx >= 2 and self._reviewer_approved() and self.saved_files:
                    self._consecutive_approvals += 1
                else:
                    self._consecutive_approvals = 0
                if self._consecutive_approvals >= 2:
                    break

            if not has_loop:
                break

            current_count = len(self.saved_files)
            if current_count > last_file_count:
                last_file_count = current_count
                stale_rounds = 0
            else:
                stale_rounds += 1
                if stale_rounds >= 3:
                    break

            # 每轮结束保存检查点
            if self.run_subfolder:
                self._save_checkpoint(round_idx, last_file_count, stale_rounds, has_loop)

    def _save_checkpoint(self, round_idx, last_file_count, stale_rounds, has_loop):
        """保存执行状态到 run 文件夹的 state.json（原子写入）"""
        try:
            # 只保留最近 50 轮的 outputs，避免 state.json 无限膨胀
            saved_outputs = dict(self.outputs)
            novel_stage = getattr(self, '_novel_stage', '')
            if novel_stage and len(saved_outputs) > 100:
                # 保留每个节点的最后一次输出
                trimmed = {}
                for k, v in saved_outputs.items():
                    trimmed[k] = v[-2000:] if len(v) > 2000 else v
                saved_outputs = trimmed

            state = {
                "task": self.task,
                "nodes": [{"id": n.id, "type": n.type, "config": n.config, "x": getattr(n, "x", 0), "y": getattr(n, "y", 0)} for n in self.nodes.values()],
                "connections": [{"id": c.id, "from": c.from_node, "fromPort": c.from_port,
                                 "to": c.to_node, "toPort": c.to_port, "annotation": c.annotation}
                                for c in self.connections],
                "presets": self.presets,
                "execution_mode": self.execution_mode,
                "outline_review_mode": getattr(self, 'outline_review_mode', 'auto'),
                "skills": self.skills,
                "active_skills": self.active_skills,
                "node_icons": self.node_icons,
                "node_roles": self.node_roles,
                "outputs": saved_outputs,
                "saved_files": self.saved_files,
                "run_subfolder": self.run_subfolder,
                "novel_stage": novel_stage,
                "round_idx": round_idx,
                "last_file_count": last_file_count,
                "stale_rounds": stale_rounds,
                "has_loop": has_loop,
                "novel_summary": getattr(self, '_novel_summary', ''),
                "conversation_history": self.conversation_history[-20:] if self.conversation_history else [],
                "novel_memory": getattr(self, '_novel_memory', ''),
                "guard_override": getattr(self, '_guard_override', ''),
                "consecutive_approvals": getattr(self, '_consecutive_approvals', 0),
                "completed_stages": getattr(self, '_completed_stages', []),
                "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            path = os.path.join(WORKSPACE_DIR, self.run_subfolder, "state.json")
            tmp_path = path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)  # 原子替换
        except Exception:
            pass

    @staticmethod
    def load_checkpoint(run_folder):
        """从 run 文件夹加载检查点。返回 dict 或 None。"""
        path = os.path.join(WORKSPACE_DIR, run_folder, "state.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

# ============================================