"""
Project Database Module - SQLite 项目数据库

一个项目文件夹 = 一个独立数据库文件，管理:
- projects (项目元数据)
- chapters (章节索引)
- memory_items (记忆条目)
- chat_messages (对话历史)
- stage_runs (阶段运行记录)
"""

import os
import sqlite3
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Any, Union

# ============================================================
# 基础路径配置
# ============================================================

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
PROJECTS_DIR = os.path.join(WORKSPACE_DIR, "projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)


# ============================================================
# 工具函数
# ============================================================

def get_project_dir(project_name: str) -> str:
    """返回项目文件夹路径（自动创建）"""
    d = os.path.join(PROJECTS_DIR, project_name)
    os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(d, "chapters"), exist_ok=True)
    os.makedirs(os.path.join(d, "memory"), exist_ok=True)
    return d


def get_project_db_path(project_name: str) -> str:
    """返回项目 SQLite 数据库路径"""
    return os.path.join(get_project_dir(project_name), "project.db")


def get_project_file(project_name: str, filename: str) -> str:
    """返回项目内文件的完整路径"""
    return os.path.join(get_project_dir(project_name), filename)


def get_chapter_path(project_name: str, chapter_index: int) -> str:
    """返回章节文件路径"""
    return os.path.join(get_project_dir(project_name), "chapters", f"第{chapter_index}章.txt")


def read_file_safe(path: str, default: str = "") -> str:
    """安全读取文件"""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return default


