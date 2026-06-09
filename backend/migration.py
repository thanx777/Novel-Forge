"""
Old Project Migration - 将旧版 run_xxx 目录下的内容导入新项目系统。

旧版目录结构：
    workspace/run_YYYYMMDD_HHMMSS_<description>/
        outline.md
        characters.md
        state.json
        novel_memory.md  (有时)
        第1章.txt, 第2章.txt, ...

新结构：
    workspace/projects/<项目名>/
        project.db
        outline.md
        characters.md
        memory/novel_memory.md
        chapters/第1章.txt, 第2章.txt...

用法：
    python migration.py          # 自动扫描所有 run_* 目录
    python migration.py --dry-run # 只看看会怎么做，不实际写入
"""

import os
import re
import json
import shutil
import argparse
from typing import List, Dict, Optional

# 从现有模块导入
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from project_db import (
    ProjectDB, create_project, get_project_dir, read_file_safe, write_file_safe, WORKSPACE_DIR
)
from project_executor import _extract_chapter_from_file


CHAPTER_RE = re.compile(r"第\s*(\d+)\s*章.*\.(txt|md)", re.IGNORECASE)


def scan_old_projects(workspace: str) -> List[str]:
    """扫描 workspace 目录下所有 run_* 子目录。"""
    if not os.path.exists(workspace):
        return []
    result = []
    for sub in sorted(os.listdir(workspace)):
        full = os.path.join(workspace, sub)
        if not os.path.isdir(full):
            continue
        if sub.startswith("run_"):
            result.append(full)
        # 也可能有老项目直接在 workspace 根
        elif os.path.exists(os.path.join(full, "outline.md")) and os.path.exists(
            os.path.join(full, "state.json")
        ):
            result.append(full)
    return result


def analyze_old_project(folder: str) -> Dict:
    """分析一个旧项目目录，提取信息。"""
    info = {
        "folder": folder,
        "name": os.path.basename(folder),
        "description": "",
        "total_chapters": 0,
        "chapter_files": [],
        "has_outline": os.path.exists(os.path.join(folder, "outline.md")),
        "has_characters": os.path.exists(os.path.join(folder, "characters.md")),
        "has_memory": os.path.exists(os.path.join(folder, "novel_memory.md")),
    }

    # 从 state.json / 文件名提取描述
    base = os.path.basename(folder)
    if "_" in base:
        # run_20260529_153031_写一个50章的科幻小说
        parts = base.split("_", 2)
        if len(parts) >= 3:
            info["description"] = parts[2].replace("_", " ")

    # state.json
    state_path = os.path.join(folder, "state.json")
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            info["state"] = state
            if isinstance(state, dict):
                info["total_chapters"] = state.get("total_chapters") or state.get("target_chapters") or 0
        except Exception:
            pass

    # 扫描章节文件
    for fn in sorted(os.listdir(folder)):
        if CHAPTER_RE.match(fn):
            info["chapter_files"].append(os.path.join(folder, fn))
    info["total_chapters"] = max(info["total_chapters"], len(info["chapter_files"]))
    return info


def infer_project_title(info: Dict) -> str:
    """从描述推断项目标题。"""
    desc = info.get("description", "") or info.get("name", "")
    # 写一个100章的科幻小说 -> 科幻小说
    m = re.search(r"(?:写一个|写)(\d+)?章?的?(.+)", desc)
    if m:
        return (m.group(2) or desc).strip()
    return desc or "未命名项目"


def infer_genre(description: str) -> str:
    d = description or ""
    if "科幻" in d or "science" in d.lower():
        return "科幻"
    if "玄幻" in d or "仙侠" in d or "修真" in d:
        return "玄幻/仙侠"
    if "都市" in d:
        return "都市"
    if "奇幻" in d or "fantasy" in d.lower():
        return "奇幻"
    if "悬疑" in d or "恐怖" in d:
        return "悬疑/恐怖"
    if "历史" in d or "军事" in d:
        return "历史/军事"
    return ""


