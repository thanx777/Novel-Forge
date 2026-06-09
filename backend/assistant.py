"""
Project Assistant - 项目 AI 助理

在引擎暂停/停止时，也能基于项目当前状态进行对话。

能力：
1. 读取项目大纲 / 人物设定 / 章节内容 / 记忆
2. 分析、提建议、做续写
3. 也能接受用户指令（"重新写第5章"、"把大纲改成东方玄幻"）
"""

import os
import re
from typing import List, Dict, Optional

from executor import AgentConfig, call_llm
from project_db import ProjectDB, get_project_dir, read_file_safe
from project_executor import get_project_file


# ============================================================
# 上下文收集
# ============================================================

def _collect_project_context(project_name: str, max_chapters: int = 5) -> str:
    """收集项目当前状态的简要上下文，作为 LLM 的背景。"""
    db = ProjectDB(project_name)
    info = db.get_project()
    chapters = db.list_chapters()
    memory_md = db.read_novel_memory()
    outline_md = db.read_outline()
    characters_md = db.read_characters()

    total = info.get("total_chapters") or 0
    done = len(chapters)
    stage = info.get("current_stage", "outline")

    lines = [
        f"【项目: {info.get('title') or project_name}】",
        f"- 体裁: {info.get('genre') or '未设置'}",
        f"- 目标章节: {total}",
        f"- 已写章节: {done}",
        f"- 当前阶段: {stage}",
    ]

    # 大纲（简洁版）
    if outline_md:
        snippet = outline_md[:1500]
        if len(outline_md) > 1500:
            snippet += "\n...(大纲过长，仅展示前 1500 字)"
        lines.append("\n【大纲概要】\n" + snippet)

    # 人物设定
    if characters_md:
        snippet = characters_md[:800]
        if len(characters_md) > 800:
            snippet += "\n..."
        lines.append("\n【人物设定】\n" + snippet)

    # 最近几章的摘要
    recent = chapters[-max_chapters:] if chapters else []
    if recent:
        lines.append(f"\n【最近 {len(recent)} 章摘要】")
        for c in recent:
            title = c.get("title") or f"第{c.get('chapter_index', '?')}章"
            summary = c.get("summary") or "（无摘要）"
            lines.append(f"- 第{c.get('chapter_index', '?')}章 {title}: {summary[:60]}")

    # 全文记忆
    if memory_md:
        snippet = memory_md[:500]
        if len(memory_md) > 500:
            snippet += "\n..."
        lines.append("\n【长篇记忆】\n" + snippet)

    db.close()
    return "\n".join(lines)


def _read_chapter_content(project_name: str, chapter_index: int) -> str:
    """读取某一章的完整内容。"""
    proj_dir = get_project_dir(project_name)
    path = os.path.join(proj_dir, "chapters", f"第{chapter_index}章.txt")
    return read_file_safe(path, f"(第{chapter_index}章尚未撰写)")


def _parse_command(user_message: str) -> Dict:
    """分析用户消息，看是否是特殊指令。"""
    msg = user_message.strip()
    lower = msg.lower()

    # 重读某章
    m = re.search(r"(?:第|chapter\s*)?\s*(\d+)\s*章", msg, re.IGNORECASE)
    if m and ("内容" in msg or "看" in msg or "读" in msg or "review" in lower or "显示" in msg):
        return {"action": "read_chapter", "chapter": int(m.group(1))}

    # 重新生成大纲
    if "重新" in msg and ("大纲" in msg or "outline" in lower):
        return {"action": "ask_regen_outline"}

    # 列出章节
    if "列出" in msg and "章" in msg:
        return {"action": "list_chapters"}

    return {"action": "chat"}


# ============================================================
# Assistant 主类
# ============================================================

