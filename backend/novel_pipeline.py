"""Novel-specific pipeline helpers"""

from typing import List, Dict

STAGE_CONFIG = [
    ("outline", "大纲创作", []),
    ("writing", "分批写作", ["长篇小说创作"]),
    ("polish", "全局审校", ["长篇小说创作"]),
]


def build_stage_context(
    stage_name: str,
    chapter_count: int,
    outline: str = "",
    characters: str = "",
) -> str:
    """Build context for a pipeline stage.

    Args:
        stage_name: One of "outline", "writing", "polish".
        chapter_count: Target total chapter count.
        outline: Outline content string (if available).
        characters: Characters setting content string (if available).

    Returns:
        A context string suitable for injecting into the system prompt.
    """
    parts = [f"【小说创作阶段：{stage_name}】"]

    if stage_name == "outline":
        parts.append(f"目标章数：{chapter_count}")
        parts.append("请产出 outline.md（每章1-2句概要）+ characters.md（人物设定）。")
    elif stage_name == "writing":
        parts.append(f"目标章数：{chapter_count}")
        parts.append("请逐章写作，每章800-1500字。严格围绕大纲，不偏离主线。")
    elif stage_name == "polish":
        parts.append("请全局审校所有章节：前后一致性、伏笔回收、文风统一、错别字修正。")

    if outline:
        parts.append(f"\n【大纲参考】\n{outline}")
    if characters:
        parts.append(f"\n【人物设定】\n{characters}")

    return "\n".join(parts)
