"""Agent role loader — parses .md agent definitions from agency-agents-zh."""
import os, re, yaml, glob
from typing import Optional, Dict, List

AGENTS_DIR = os.path.join(os.path.dirname(__file__), "agents")

def parse_agent_file(path: str) -> Optional[Dict]:
    """Parse a single agent .md file: YAML frontmatter + markdown body."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not m:
        return None
    try:
        meta = yaml.safe_load(m.group(1))
    except Exception:
        return None
    return {
        "path": path,
        "name": meta.get("name", os.path.basename(path).replace(".md", "")),
        "description": meta.get("description", ""),
        "emoji": meta.get("emoji", "🤖"),
        "color": meta.get("color", "gray"),
        "content": m.group(2).strip(),
        "department": os.path.basename(os.path.dirname(path)),
    }


def load_all_agents() -> List[Dict]:
    """Load all agent definitions from the agents/ directory."""
    agents = []
    for path in glob.glob(os.path.join(AGENTS_DIR, "**/*.md"), recursive=True):
        agent = parse_agent_file(path)
        if agent:
            agents.append(agent)
    return sorted(agents, key=lambda a: a["name"])


def build_role_catalog(agents: List[Dict]) -> str:
    """Build a compact role catalog for the Manager to select from.
    Returns a markdown table."""
    lines = ["| # | 角色名 | 部门 | 简介 |",
             "|---|--------|------|------|"]
    for i, a in enumerate(agents, 1):
        desc = a["description"][:60] + ("..." if len(a["description"]) > 60 else "")
        lines.append(f"| {i} | {a['name']} | {a['department']} | {desc} |")
    return "\n".join(lines)


def get_agent_by_name(agents: List[Dict], name: str) -> Optional[Dict]:
    """Find an agent by exact name match."""
    for a in agents:
        if a["name"] == name:
            return a
    return None


def get_agent_by_index(agents: List[Dict], index: int) -> Optional[Dict]:
    """Find an agent by 1-based index in the catalog."""
    if 1 <= index <= len(agents):
        return agents[index - 1]
    return None