def write_file_safe(path: str, content: str) -> bool:
    """安全写入文件"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception:
        return False


def fmt_time(timestamp: Optional[float] = None) -> str:
    """格式化时间字符串"""
    t = timestamp or time.time()
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# 项目数据库
# ============================================================

class ProjectDB:
    """项目数据库 - 每个项目独立连接"""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        title TEXT DEFAULT '',
        genre TEXT DEFAULT '',
        total_chapters INTEGER DEFAULT 0,
        current_stage TEXT DEFAULT 'outline',  -- outline | writing | polish | done
        ai_preset TEXT DEFAULT '',
        execution_mode TEXT DEFAULT 'lite',
        outline_review_mode TEXT DEFAULT 'auto',  -- auto | manual
        description TEXT DEFAULT '',
        created_at TEXT DEFAULT '',
        updated_at TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS chapters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        chapter_index INTEGER NOT NULL,
        title TEXT DEFAULT '',
        summary TEXT DEFAULT '',
        content_path TEXT DEFAULT '',
        status TEXT DEFAULT 'not_started',  -- not_started | in_progress | drafted | reviewed | final
        word_count INTEGER DEFAULT 0,
        prev_text TEXT DEFAULT '',
        created_at TEXT DEFAULT '',
        updated_at TEXT DEFAULT '',
        FOREIGN KEY (project_id) REFERENCES projects(id),
        UNIQUE (project_id, chapter_index)
    );

    CREATE TABLE IF NOT EXISTS memory_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        type TEXT DEFAULT '',  -- summary | character | hook | world | memory | etc
        content TEXT DEFAULT '',
        chapter_ref INTEGER DEFAULT 0,
        created_at TEXT DEFAULT '',
        FOREIGN KEY (project_id) REFERENCES projects(id)
    );

    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        role TEXT NOT NULL,  -- user | assistant | system
        content TEXT NOT NULL,
        context TEXT DEFAULT '',  -- 当前阶段: outline/writing/polish
        created_at TEXT DEFAULT '',
        FOREIGN KEY (project_id) REFERENCES projects(id)
    );

    CREATE TABLE IF NOT EXISTS stage_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        stage TEXT NOT NULL,  -- outline | writing | polish
        status TEXT DEFAULT 'pending',  -- pending | running | completed | paused | failed
        started_at TEXT DEFAULT '',
        finished_at TEXT DEFAULT '',
        message TEXT DEFAULT '',
        FOREIGN KEY (project_id) REFERENCES projects(id)
    );

    CREATE INDEX IF NOT EXISTS idx_chapters_project ON chapters(project_id);
    CREATE INDEX IF NOT EXISTS idx_chapters_index ON chapters(chapter_index);
    CREATE INDEX IF NOT EXISTS idx_memory_project ON memory_items(project_id);
    CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_items(type);
    CREATE INDEX IF NOT EXISTS idx_chat_project ON chat_messages(project_id);
    CREATE INDEX IF NOT EXISTS idx_stage_project ON stage_runs(project_id);
    """

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.db_path = get_project_db_path(project_name)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()
        self._ensure_project_record()

    # ---------------- 内部方法 ----------------

    def _init_schema(self):
        """初始化表结构"""
        self.conn.executescript(self.SCHEMA)
        self.conn.commit()

    def _ensure_project_record(self):
        """确保项目记录存在"""
        cur = self.conn.execute("SELECT id FROM projects WHERE name=?", (self.project_name,))
        row = cur.fetchone()
        now = fmt_time()
        if not row:
            self.conn.execute(
                "INSERT INTO projects (name, title, total_chapters, current_stage, outline_review_mode, execution_mode, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.project_name, self.project_name, 0, "outline", "auto", "lite", now, now)
            )
            self.conn.commit()

    def _now(self) -> str:
        return fmt_time()

    def _row_to_dict(self, row) -> Optional[Dict]:
        if row is None:
            return None
        return dict(row)

    def _rows_to_list(self, rows) -> List[Dict]:
        return [dict(r) for r in rows]

    # ---------------- 项目 CRUD ----------------

    def get_project(self) -> Dict:
        """获取项目信息"""
        cur = self.conn.execute("SELECT * FROM projects WHERE name=?", (self.project_name,))
        return self._row_to_dict(cur.fetchone()) or {}

    def update_project(self, **kwargs) -> bool:
        """更新项目字段"""
        if not kwargs:
            return False
        kwargs["updated_at"] = self._now()
        fields = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [self.project_name]
        try:
            self.conn.execute(f"UPDATE projects SET {fields} WHERE name=?", values)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[DB] update_project error: {e}")
            return False

    def set_stage(self, stage: str) -> bool:
        """设置当前阶段"""
        return self.update_project(current_stage=stage)

    def get_stage(self) -> str:
        """获取当前阶段"""
        project = self.get_project()
        return project.get("current_stage", "outline") or "outline"

    # ---------------- 章节 CRUD ----------------

    def list_chapters(self) -> List[Dict]:
        """获取所有章节列表（按序号排序）"""
        cur = self.conn.execute(
            "SELECT * FROM chapters WHERE project_id=(SELECT id FROM projects WHERE name=?) ORDER BY chapter_index",
            (self.project_name,)
        )
        return self._rows_to_list(cur.fetchall())

    def get_chapter(self, chapter_index: int) -> Optional[Dict]:
        """获取单个章节信息"""
        cur = self.conn.execute(
            "SELECT * FROM chapters WHERE project_id=(SELECT id FROM projects WHERE name=?) AND chapter_index=?",
            (self.project_name, chapter_index)
        )
        row = cur.fetchone()
        if not row:
            return None
        d = self._row_to_dict(row)
        # 读取实际内容（如果文件存在）
        path = d.get("content_path") or get_chapter_path(self.project_name, chapter_index)
        d["content"] = read_file_safe(path, "")
        return d

    def upsert_chapter(self, chapter_index: int, title: str = "", summary: str = "",
                        status: str = "drafted", content: Optional[str] = None,
                        word_count: int = 0, prev_text: str = "") -> bool:
        """插入或更新章节"""
        project = self.get_project()
        project_id = project.get("id", 1)
        now = self._now()
        path = get_chapter_path(self.project_name, chapter_index)

        # 保存内容到磁盘
        if content is not None:
            write_file_safe(path, content)
            if word_count == 0:
                word_count = len(content.replace(" ", "").replace("\n", ""))

        # 更新数据库
        try:
            cur = self.conn.execute(
                "SELECT id FROM chapters WHERE project_id=? AND chapter_index=?",
                (project_id, chapter_index)
            )
            if cur.fetchone():
                self.conn.execute(
                    "UPDATE chapters SET title=?, summary=?, content_path=?, status=?, word_count=?, prev_text=?, updated_at=? WHERE project_id=? AND chapter_index=?",
                    (title, summary, path, status, word_count, prev_text, now, project_id, chapter_index)
                )
            else:
                self.conn.execute(
                    "INSERT INTO chapters (project_id, chapter_index, title, summary, content_path, status, word_count, prev_text, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (project_id, chapter_index, title, summary, path, status, word_count, prev_text, now, now)
                )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[DB] upsert_chapter error: {e}")
            return False

    def update_chapter_status(self, chapter_index: int, status: str) -> bool:
        """更新章节状态"""
        project = self.get_project()
        try:
            self.conn.execute(
                "UPDATE chapters SET status=?, updated_at=? WHERE project_id=? AND chapter_index=?",
                (status, self._now(), project.get("id", 1), chapter_index)
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def delete_chapter(self, chapter_index: int) -> bool:
        """删除章节"""
        project = self.get_project()
        try:
            self.conn.execute(
                "DELETE FROM chapters WHERE project_id=? AND chapter_index=?",
                (project.get("id", 1), chapter_index)
            )
            self.conn.commit()
            # 同时删除文件
            path = get_chapter_path(self.project_name, chapter_index)
            if os.path.exists(path):
                os.remove(path)
            return True
        except Exception:
            return False

    def get_chapter_count(self) -> int:
        """已完成章节数"""
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM chapters WHERE project_id=(SELECT id FROM projects WHERE name=?) AND status IN ('drafted','reviewed','final','revised')",
            (self.project_name,)
        )
        row = cur.fetchone()
        return row[0] if row else 0

    def get_progress(self) -> Dict:
        """获取项目进度摘要"""
        project = self.get_project()
        chapters = self.list_chapters()
        total = project.get("total_chapters", 0) or len(chapters) or 0
        done = len([c for c in chapters if c.get("status") in ("drafted", "reviewed", "final", "revised")])
        total_words = sum(c.get("word_count", 0) for c in chapters)
        return {
            "total": total,
            "done": done,
            "percent": round(done / total * 100, 1) if total > 0 else 0,
            "total_words": total_words,
            "current_stage": project.get("current_stage", "outline"),
        }

    # ---------------- 记忆 CRUD ----------------

    def list_memory(self, mem_type: str = "") -> List[Dict]:
        """获取记忆条目"""
        project = self.get_project()
        if mem_type:
            cur = self.conn.execute(
                "SELECT * FROM memory_items WHERE project_id=? AND type=? ORDER BY id",
                (project.get("id", 1), mem_type)
            )
        else:
            cur = self.conn.execute(
                "SELECT * FROM memory_items WHERE project_id=? ORDER BY type, id",
                (project.get("id", 1),)
            )
        return self._rows_to_list(cur.fetchall())

    def add_memory(self, mem_type: str, content: str, chapter_ref: int = 0) -> int:
        """添加记忆条目"""
        project = self.get_project()
        try:
            cur = self.conn.execute(
                "INSERT INTO memory_items (project_id, type, content, chapter_ref, created_at) VALUES (?, ?, ?, ?, ?)",
                (project.get("id", 1), mem_type, content, chapter_ref, self._now())
            )
            self.conn.commit()
            return cur.lastrowid
        except Exception as e:
            print(f"[DB] add_memory error: {e}")
            return 0

    def clear_memory_type(self, mem_type: str) -> bool:
        """清除某类型记忆"""
        project = self.get_project()
        try:
            self.conn.execute(
                "DELETE FROM memory_items WHERE project_id=? AND type=?",
                (project.get("id", 1), mem_type)
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    # ---------------- 对话 CRUD ----------------

    def list_chat(self, limit: int = 50) -> List[Dict]:
        """获取对话历史（最新N条，按时间正序）"""
        project = self.get_project()
        cur = self.conn.execute(
            "SELECT * FROM chat_messages WHERE project_id=? ORDER BY id DESC LIMIT ?",
            (project.get("id", 1), limit)
        )
        rows = cur.fetchall()
        return list(reversed(self._rows_to_list(rows)))

    def add_chat(self, role: str, content: str, context: str = "") -> int:
        """添加一条对话"""
        project = self.get_project()
        try:
            cur = self.conn.execute(
                "INSERT INTO chat_messages (project_id, role, content, context, created_at) VALUES (?, ?, ?, ?, ?)",
                (project.get("id", 1), role, content, context, self._now())
            )
            self.conn.commit()
            return cur.lastrowid
        except Exception as e:
            print(f"[DB] add_chat error: {e}")
            return 0

    def clear_chat(self) -> bool:
        """清空对话历史"""
        project = self.get_project()
        try:
            self.conn.execute("DELETE FROM chat_messages WHERE project_id=?", (project.get("id", 1),))
            self.conn.commit()
            return True
        except Exception:
            return False

    # ---------------- 阶段运行记录 ----------------

    def start_stage_run(self, stage: str) -> int:
        """启动一个阶段"""
        project = self.get_project()
        try:
            cur = self.conn.execute(
                "INSERT INTO stage_runs (project_id, stage, status, started_at) VALUES (?, ?, 'running', ?)",
                (project.get("id", 1), stage, self._now())
            )
            self.conn.commit()
            self.set_stage(stage)
            return cur.lastrowid
        except Exception as e:
            print(f"[DB] start_stage_run error: {e}")
            return 0

    def finish_stage_run(self, stage: str, status: str = "completed", message: str = "") -> bool:
        """完成一个阶段"""
        project = self.get_project()
        try:
            self.conn.execute(
                "UPDATE stage_runs SET status=?, finished_at=?, message=? WHERE project_id=? AND stage=? AND status='running'",
                (status, self._now(), message, project.get("id", 1), stage)
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def list_stage_runs(self) -> List[Dict]:
        """获取阶段运行记录"""
        project = self.get_project()
        cur = self.conn.execute(
            "SELECT * FROM stage_runs WHERE project_id=? ORDER BY id",
            (project.get("id", 1),)
        )
        return self._rows_to_list(cur.fetchall())

    # ---------------- 文件操作（大纲/人物/记忆原文） ----------------

    def save_outline(self, content: str) -> bool:
        """保存大纲"""
        path = get_project_file(self.project_name, "outline.md")
        ok = write_file_safe(path, content)
        if ok:
            self.update_project(updated_at=self._now())
        return ok

    def save_characters(self, content: str) -> bool:
        """保存人物设定"""
        path = get_project_file(self.project_name, "characters.md")
        ok = write_file_safe(path, content)
        if ok:
            # 同步到 memory_items
            self.clear_memory_type("character")
            self.add_memory("character", f"characters.md 完整内容已保存（{len(content)}字）", 0)
        return ok

    def save_novel_memory(self, content: str) -> bool:
        """保存长篇记忆（novel_memory.md）"""
        path = get_project_file(self.project_name, "memory", "novel_memory.md")
        ok = write_file_safe(path, content)
        if ok:
            self.clear_memory_type("memory")
            self.add_memory("memory", f"novel_memory.md 已更新（{len(content)}字）", 0)
        return ok

    def read_outline(self) -> str:
        return read_file_safe(get_project_file(self.project_name, "outline.md"), "")

    def read_characters(self) -> str:
        return read_file_safe(get_project_file(self.project_name, "characters.md"), "")

    def read_novel_memory(self) -> str:
        return read_file_safe(get_project_file(self.project_name, "memory", "novel_memory.md"), "")

    def read_chapter_content(self, chapter_index: int) -> str:
        """读取章节正文"""
        return read_file_safe(get_chapter_path(self.project_name, chapter_index), "")

    # ---------------- 导出 ----------------

    def to_dict(self) -> Dict:
        """导出完整项目信息（给前端用）"""
        project = self.get_project()
        chapters = self.list_chapters()
        progress = self.get_progress()
        summary_memory = "\n".join(m.get("content", "") for m in self.list_memory("summary"))
        character_memory = "\n".join(m.get("content", "") for m in self.list_memory("character"))

        return {
            "project": project,
            "chapters": chapters,
            "progress": progress,
            "memory_summary": summary_memory,
            "memory_character": character_memory,
            "outline": self.read_outline(),
            "characters": self.read_characters(),
            "chat": self.list_chat(100),
            "stage_runs": self.list_stage_runs(),
        }

    def close(self):
        """关闭连接"""
        try:
            self.conn.close()
        except Exception:
            pass


# ============================================================
# 项目列表管理（projects 目录下的所有项目）
# ============================================================

def list_all_projects() -> List[Dict]:
    """获取所有项目摘要"""
    result = []
    if not os.path.exists(PROJECTS_DIR):
        return result
    for name in sorted(os.listdir(PROJECTS_DIR)):
        p = os.path.join(PROJECTS_DIR, name)
        if not os.path.isdir(p):
            continue
        db_path = os.path.join(p, "project.db")
        try:
            db = ProjectDB(name)
            info = db.get_project()
            progress = db.get_progress()
            db.close()
            result.append({
                "name": name,
                "title": info.get("title", name),
                "genre": info.get("genre", ""),
                "total_chapters": info.get("total_chapters", 0),
                "current_stage": info.get("current_stage", "outline"),
                "created_at": info.get("created_at", ""),
                "updated_at": info.get("updated_at", ""),
                "progress": progress,
            })
        except Exception:
            # 还没初始化的文件夹
            result.append({
                "name": name, "title": name, "genre": "",
                "total_chapters": 0, "current_stage": "outline",
                "created_at": "", "updated_at": "", "progress": {"total": 0, "done": 0, "percent": 0, "total_words": 0, "current_stage": "outline"}
            })
    return result


def create_project(name: str, title: str = "", genre: str = "",
                   total_chapters: int = 0, execution_mode: str = "lite",
                   outline_review_mode: str = "auto") -> Dict:
    """创建新项目"""
    # 清理不合法字符
    safe_name = "".join(c for c in name if c.isalnum() or c in "_-《》（）()[] ")
    safe_name = safe_name.strip() or f"project_{int(time.time())}"

    db = ProjectDB(safe_name)
    db.update_project(
        title=title or safe_name,
        genre=genre,
        total_chapters=total_chapters,
        execution_mode=execution_mode,
        outline_review_mode=outline_review_mode,
    )
    info = db.get_project()
    db.close()
    return {"success": True, "name": safe_name, "project": info}


def delete_project(name: str) -> bool:
    """删除项目（删除整个文件夹）"""
    p = os.path.join(PROJECTS_DIR, name)
    if not os.path.exists(p):
        return False
    import shutil
    try:
        shutil.rmtree(p)
        return True
    except Exception as e:
        print(f"[DB] delete_project error: {e}")
        return False
