"""
ProjectExecutor - 项目阶段执行管理器

将 GraphExecutor（多阶段小说生成引擎）与 ProjectDB（项目数据库）结合，
实现"一个项目 + 按阶段执行"的灵活模式：

1. 项目创建 → 2. 大纲阶段（可暂停+人工审查）→ 3. 写作阶段 → 4. 审校阶段

每个阶段完成后都会：
- 将产出文件同步到项目目录
- 更新数据库中的章节/记忆/对话记录
- 标记阶段完成状态
- 返回给前端，等你确认"继续下一阶段"
"""

import os
import asyncio
import json
import re
import time
from typing import List, Dict, Optional, Callable, Any

from executor import GraphExecutor, NodeInfo, ConnectionInfo
from project_db import (
    ProjectDB, list_all_projects, create_project, delete_project,
    get_project_dir, get_project_file, read_file_safe, write_file_safe,
)

# ============================================================
# 节点配置 - 标准三阶段模板
# ============================================================

def _build_novel_nodes(stage: str, preset_name: str = "") -> tuple:
    """
    为特定阶段构建节点和连接。
    stage: "outline" | "writing" | "polish"
    返回 (nodes, connections)
    """
    if stage == "outline":
        suffix = 1
    elif stage == "writing":
        suffix = 2
    elif stage == "polish":
        suffix = 3
    else:
        suffix = 1

    default_cfg = {
        "preset_name": preset_name,
        "custom_prompt": "",
        "agent_role": "",
        "label": "",
    }

    nodes = [
        NodeInfo(id=f"m_{suffix}", type="manager", config=dict(default_cfg)),
        NodeInfo(id=f"w_{suffix}", type="worker",  config=dict(default_cfg)),
        NodeInfo(id=f"r_{suffix}", type="reviewer", config=dict(default_cfg)),
    ]
    conns = [
        ConnectionInfo(id=f"auto_mw_{suffix}", from_node=f"m_{suffix}", to_node=f"w_{suffix}", annotation=""),
        ConnectionInfo(id=f"auto_wr_{suffix}", from_node=f"w_{suffix}", to_node=f"r_{suffix}", annotation=""),
        ConnectionInfo(id=f"auto_rm_{suffix}", from_node=f"r_{suffix}", to_node=f"m_{suffix}", annotation=""),
    ]
    return nodes, conns


# ============================================================
# 章节提取辅助
# ============================================================

_CH_PATTERNS = [
    r"第\s*(\d+)\s*章[章。、\s:：]*(.+?)(?=\n|$)",
    r"Chapter\s*(\d+)[\.\s:：]*(.+?)(?=\n|$)",
    r"^(\d+)\.\s*(.+?)(?=\n|$)",
]


def _parse_chapter_title(text: str) -> Optional[tuple]:
    """从文本中粗略提取"第X章 标题"。"""
    for pattern in _CH_PATTERNS:
        m = re.search(pattern, text[:200])
        if m:
            idx = int(m.group(1)) if m.group(1).isdigit() else 0
            title = m.group(2).strip().strip("：:。,.、-")[:60]
            if idx > 0:
                return (idx, title)
    # 尝试从文件名提取（outline.md 中有时用数字开头）
    return None


def _extract_chapter_from_file(filepath: str) -> Optional[Dict]:
    """从磁盘章节文件提取：章号、标题、字数。"""
    content = read_file_safe(filepath, "")
    if not content:
        return None
    bn = os.path.basename(filepath)
    m = re.search(r"第\s*(\d+)\s*章", bn)
    if not m:
        return None
    chapter_idx = int(m.group(1))
    title_line = content.split("\n", 1)[0].strip("# \n\r\t")
    if not title_line or len(title_line) > 80:
        title_line = f"第{chapter_idx}章"
    return {
        "chapter_index": chapter_idx,
        "title": title_line[:80],
        "summary": content[:200].strip(),
        "content": content,
        "word_count": len(content.replace(" ", "").replace("\n", "")),
    }


# ============================================================
# ProjectExecutor - 主类
# ============================================================

