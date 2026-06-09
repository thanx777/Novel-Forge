"""
全局记忆管理器 — 管理每部小说的累计式上下文记忆

记忆文件: run_xxx/memory/novel_memory.md
由 Manager 每 N 章更新，包含：
- 角色状态
- 主线进展
- 伏笔记录
- 世界观设定
"""
import os
import re
from typing import Optional


class MemoryManager:
    """管理小说全局记忆的读写和摘要提取"""

    MEMORY_DIRNAME = "memory"
    MEMORY_FILENAME = "novel_memory.md"

    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.memory_dir = os.path.join(run_dir, self.MEMORY_DIRNAME)
        self.memory_path = os.path.join(self.memory_dir, self.MEMORY_FILENAME)
        self._content: Optional[str] = None
        self._loaded = False

    # ----- 加载 -----

    def load(self) -> str:
        """加载记忆内容，未加载时返回空"""
        if self._loaded:
            return self._content or ""

        if os.path.isfile(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    self._content = f.read()
            except Exception:
                self._content = ""
        else:
            self._content = ""

        self._loaded = True
        return self._content or ""

    @property
    def content(self) -> str:
        return self.load()

    def is_loaded(self) -> bool:
        return self._loaded

    # ----- 写入 -----

    def save(self, text: str) -> None:
        """写入记忆文件（完全替换）"""
        os.makedirs(self.memory_dir, exist_ok=True)
        with open(self.memory_path, "w", encoding="utf-8") as f:
            f.write(text)
        self._content = text
        self._loaded = True

    def append(self, text: str) -> None:
        """追加到记忆文件末尾"""
        existing = self.load()
        self.save(existing + "\n\n" + text if existing else text)

    # ----- 摘要 -----

    def get_recent_context(self, max_chars: int = 2000) -> str:
        """获取用于注入到写作 prompt 的最近上下文"""
        content = self.load()
        if not content:
            return ""
        return content[-max_chars:] if len(content) > max_chars else content

    def get_summary(self, max_chars: int = 1000) -> str:
        """获取情节摘要（用于阶段间传递）"""
        content = self.load()
        if not content:
            return ""

        # 优先提取 [SUMMARY:] 标记的内容
        summaries = re.findall(r'\[SUMMARY:\s*(.+?)\]', content, re.DOTALL)
        if summaries:
            return "\n".join(s.strip()[:200] for s in summaries)[-max_chars:]

        # 回退：取最后的内容
        return content[-max_chars:] if len(content) > max_chars else content

    # ----- 更新 -----

    def update_from_manager_output(self, manager_output: str) -> None:
        """从 Manager 的输出中提取 [MEMORY:] 和 [SUMMARY:] 标记更新记忆"""
        if not manager_output:
            return

        # 提取 [MEMORY:] 块
        memory_blocks = re.findall(r'\[MEMORY:\s*(.+?)\]', manager_output, re.DOTALL)
        if memory_blocks:
            self.save("\n\n".join(m.strip() for m in memory_blocks))

        # 提取 [SUMMARY:] 块并追加
        summary_blocks = re.findall(r'\[SUMMARY:\s*(.+?)\]', manager_output, re.DOTALL)
        for s in summary_blocks:
            existing = self.load()
            if s.strip() not in existing:
                lines = existing.split("\n") if existing else []
                lines.append(f"[SUMMARY: {s.strip()}]")
                self.save("\n".join(lines))

    def get_chapter_summaries(self) -> list:
        """提取所有章节摘要"""
        content = self.load()
        if not content:
            return []

        # 按 "第N章" 分段
        chapters = re.split(r'\n(?=第\d+章)', content)
        summaries = []
        for ch in chapters:
            m = re.match(r'(第\d+章).*?[：:]\s*(.+)', ch)
            if m:
                summaries.append({"title": m.group(1), "summary": m.group(2)[:200]})
        return summaries

    # ----- 章节索引 -----

    def get_chapter_count(self) -> int:
        """从记忆中提取已完成章节数"""
        content = self.load()
        chapters = re.findall(r'第\d+章', content)
        nums = set()
        for ch in chapters:
            num = re.search(r'(\d+)', ch)
            if num:
                nums.add(int(num.group(1)))
        return len(nums)
