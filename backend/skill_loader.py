"""Skill loader — loads skill definitions from the skills/ directory.
Skills are reusable prompt templates that inject domain knowledge into agents.

Supported formats: .md (with YAML frontmatter), .yaml, .json, .txt
"""

import os
import re
import yaml
import json
import glob
from typing import Optional, Dict, List

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "skills")


def parse_skill_file(path: str) -> Optional[Dict]:
    """Parse a skill file. Supports .md (frontmatter+body), .yaml, .json, .txt."""
    ext = os.path.splitext(path)[1].lower()
    basename = os.path.splitext(os.path.basename(path))[0]

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    if ext in (".yaml", ".yml"):
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                return {
                    "path": path,
                    "name": data.get("name", basename),
                    "description": data.get("description", ""),
                    "category": data.get("category", "custom"),
                    "tags": data.get("tags", []),
                    "icon": data.get("icon", "🔧"),
                    "apply_to": data.get("apply_to", ["worker"]),
                    "version": data.get("version", "1.0"),
                    "content": data.get("content", content),
                }
        except Exception:
            pass

    if ext == ".json":
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return {
                    "path": path,
                    "name": data.get("name", basename),
                    "description": data.get("description", ""),
                    "category": data.get("category", "custom"),
                    "tags": data.get("tags", []),
                    "icon": data.get("icon", "🔧"),
                    "apply_to": data.get("apply_to", ["worker"]),
                    "version": data.get("version", "1.0"),
                    "content": data.get("content", content),
                }
        except Exception:
            pass

    # .md with YAML frontmatter, or plain .txt
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if m:
        try:
            meta = yaml.safe_load(m.group(1))
        except Exception:
            meta = {}
        body = m.group(2).strip()
        return {
            "path": path,
            "name": meta.get("name", basename),
            "description": meta.get("description", ""),
            "category": meta.get("category", "custom"),
            "tags": meta.get("tags", []),
            "icon": meta.get("icon", "🔧"),
            "apply_to": meta.get("apply_to", ["worker"]),
            "version": meta.get("version", "1.0"),
            "content": body,
        }

    # Plain text file — use filename as name
    return {
        "path": path,
        "name": basename,
        "description": f"Plain text skill: {basename}",
        "category": "custom",
        "tags": [],
        "icon": "📄",
        "apply_to": ["worker"],
        "version": "1.0",
        "content": content.strip(),
    }


def load_all_skills() -> List[Dict]:
    """Load all skills from the skills/ directory. Returns metadata-only (no content body)."""
    skills = []
    patterns = ["**/*.md", "**/*.yaml", "**/*.yml", "**/*.json", "**/*.txt"]
    for pattern in patterns:
        for path in glob.glob(os.path.join(SKILLS_DIR, pattern), recursive=True):
            skill = parse_skill_file(path)
            if skill and skill["name"]:
                skills.append({
                    "name": skill["name"],
                    "description": skill["description"],
                    "category": skill["category"],
                    "tags": skill["tags"],
                    "icon": skill["icon"],
                    "apply_to": skill["apply_to"],
                    "version": skill["version"],
                })
    # Deduplicate by name
    seen = set()
    unique = []
    for s in sorted(skills, key=lambda s: s["name"]):
        if s["name"] not in seen:
            seen.add(s["name"])
            unique.append(s)
    return unique


def load_skill_content(name: str) -> Optional[Dict]:
    """Load the full content of a skill by name."""
    patterns = ["**/*.md", "**/*.yaml", "**/*.yml", "**/*.json", "**/*.txt"]
    for pattern in patterns:
        for path in glob.glob(os.path.join(SKILLS_DIR, pattern), recursive=True):
            skill = parse_skill_file(path)
            if skill and skill["name"] == name:
                return skill
    return None


def save_skill(name: str, content: str, description: str = "", category: str = "custom",
               tags: list = None, icon: str = "🔧", apply_to: list = None, version: str = "1.0") -> str:
    """Save a skill as a .skill.md file. Returns the file path."""
    os.makedirs(SKILLS_DIR, exist_ok=True)
    safe_name = name.replace("/", "-").replace("\\", "-")
    filepath = os.path.join(SKILLS_DIR, f"{safe_name}.skill.md")

    tags_yaml = yaml.dump(tags or [], default_flow_style=True).strip()
    apply_yaml = yaml.dump(apply_to or ["worker"], default_flow_style=True).strip()

    skill_md = f"""---
name: {safe_name}
description: {description}
category: {category}
tags: {tags_yaml}
icon: {icon}
apply_to: {apply_yaml}
version: {version}
---

{content}
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(skill_md)
    return filepath


def delete_skill(name: str) -> bool:
    """Delete a skill file by name. Returns True if deleted."""
    patterns = ["**/*.md", "**/*.yaml", "**/*.yml", "**/*.json", "**/*.txt"]
    for pattern in patterns:
        for path in glob.glob(os.path.join(SKILLS_DIR, pattern), recursive=True):
            skill = parse_skill_file(path)
            if skill and skill["name"] == name:
                os.remove(path)
                return True
    return False


def search_skills(query: str, all_skills: List[Dict] = None) -> List[Dict]:
    """Search skills by name, description, category, or tags."""
    if all_skills is None:
        all_skills = load_all_skills()
    q = query.lower()
    results = []
    for s in all_skills:
        score = 0
        if q in s["name"].lower():
            score += 10
        if q in s["description"].lower():
            score += 5
        if q in s["category"].lower():
            score += 3
        for tag in s.get("tags", []):
            if q in tag.lower():
                score += 4
        if score > 0:
            results.append({**s, "score": score})
    return sorted(results, key=lambda s: s["score"], reverse=True)