class ProjectExecutor:
    """
    按阶段执行的项目管理器。

    使用方式：
        pe = ProjectExecutor("我的小说项目", presets_list)
        pe.run_stage("outline", task="写一个100章的玄幻小说",
                     outline_review_mode="auto", execution_mode="standard",
                     yield_func=your_event_emitter)
        # 完成后...
        pe.run_stage("writing", ...)
        # 再完成后...
        pe.run_stage("polish", ...)
    """

    def __init__(self, project_name: str, presets: List[dict],
                 total_chapters: int = 100, genre: str = "", title: str = ""):
        self.project_name = project_name
        self.presets = presets
        self.total_chapters = total_chapters
        self.genre = genre

        # 初始化项目（如不存在则创建）
        try:
            create_project(
                name=project_name,
                title=title or project_name,
                genre=genre,
                total_chapters=total_chapters,
            )
        except Exception:
            pass

        # 获取 DB 引用
        self.db = ProjectDB(project_name)

        # 当前运行 executor 引用（用于 stop）
        self._executor: Optional[GraphExecutor] = None

    # ---------------- 基础查询 ----------------

    def info(self) -> Dict:
        """返回项目完整信息（给前端）。"""
        return self.db.to_dict()

    def get_progress(self) -> Dict:
        return self.db.get_progress()

    def get_stage(self) -> str:
        return self.db.get_project().get("current_stage", "outline")

    # ---------------- 核心：按阶段启动 ----------------

    async def run_stage(self, stage: str, task: str = "",
                        execution_mode: str = "standard",
                        outline_review_mode: str = "auto",
                        yield_func: Optional[Callable[[Dict], Any]] = None) -> Dict:
        """
        启动一个阶段。

        Args:
            stage: "outline" | "writing" | "polish"
            task: 补充任务描述（不包括章数/体裁，这些由项目设置提供）
            execution_mode: "standard" | "lite" | "full"
            outline_review_mode: "auto" | "manual" - 仅对 outline 阶段生效
            yield_func: 事件回调函数，每有新产出就会被调用

        Returns:
            {"success": bool, "stage": str, "saved_files": [...], "info": {...}}
        """
        if yield_func is None:
            yield_func = lambda ev: None

        stage_label = {
            "outline": "大纲创作",
            "writing": "分批写作",
            "polish": "全局审校",
        }.get(stage, stage)

        # 1) 合成任务描述
        info = self.db.get_project()
        project_title = info.get("title") or self.project_name
        project_genre = info.get("genre") or self.genre or ""
        project_chapters = info.get("total_chapters") or self.total_chapters or 100

        # 如果 outline/writing 阶段有前置文件，让引擎能读到
        prev_stage_files = self._collect_prev_stage_files(stage)

        full_task_parts = [f"《{project_title}》"]
        if project_genre:
            full_task_parts.append(f"{project_genre}风格")
        full_task_parts.append(f"共{project_chapters}章")
        if task:
            full_task_parts.append(f"要求：{task}")
        full_task = " ".join(full_task_parts)

        # 2) 构建子阶段节点
        nodes, conns = _build_novel_nodes(stage, preset_name=(self.presets[0].get("name") if self.presets else ""))

        # 3) 启动 GraphExecutor
        executor = GraphExecutor(
            nodes=nodes,
            connections=conns,
            task=full_task,
            presets=self.presets,
            skills=[],
            conversation_history=[],
            execution_mode=execution_mode,
            prev_stage_files=prev_stage_files,
            run_subfolder="",  # 留空，让它用 workspace 根目录；后会手动迁移到项目目录
            outline_review_mode=outline_review_mode if stage == "outline" else "auto",
        )
        self._executor = executor

        # 写事件：阶段开始
        yield_func({
            "status": "info", "role": "系统",
            "project_name": self.project_name, "stage": stage,
            "message": f"🚀 启动{stage_label}阶段：{project_title}",
        })

        # 启动阶段记录
        self.db.start_stage_run(stage)

        try:
            # 执行
            await executor.execute(yield_func)
        except Exception as e:
            yield_func({
                "status": "error", "role": "系统",
                "message": f"{stage_label}执行异常: {e}",
            })
            self.db.finish_stage_run(stage, "failed", str(e))
            return {"success": False, "stage": stage, "error": str(e)}

        # 4) 把产出文件迁移到项目目录，并同步到数据库
        saved_files = []
        try:
            saved_files = self._sync_outputs_to_project(stage, executor)
        except Exception as e:
            yield_func({
                "status": "warning", "role": "系统",
                "message": f"文件同步到项目目录时出错: {e}",
            })

        # 5) 记录阶段完成（如果是 manual 模式，则状态为 paused）
        stage_status = "paused" if (stage == "outline" and outline_review_mode == "manual") else "completed"

        if stage_status == "completed":
            # 标记阶段完成
            self.db.finish_stage_run(stage, "completed", f"产出{len(saved_files)}个文件")
            # 如果是 outline，推进到 writing；如果是 writing，推进到 polish
            if stage == "outline":
                self.db.set_stage("writing")
            elif stage == "writing":
                self.db.set_stage("polish")
            elif stage == "polish":
                self.db.set_stage("done")

            yield_func({
                "status": "done", "role": "系统",
                "project_name": self.project_name, "stage": stage,
                "message": f"✅ {stage_label}阶段完成，共产出 {len(saved_files)} 个文件",
                "saved_files": saved_files[:20],
                "progress": self.db.get_progress(),
            })
        else:
            # 暂停（manual review）
            self.db.finish_stage_run(stage, "paused", "等待人工审查大纲")
            self.db.set_stage("outline_review")  # 等待人工点击"继续写作"
            yield_func({
                "status": "paused", "role": "系统",
                "project_name": self.project_name, "stage": stage,
                "message": "📋 大纲已生成，等待人工确认。确认后可进入写作阶段。",
                "saved_files": saved_files[:20],
                "novel_stage": "outline_review",
            })

        self._executor = None
        return {
            "success": True, "stage": stage,
            "saved_files": saved_files,
            "info": self.db.to_dict(),
        }

    # ---------------- 从之前阶段收集文件 ----------------

    def _collect_prev_stage_files(self, current_stage: str) -> List[str]:
        """返回当前阶段之前已经生成的文件路径（相对于 WORKSPACE 根）。"""
        # outline 阶段没有前置文件
        if current_stage == "outline":
            return []

        proj_dir = get_project_dir(self.project_name)
        files = []

        # writing/polish 需要 outline.md 和 characters.md
        outline_file = os.path.join(proj_dir, "outline.md")
        chars_file = os.path.join(proj_dir, "characters.md")

        if os.path.exists(outline_file):
            # 转成相对路径（GraphExecutor 期望相对路径来 join WORKSPACE）
            from executor import WORKSPACE_DIR
            rel = os.path.relpath(outline_file, WORKSPACE_DIR)
            files.append(rel)
        if os.path.exists(chars_file):
            from executor import WORKSPACE_DIR
            rel = os.path.relpath(chars_file, WORKSPACE_DIR)
            files.append(rel)

        # 如果是 polish，也加上已写的章节
        if current_stage == "polish":
            chapters_dir = os.path.join(proj_dir, "chapters")
            if os.path.exists(chapters_dir):
                for f in sorted(os.listdir(chapters_dir)):
                    if f.endswith(".txt") or f.endswith(".md"):
                        from executor import WORKSPACE_DIR
                        rel = os.path.relpath(os.path.join(chapters_dir, f), WORKSPACE_DIR)
                        files.append(rel)

        return files

    # ---------------- 文件同步 ----------------

    def _sync_outputs_to_project(self, stage: str, executor: GraphExecutor) -> List[str]:
        """
        把 executor 产出的文件（saved_files 中）同步到项目目录。
        - outline.md / characters.md → 项目根目录，并写入数据库
        - 章节文本 → 项目 chapters/ 目录，章节元数据写数据库
        - 记忆 → memory/novel_memory.md，同时写入数据库
        """
        from executor import WORKSPACE_DIR

        saved = []
        for relpath in list(getattr(executor, "saved_files", [])):
            src = os.path.join(WORKSPACE_DIR, relpath)
            if not os.path.exists(src):
                continue
            bname = os.path.basename(relpath)

            content = read_file_safe(src, "")
            if not content:
                continue

            # 根据文件类型分派
            lower = bname.lower()
            if lower == "outline.md":
                self.db.save_outline(content)
                saved.append(f"outline.md")
            elif lower == "characters.md":
                self.db.save_characters(content)
                saved.append(f"characters.md")
            elif "memory" in lower and lower.endswith(".md"):
                self.db.save_novel_memory(content)
                saved.append(f"memory/{bname}")
            elif re.search(r"第\s*\d+\s*章", bname) or lower.startswith("chapter"):
                # 章节文件
                info = _extract_chapter_from_file(src)
                if info and info["chapter_index"] > 0:
                    chap_path = os.path.join(get_project_dir(self.project_name), "chapters",
                                             f"第{info['chapter_index']}章.txt")
                    write_file_safe(chap_path, content)
                    self.db.upsert_chapter(
                        chapter_index=info["chapter_index"],
                        title=info["title"],
                        summary=info["summary"],
                        status="drafted",
                        content=content,
                        word_count=info["word_count"],
                        prev_text="",
                    )
                    saved.append(f"chapters/第{info['chapter_index']}章.txt")
                else:
                    # 无法识别章节号，放到 misc
                    misc_path = os.path.join(get_project_dir(self.project_name), bname)
                    write_file_safe(misc_path, content)
                    saved.append(bname)
            else:
                misc_path = os.path.join(get_project_dir(self.project_name), bname)
                write_file_safe(misc_path, content)
                saved.append(bname)

        # 更新 total_chapters
        info = self.db.get_project()
        if info.get("total_chapters", 0) == 0 and self.total_chapters > 0:
            self.db.update_project(total_chapters=self.total_chapters)

        # 收集记忆摘要
        novel_summary = getattr(executor, "_novel_summary", "") or ""
        if novel_summary:
            self.db.add_memory("summary", novel_summary, 0)

        return saved

    # ---------------- 人工审查后继续 ----------------

    def confirm_outline_and_continue(self) -> Dict:
        """人工审查大纲通过，推进到写作阶段。
        返回新的阶段状态供前端刷新 UI。"""
        # 如果 outline_review 状态，则推进到 writing
        current = self.get_stage()
        if current in ("outline", "outline_review"):
            self.db.set_stage("writing")
        return self.db.to_dict()

    def reject_outline_and_restart(self) -> Dict:
        """人工审查不通过，保留 outline 状态让重新生成。"""
        self.db.set_stage("outline")
        return self.db.to_dict()

    # ---------------- 停止 ----------------

    def stop(self):
        """停止当前运行中的 executor。"""
        if self._executor:
            self._executor.cancelled = True

    # ---------------- 对话/助理 ----------------

    def add_chat(self, role: str, content: str) -> None:
        self.db.add_chat(role, content, self.get_stage())

    def list_chat(self) -> List[Dict]:
        return self.db.list_chat(100)


