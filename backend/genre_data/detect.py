"""体裁检测 + 模板构建
数据来源: webnovel-writer 裁决规则 + InkOS 体裁文件
"""
from .genre_profiles import GENRE_PROFILES, VERDICT_RULES, DEFAULT_GENRE
from .taxonomy import (
    HOOK_TYPES, COOLPOINT_PATTERNS, MICROPAYOFF_TYPES,
    HARD_INVARIANTS, STRAND_DEFINITIONS,
)
from .inkos_data import get_inkos_genre, get_fatigue_words, get_chapter_types


def detect_genre(task: str) -> dict:
    """从用户任务中检测体裁，返回完整 profile"""
    task_lower = task.lower()

    # 先精确匹配 VERDICT_RULES 中的关键词
    for rule_name, rule in VERDICT_RULES.items():
        for kw in rule.get("keywords", []):
            if kw in task:
                # 尝试在 GENRE_PROFILES 中找到对应 profile
                for profile_name, profile in GENRE_PROFILES.items():
                    if rule_name in profile_name or any(kw in t for t in profile.get("tags", [])):
                        return {"name": profile_name, **profile}

    # 再匹配 GENRE_PROFILES 中的 tag
    for profile_name, profile in GENRE_PROFILES.items():
        for tag in profile.get("tags", []):
            if tag in task:
                return {"name": profile_name, **profile}

    return {"name": "通用", **DEFAULT_GENRE}


def build_genre_guide(genre_info: dict, novel_stage: str = "writing") -> str:
    """根据体裁和阶段构建注入到 prompt 的写作指南"""
    if not genre_info:
        return ""

    name = genre_info.get("name", "")
    if name == "通用":
        return ""

    parts = [f"\n【📖 体裁写作指南：{name}】"]

    # 风格优先级
    sp = genre_info.get("style_priority", [])
    if sp:
        parts.append(f"风格：{' > '.join(sp[:3])}")

    # 爽点
    cp = genre_info.get("coolpoint_priority", [])
    if cp:
        parts.append(f"爽点：{' > '.join(cp[:3])}")

    # 节奏
    rhythm = genre_info.get("rhythm_strategy", "")
    if rhythm:
        parts.append(f"节奏：{rhythm}")

    # 毒点
    poisons = genre_info.get("poison_weight", [])
    if poisons:
        parts.append(f"毒点（按权重）：{' > '.join(poisons[:3])}")

    # 风格笔记
    notes = genre_info.get("style_notes", "")
    if notes:
        parts.append(f"风格要点：{notes}")

    # 禁忌
    taboos = genre_info.get("anti_patterns", []) or genre_info.get("taboos", [])
    if taboos:
        parts.append(f"创作禁忌：{'；'.join(taboos[:5])}")

    # 冲突裁决
    verdict = genre_info.get("conflict_verdict", "")
    if verdict:
        parts.append(f"冲突裁决优先级：{verdict}")

    # === InkOS 数据补充 ===
    # 尝试匹配 InkOS 体裁
    inkos = None
    for inkos_name in ["玄幻", "仙侠", "都市", "恐怖", "通用"]:
        if inkos_name in name:
            inkos = get_inkos_genre(inkos_name)
            break
    if inkos and inkos.get("id") != "other":
        # 疲劳词
        fw = inkos.get("fatigueWords", [])[:6]
        if fw:
            parts.append(f"InkOS疲劳词（禁止）：{'、'.join(fw)}")
        # 爽点类型
        sat = inkos.get("satisfactionTypes", [])
        if sat:
            parts.append(f"InkOS爽点：{'、'.join(sat[:4])}")
        # 章节类型
        ct = inkos.get("chapterTypes", [])
        if ct:
            parts.append(f"章节分类：{'/'.join(ct)}")

    return "\n".join(parts)


def get_strand_rules() -> str:
    """构建 Strand 三线规则文本"""
    lines = [
        "【🎯 Strand 节奏管理】",
        "每章标注类型：---STRAND: Quest|Fire|Constellation---",
        "",
        "三线比例：",
    ]
    for key, info in STRAND_DEFINITIONS.items():
        lines.append(f"  {key}（{info['name']}）: {info['ratio']} | {info['description']}")
    lines.append("")
    lines.append("断档红线：")
    lines.append("  Quest 连续≤5章 | Fire 间隔≤10章 | Constellation 间隔≤15章")
    return "\n".join(lines)


def get_reviewer_dimensions() -> str:
    """构建 Reviewer 审查维度 — 来自 InkOS 真实 33 维审计 + webnovel-writer 追读力"""
    from .inkos_data import INKOS_AUDIT_DIMENSIONS

    dims = []
    # 核心维度（所有体裁通用）
    core = [1,2,3,6,8,9,10,11,13,14,16,17,18,19,24,25,26]
    for d in core:
        name = INKOS_AUDIT_DIMENSIONS.get(d, f"维度{d}")
        dims.append(f"{d}. {name}")

    lines = ["【审查维度 — 逐项检查，不可跳过】", ""]
    lines.extend(dims)
    lines.append("")
    lines.append("追读力 Hard Invariants（webnovel-writer）：")
    lines.append("HARD-001 可读性底线 | HARD-002 承诺兑现 | HARD-003 节奏灾难 | HARD-004 冲突真空")
    lines.append("")
    lines.append("结论: 通过 ✅ / 需修改（指出第几章、第几维度、什么问题）")
    return "\n".join(lines)