def migrate_one(folder: str, dry_run: bool = False, force: bool = False) -> Dict:
    """迁移单个旧项目。"""
    info = analyze_old_project(folder)
    title = infer_project_title(info)
    genre = infer_genre(info["description"])
    chapters = info["chapter_files"]

    # 创建新的项目名（避免重复）
    safe_name = title[:40] or info["name"]
    safe_name = re.sub(r"[\\/:*?\"<>|]", "_", safe_name)

    proj_dir = get_project_dir(safe_name)
    if os.path.exists(proj_dir) and not force and not dry_run:
        print(f"  [跳过] {safe_name} 已存在，使用 --force 覆盖")
        return {"status": "exists", "name": safe_name}

    print(f"\n  -> 迁移: {safe_name} ({len(chapters)}章)")
    print(f"     来源: {folder}")
    print(f"     体裁: {genre or '(未识别)'}")

    if dry_run:
        return {"status": "dry-run", "name": safe_name, "chapters": len(chapters)}

    # 创建项目 + 数据库
    create_project(
        name=safe_name,
        title=title,
        genre=genre,
        total_chapters=info["total_chapters"] or len(chapters),
    )

    # 写文件
    new_dir = proj_dir

    # outline.md
    if info["has_outline"]:
        src = os.path.join(folder, "outline.md")
        content = read_file_safe(src, "")
        if content:
            write_file_safe(os.path.join(new_dir, "outline.md"), content)

    # characters.md
    if info["has_characters"]:
        src = os.path.join(folder, "characters.md")
        content = read_file_safe(src, "")
        if content:
            write_file_safe(os.path.join(new_dir, "characters.md"), content)

    # novel_memory.md -> memory/
    if info["has_memory"]:
        src = os.path.join(folder, "novel_memory.md")
        content = read_file_safe(src, "")
        if content:
            os.makedirs(os.path.join(new_dir, "memory"), exist_ok=True)
            write_file_safe(os.path.join(new_dir, "memory", "novel_memory.md"), content)

    # 章节文件
    chapters_dir = os.path.join(new_dir, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    db = ProjectDB(safe_name)
    count = 0
    for chap_src in chapters:
        chap_info = _extract_chapter_from_file(chap_src)
        if chap_info and chap_info.get("chapter_index"):
            idx = chap_info["chapter_index"]
            content = chap_info["content"]
            chap_path = os.path.join(chapters_dir, f"第{idx}章.txt")
            write_file_safe(chap_path, content)
            db.upsert_chapter(
                chapter_index=idx,
                title=chap_info["title"],
                summary=chap_info["summary"],
                status="drafted",
                content=content,
                word_count=chap_info["word_count"],
            )
            count += 1

    # 同步 memory 条目
    nm = read_file_safe(os.path.join(new_dir, "memory", "novel_memory.md"), "")
    if nm:
        db.add_memory("memory", f"novel_memory.md 已导入（{len(nm)}字）", 0)

    outline_md = read_file_safe(os.path.join(new_dir, "outline.md"), "")
    if outline_md:
        db.add_memory("outline", f"outline.md 已导入（{len(outline_md)}字）", 0)

    chars_md = read_file_safe(os.path.join(new_dir, "characters.md"), "")
    if chars_md:
        db.add_memory("character", f"characters.md 已导入（{len(chars_md)}字）", 0)

    db.close()

    print(f"     完成！导入 {count} 个章节")
    return {"status": "ok", "name": safe_name, "chapters": count}


def main():
    parser = argparse.ArgumentParser(description="迁移旧 run_* 项目到新版 projects 系统")
    parser.add_argument("--dry-run", action="store_true", help="只扫描，不实际写入")
    parser.add_argument("--force", action="store_true", help="同名项目重新写入（不跳过）")
    args = parser.parse_args()

    workspace = WORKSPACE_DIR
    print(f"扫描目录: {workspace}")
    folders = scan_old_projects(workspace)
    print(f"找到 {len(folders)} 个旧项目")

    results = []
    for folder in folders:
        results.append(migrate_one(folder, dry_run=args.dry_run, force=args.force))

    print("\n=== 汇总 ===")
    for r in results:
        status = r.get("status")
        name = r.get("name")
        extra = f" ({r.get('chapters', 0)}章)" if status in ("ok", "dry-run") else ""
        print(f"  [{status}] {name}{extra}")


if __name__ == "__main__":
    main()