# ============================================================
# 便捷函数（给 API 层用）
# ============================================================

def list_projects_for_api() -> List[Dict]:
    return list_all_projects()


def create_project_for_api(name: str, title: str = "", genre: str = "",
                           total_chapters: int = 100) -> Dict:
    return create_project(name=name, title=title, genre=genre, total_chapters=total_chapters)


def delete_project_for_api(name: str) -> Dict:
    ok = delete_project(name)
    return {"success": ok}


def get_project_info(name: str) -> Dict:
    db = ProjectDB(name)
    data = db.to_dict()
    db.close()
    return data


def update_project_settings(name: str, **fields) -> Dict:
    db = ProjectDB(name)
    ok = db.update_project(**{k: v for k, v in fields.items() if v is not None})
    info = db.get_project()
    db.close()
    return {"success": ok, "project": info}


# ============================================================
# 同步章节文件到数据库（一次性工具，老项目/手动添加章节用）
# ============================================================

def sync_chapters_to_db(project_name: str) -> Dict:
    """扫描项目 chapters/ 目录，把已有章节写进数据库。"""
    proj_dir = get_project_dir(project_name)
    chapters_dir = os.path.join(proj_dir, "chapters")
    count = 0
    if os.path.exists(chapters_dir):
        db = ProjectDB(project_name)
        for fname in sorted(os.listdir(chapters_dir)):
            info = _extract_chapter_from_file(os.path.join(chapters_dir, fname))
            if info and info["chapter_index"] > 0:
                db.upsert_chapter(
                    chapter_index=info["chapter_index"],
                    title=info["title"],
                    summary=info["summary"],
                    status="drafted",
                    content=info["content"],
                    word_count=info["word_count"],
                )
                count += 1
        db.close()
    return {"synced": count}