class ProjectAssistant:

    def __init__(self, project_name: str, presets: List[dict]):
        self.project_name = project_name
        self.presets = presets

    # ---------- 配置 ----------

    def _get_agent_config(self) -> Optional[AgentConfig]:
        if not self.presets:
            return None
        p = self.presets[0]
        return AgentConfig(
            api_key=p.get("api_key", ""),
            base_url=p.get("base_url", ""),
            model=p.get("model", ""),
            api_format=getattr(p, "api_format", "openai"),
            chat_template_kwargs=p.get("chat_template_kwargs"),
        )

    # ---------- 主入口 ----------

    def chat(self, user_message: str, sys_overrides: str = "") -> str:
        """
        用户说一句话，助理结合项目上下文回应。
        同步返回（非流式），简洁版。
        """
        cmd = _parse_command(user_message)
        user_msg = user_message

        # 根据 action 处理
        if cmd["action"] == "read_chapter":
            content = _read_chapter_content(self.project_name, cmd["chapter"])
            return f"【第{cmd['chapter']}章完整内容】\n\n{content[:3000]}" + ("\n...(过长截断)" if len(content) > 3000 else "")

        if cmd["action"] == "list_chapters":
            db = ProjectDB(self.project_name)
            chapters = db.list_chapters()
            db.close()
            if not chapters:
                return "还没有已写的章节。"
            lines = [f"【已写章节列表（{len(chapters)}章）】"]
            for c in chapters:
                title = c.get("title") or f"第{c.get('chapter_index')}章"
                wc = c.get("word_count", 0)
                lines.append(f"- 第{c.get('chapter_index')}章 {title}（{wc}字）")
            return "\n".join(lines)

        if cmd["action"] == "ask_regen_outline":
            return "好的，你可以在 UI 上点击「重新生成大纲」按钮启动 outline 阶段。"

        # 普通 chat：结合上下文给 LLM
        cfg = self._get_agent_config()
        if not cfg or not cfg.api_key:
            return "（没有配置 LLM preset，助理无法调用 AI）"

        ctx = _collect_project_context(self.project_name)
        system_prompt = (
            "你是一个专业的小说创作助理。你会阅读用户提供的项目上下文（大纲、人物、已写章节、记忆），"
            "并根据用户的提问给出建议、分析或内容。保持中文回复，简洁清晰，避免长篇大论。"
            + (("\n" + sys_overrides) if sys_overrides else "")
        )
        user_prompt = f"当前项目上下文：\n{ctx}\n\n用户提问：{user_msg}\n\n请给出回复（简洁，不超过500字）。"

        import asyncio
        try:
            text = asyncio.run(call_llm(cfg, system_prompt, user_prompt, 1200, 60))
        except Exception as e:
            text = f"(LLM 调用失败: {e})"

        # 存一份对话历史
        db = ProjectDB(self.project_name)
        db.add_chat("user", user_msg, "assistant")
        db.add_chat("assistant", text, "assistant")
        db.close()
        return text

    # ---------- 专项能力 ----------

    def suggest_next_chapter(self) -> str:
        """根据当前大纲和已写章节，建议下一章怎么写。"""
        cfg = self._get_agent_config()
        if not cfg or not cfg.api_key:
            return "（没有配置 LLM preset）"

        ctx = _collect_project_context(self.project_name)
        sys_prompt = (
            "你是一个资深的小说编辑。根据项目上下文，简要给出下一章的写作建议，"
            "包括关键冲突、人物发展、悬念设置等。"
        )
        user_prompt = f"项目上下文：\n{ctx}\n\n请给出下一章（第?章）的写作建议，300字以内。"
        import asyncio
        try:
            return asyncio.run(call_llm(cfg, sys_prompt, user_prompt, 1000, 60))
        except Exception as e:
            return f"(LLM 调用失败: {e})"

    def analyze_consistency(self) -> str:
        """检查人物/设定一致性。"""
        cfg = self._get_agent_config()
        if not cfg or not cfg.api_key:
            return "（没有配置 LLM preset）"

        ctx = _collect_project_context(self.project_name, max_chapters=10)
        sys_prompt = "你是一个严谨的小说审稿编辑。检查人物、时间线、设定是否一致，给出问题列表和修正建议。"
        user_prompt = f"项目上下文：\n{ctx}\n\n请指出可能的一致性问题（人物性格、情节、时间线、设定等）。"
        import asyncio
        try:
            return asyncio.run(call_llm(cfg, sys_prompt, user_prompt, 1500, 90))
        except Exception as e:
            return f"(LLM 调用失败: {e})"


# ============================================================
# 便捷函数
# ============================================================

def assistant_chat(project_name: str, presets: List[dict], message: str) -> str:
    """单行调用。"""
    pa = ProjectAssistant(project_name, presets)
    return pa.chat(message)
