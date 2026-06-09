"""体裁数据模块 — 统一导出
数据来源:
  - webnovel-writer/references/csv/ 裁决规则（genre_profiles.py）
  - webnovel-writer/references/ 追读力分类学（taxonomy.py）
  - webnovel-writer 写作指南（writing_guides.py）
  - InkOS packages/core/genres/*.md（inkos_data.py）
"""
from .detect import detect_genre, build_genre_guide, get_strand_rules, get_reviewer_dimensions
from .genre_profiles import GENRE_PROFILES, GENRE_TAGS, VERDICT_RULES
from .writing_guides import ANTI_AI_GUIDE, CORE_CONSTRAINTS, COOLPOINT_STRUCTURE
from .inkos_data import (
    INKOS_GENRES, INKOS_AUDIT_DIMENSIONS, INKOS_FATIGUE_WORDS,
    get_inkos_genre, get_fatigue_words, get_chapter_types,
    build_inkos_reviewer_guide, build_inkos_writer_guide,
)

__all__ = [
    "detect_genre", "build_genre_guide", "get_strand_rules", "get_reviewer_dimensions",
    "GENRE_PROFILES", "GENRE_TAGS", "VERDICT_RULES",
    "ANTI_AI_GUIDE", "CORE_CONSTRAINTS", "COOLPOINT_STRUCTURE",
    "INKOS_GENRES", "INKOS_AUDIT_DIMENSIONS", "INKOS_FATIGUE_WORDS",
    "get_inkos_genre", "get_fatigue_words", "get_chapter_types",
    "build_inkos_reviewer_guide", "build_inkos_writer_guide",
]
