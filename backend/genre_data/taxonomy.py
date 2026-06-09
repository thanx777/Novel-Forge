"""追读力分类学 (Reading Power Taxonomy)
来源: webnovel-writer/references/reading-power-taxonomy.md
"""

# ============================================
# 一、钩子类型 (Hook Types) — 5 种
# ============================================
HOOK_TYPES = {
    "危机钩": {
        "id": "crisis",
        "description": "敌人出现/危险逼近/生死危机",
        "trigger": "主角或在意的人面临直接威胁",
        "strength": "strong",
        "genres": ["爽文", "玄幻", "悬疑", "末世"],
    },
    "悬念钩": {
        "id": "mystery",
        "description": "信息缺口/未解之谜/反常现象",
        "trigger": "出现无法解释的事件或可疑线索",
        "strength": "medium",
        "genres": ["悬疑", "灵异", "科幻", "规则怪谈"],
    },
    "情绪钩": {
        "id": "emotion",
        "description": "触发强烈情绪反应（愤怒/心疼/共情/不公）",
        "trigger": "主角遭受不白之冤、被背叛、弱者被欺凌",
        "strength": "strong",
        "genres": ["言情", "爽文", "都市", "甜宠"],
    },
    "选择钩": {
        "id": "choice",
        "description": "两难抉择/高风险决策",
        "trigger": "两个选项各有利弊，角色被迫选择",
        "strength": "medium",
        "genres": ["悬疑", "权谋", "竞技", "科幻"],
    },
    "渴望钩": {
        "id": "desire",
        "description": "展示可期待的奖励/成就/进展",
        "trigger": "好事即将发生/奖励可期/突破在即",
        "strength": "medium",
        "genres": ["爽文", "玄幻", "游戏", "种田"],
    },
}

# ============================================
# 二、爽点模式 (Cool Points) — 8 种
# ============================================
COOLPOINT_PATTERNS = {
    "装逼打脸": {
        "id": "face_slap",
        "structure": "对方轻视 → 主角展示实力 → 对方震惊/后悔",
        "genres": ["都市", "玄幻", "职场"],
        "strength": 5,
    },
    "扮猪吃虎": {
        "id": "hidden_power",
        "structure": "表面弱小 → 关键时刻爆发 → 众人惊艳",
        "genres": ["重生", "都市", "玄幻"],
        "strength": 4,
    },
    "越级反杀": {
        "id": "overlevel_kill",
        "structure": "实力差距明显 → 主角逆袭 → 敌人不可置信",
        "genres": ["玄幻", "武侠", "竞技"],
        "strength": 5,
    },
    "打脸权威": {
        "id": "authority_slap",
        "structure": "权威质疑 → 主角用实力证明 → 权威认可/尴尬",
        "genres": ["职场", "学院", "技术流"],
        "strength": 4,
    },
    "反派翻车": {
        "id": "villain_fail",
        "structure": "反派得意 → 计划破产 → 反派狼狈",
        "genres": ["所有题材"],
        "strength": 4,
    },
    "甜蜜超预期": {
        "id": "sweet_surprise",
        "structure": "平淡日常 → 意外惊喜 → 情感升温",
        "genres": ["言情", "甜宠"],
        "strength": 3,
    },
    "迪化误解": {
        "id": "misunderstanding_power",
        "structure": "路人低估主角 → 主角无意展示 → 路人脑补过度",
        "genres": ["爽文", "都市", "科幻"],
        "strength": 3,
    },
    "身份掉马": {
        "id": "identity_reveal",
        "structure": "隐藏身份 → 意外暴露/主动揭示 → 众人震惊",
        "genres": ["都市", "重生", "历史"],
        "strength": 4,
    },
}

# ============================================
# 三、微兑现类型 (Micro Payoffs) — 7 种
# ============================================
MICROPAYOFF_TYPES = {
    "信息兑现": {"id": "info", "description": "揭示新信息/线索/真相", "example": "原来那把钥匙的真正用途是..."},
    "关系兑现": {"id": "relation", "description": "关系推进/确认/变化", "example": "她第一次主动握住了他的手"},
    "能力兑现": {"id": "ability", "description": "能力提升/新技能/突破", "example": "他终于掌握了这门功法的精髓"},
    "资源兑现": {"id": "resource", "description": "获得物品/资源/财富", "example": "储物袋里竟然还藏着一颗聚气丹"},
    "认可兑现": {"id": "recognition", "description": "获得认可/面子/地位", "example": "在场所有人看他的眼神都变了"},
    "情绪兑现": {"id": "emotion", "description": "情绪释放/共鸣/宣泄", "example": "他终于说出了压在心底的那句话"},
    "线索兑现": {"id": "clue", "description": "伏笔回收/线索推进", "example": "三年前的那件事，终于有了眉目"},
}

# ============================================
# 四、Hard Invariants（不可违反红线）
# ============================================
HARD_INVARIANTS = [
    {
        "id": "HARD-001",
        "name": "可读性底线",
        "rule": "关键信息缺失导致看不懂 → 读者无法回答'发生了什么/谁在做什么/为什么'",
        "trigger": "章节无清晰事件/角色行动无动机",
    },
    {
        "id": "HARD-002",
        "name": "承诺兑现",
        "rule": "上章钩子必须在本章回应（允许部分兑现，不要求一次性结清）",
        "trigger": "明确的章末承诺在下章无任何回应",
    },
    {
        "id": "HARD-003",
        "name": "节奏灾难",
        "rule": "不可连续N章无任何推进（无新信息/关系变化/能力变化/局势变化）",
        "trigger": "连续多章读者感觉'这章看了和没看一样'",
    },
    {
        "id": "HARD-004",
        "name": "冲突真空",
        "rule": "每章必须有 问题/目标/代价（至少一项可被识别）",
        "trigger": "整章无悬念/无期待/无代价",
    },
]

# ============================================
# 五、Strand Weave 三线定义
# ============================================
STRAND_DEFINITIONS = {
    "Quest": {
        "name": "主线推进",
        "ratio": "55-65%",
        "max_consecutive": 5,
        "description": "核心任务、升级、战斗、夺宝、复仇",
    },
    "Fire": {
        "name": "感情线",
        "ratio": "20-30%",
        "max_gap": 10,
        "description": "情感关系发展（爱情/友情/师徒），爽点高潮",
    },
    "Constellation": {
        "name": "世界观线",
        "ratio": "10-20%",
        "max_gap": 15,
        "description": "扩展设定、展示新势力/地点、揭示身世",
    },
}

# ============================================
# 六、爽点三段式结构
# ============================================
COOLPOINT_STRUCTURE = {
    "setup": {"ratio": "30%", "description": "建立预期 + 制造反差 + 信息差设置"},
    "delivery": {"ratio": "40%", "description": "触发时机 + 展现方式 + 情绪高峰"},
    "twist": {"ratio": "30%", "description": "假结束 + 还有一手 + 余韵"},
}

# 压扬比例
PRESSURE_RELEASE_RATIO = {
    "传统爽文": "压3扬7 — 轻度压迫，快速释放",
    "硬核正剧": "压5扬5 — 平衡叙事",
    "虐恋/黑深残": "压7扬3 — 长期压抑，爆发更爽",
}
