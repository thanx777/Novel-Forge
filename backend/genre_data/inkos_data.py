"""InkOS 真实数据 — 从 https://github.com/Narcooo/inkos 源码提取
每个体裁文件来自 packages/core/genres/*.md
"""

# ============================================
# InkOS 体裁配置（中文 + 英文 共 15 个）
# ============================================
INKOS_GENRES = {
    "玄幻": {
        "id": "xuanhuan",
        "name": "玄幻",
        "chapterTypes": ["战斗章", "布局章", "过渡章", "回收章"],
        "fatigueWords": ["冷笑", "蝼蚁", "倒吸凉气", "瞳孔骤缩", "不可置信", "轰然炸裂",
                         "满场死寂", "难以置信", "仿佛", "不禁", "宛如", "竟然"],
        "numericalSystem": True,
        "powerScaling": True,
        "pacingRule": "三章内必有明确反馈：打脸、收益兑现、信息反转、地位变化",
        "satisfactionTypes": ["打脸", "升级突破", "收益兑现", "智斗碾压", "身份揭示", "底牌亮出"],
        "auditDimensions": [1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,18,19,24,25,26],
        "taboos": [
            "主角为推剧情突然仁慈、犯蠢、讲武德",
            "同质资源不写衰减默认全额结算",
            "用'暴涨''海量'跳过数值结算",
            "无铺垫的能力觉醒",
            "反派像木桩一样排队送死",
            "无铺垫强行让退场角色回归",
            "在没有铺垫的情况下突然塞入新体系、新地图、新外挂解决问题",
            "把所有章节都写成高爆裂战斗章",
        ],
        "languageRules": [
            "力量体系的量级感用体感传达，不用抽象数字",
            "同一高潮段中同一意象域的渲染不超过两轮，第三轮必须切入新信息或新动作",
            "搜尸/清点/装备段落禁止清单式列举，必须带入角色判断或取舍",
        ],
        "narrativeGuidance": "以战斗和资源获取驱动剧情。主角行为由利益驱动，杀伐果断。核心对手必须有脑子，有试探、有误判、有反扑。每个场景至少推进一项：信息、地位、资源、伤亡、仇恨、境界。",
    },
    "仙侠": {
        "id": "xianxia",
        "name": "仙侠",
        "chapterTypes": ["战斗章", "悟道章", "布局章", "过渡章", "回收章"],
        "fatigueWords": ["冷笑", "蝼蚁", "倒吸凉气", "瞳孔骤缩", "天道", "大道", "因果", "气运",
                         "仿佛", "不禁", "宛如", "竟然"],
        "numericalSystem": True,
        "powerScaling": True,
        "pacingRule": "修炼/悟道与战斗交替，每3-5章一次小突破或关键收获",
        "satisfactionTypes": ["悟道突破", "斗法碾压", "法宝收获", "身份揭示", "天劫渡过", "因果了结"],
        "auditDimensions": [1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,18,19,24,25,26],
        "taboos": [
            "主角为推剧情突然仁慈、犯蠢",
            "修为无铺垫跳跃式突破",
            "法宝凭空出现解决危机",
            "天道规则前后矛盾",
            "用'大道无形''天道感应'跳过具体修炼过程",
            "同质资源不写衰减默认全额结算",
        ],
        "languageRules": [
            "悟道场景用五感描写，不用抽象哲理灌输",
            "仙侠世界的规则感要强：因果、天劫、气运都是叙事工具",
            "人情债与道义约束是仙侠特有的驱动力",
        ],
        "narrativeGuidance": "修炼与悟道是叙事核心，但必须融入剧情而非独立说教。境界突破必须有积累过程。战斗以法术、法宝、阵法为核心，注重空间感和规模感。",
    },
    "都市": {
        "id": "urban",
        "name": "都市",
        "chapterTypes": ["商战章", "社交章", "布局章", "过渡章", "回收章"],
        "fatigueWords": ["冷笑", "不可思议", "震惊", "难以置信", "深吸一口气", "眼中闪过一丝",
                         "仿佛", "不禁", "宛如", "竟然", "核心动机", "信息边界"],
        "numericalSystem": False,
        "powerScaling": False,
        "eraResearch": True,
        "pacingRule": "每2-3章一个小回报：商业收益、人脉拓展、对手受挫、信息优势",
        "satisfactionTypes": ["商战碾压", "身份揭示", "人脉兑现", "对手打脸", "资源收割", "地位跃升"],
        "auditDimensions": [1,2,3,6,7,8,9,10,11,12,13,14,15,16,17,18,19,24,25,26],
        "taboos": [
            "无逻辑的商业奇迹（没有铺垫的暴富）",
            "反派降智配合主角表演",
            "无视现实法律和商业规则",
            "用'一个电话搞定'跳过具体操作过程",
            "女性角色沦为花瓶或奖励",
        ],
        "languageRules": [
            "人物内心独白必须口语化、直觉化，禁止商业分析术语渗入叙事",
            "法律术语必须匹配设定年代的真实语感",
            "主角的判断通过行动和对话体现，不通过上帝视角的分析段落",
        ],
        "narrativeGuidance": "以商战、社交博弈和信息差驱动剧情。时代厚重感、人情债与制度摩擦是都市文的灵魂。主角不是全知全能，必须在前5章内至少出现一次判断失误。",
    },
    "恐怖": {
        "id": "horror",
        "name": "恐怖",
        "chapterTypes": ["氛围章", "事件章", "揭示章", "过渡章", "回收章"],
        "fatigueWords": ["毛骨悚然", "不寒而栗", "浑身发冷", "头皮发麻", "鸡皮疙瘩",
                         "心跳加速", "仿佛", "不禁", "宛如", "竟然"],
        "numericalSystem": False,
        "powerScaling": False,
        "pacingRule": "氛围递进：安全感→微妙不适→确认异常→恐惧升级→高潮→喘息，循环推进",
        "satisfactionTypes": ["真相揭示", "成功逃脱", "反杀怪物", "谜团解开", "同伴获救", "规则发现"],
        "auditDimensions": [1,2,3,6,7,8,9,10,13,14,15,16,17,18,19,24,25,26],
        "taboos": [
            "恐怖源头过早完全暴露（未知才恐怖）",
            "主角无脑刚正面解决一切",
            "用打脸/升级等爽文套路替代恐怖氛围",
            "角色面对恐怖事件完全不害怕",
            "用大量血腥描写替代心理恐惧",
        ],
        "languageRules": [
            "恐怖用事实传达，不用情绪标签",
            "禁止过度解释恐怖。异常现象只需呈现，不需叙述者出来总结",
            "克制叙事：越恐怖越冷静。句子随恐惧升级而变短，但叙述者语气始终平稳",
        ],
        "narrativeGuidance": "氛围是第一生产力。用五感细节建立不安。恐怖来自对未知的恐惧，信息揭示要克制。规则感：恐怖世界有自己的规则，发现规则是生存的关键。",
    },
    "通用": {
        "id": "other",
        "name": "通用",
        "chapterTypes": ["推进章", "布局章", "过渡章", "回收章"],
        "fatigueWords": ["震惊", "不可思议", "难以置信", "深吸一口气", "仿佛", "不禁", "宛如", "竟然"],
        "numericalSystem": False,
        "powerScaling": False,
        "pacingRule": "每2-3章有一个明确的进展或反馈",
        "satisfactionTypes": ["目标达成", "困难克服", "真相揭示", "关系转变"],
        "auditDimensions": [1,2,3,6,7,8,9,10,13,14,15,16,17,18,19,24,25,26],
        "taboos": [
            "无逻辑的巧合推进剧情",
            "配角降智配合主角",
            "无铺垫的高潮",
        ],
        "languageRules": [],
        "narrativeGuidance": "根据具体题材调整叙事重心。保持因果逻辑链完整。人物行为由动机驱动，不由剧情需要驱动。",
    },
}

# ============================================
# InkOS 审计维度（33维 — 从 auditDimensions 字段反推）
# ============================================
INKOS_AUDIT_DIMENSIONS = {
    1: "人物一致性 — 角色言行是否符合人设档案",
    2: "情节因果链 — 事件前后逻辑是否成立",
    3: "OOC检测 — 角色是否出现性格突变",
    4: "战力/数值一致性 — 战力体系不崩坏，数值前后可追溯",
    5: "资源连续性 — 物资/金钱/道具不凭空出现消失",
    6: "时间线一致 — 时间推进合理，无跳跃错误",
    7: "空间/地点一致 — 场景转换有逻辑，无瞬移",
    8: "对话真实感 — 对话符合角色性格和身份",
    9: "信息泄露 — 角色不会知道未经历的事",
    10: "AI痕迹检测 — 疲劳词、重复句式、模板化段落",
    11: "伏笔管理 — 已埋伏笔是否回收，新伏笔是否合理",
    12: "章节节奏 — 起承转合、高潮分布",
    13: "Hook健康 — 章末钩子强度、上章钩子是否承接",
    14: "爽点密度 — 爽点频率是否符合题材标准",
    15: "微兑现 — 小承诺/小伏笔是否按时回收",
    16: "情感逻辑 — 角色行为动机合理，情感变化有铺垫",
    17: "世界观一致 — 设定规则不前后矛盾",
    18: "节奏灾难 — 连续多章无实质推进",
    19: "字数质量 — 水文检测、灌水段落",
    20: "数值同质衰减 — 同质资源重复吞噬是否有衰减",
    21: "法宝/道具连续性 — 装备道具不凭空出现消失",
    22: "年代/现实约束 — 法律、物价、时代背景准确",
    23: "非人POV合理性 — 非人类视角的认知局限",
    24: "语言铁律 — 无情绪标签、无过度解释、无万能副词",
    25: "叙事指导 — 场景推进、描写质量、信息密度",
    26: "体裁禁忌 — 是否违反题材特定规则",
}

# ============================================
# InkOS 疲劳词表 — 按语言/体裁汇总
# ============================================
INKOS_FATIGUE_WORDS = {
    "zh": {
        "通用": INKOS_GENRES["通用"]["fatigueWords"],
        "玄幻": ["冷笑", "蝼蚁", "倒吸凉气", "瞳孔骤缩", "不可置信", "轰然炸裂", "满场死寂"],
        "仙侠": ["冷笑", "蝼蚁", "倒吸凉气", "瞳孔骤缩", "天道", "大道", "因果", "气运"],
        "都市": ["冷笑", "不可思议", "震惊", "难以置信", "深吸一口气", "眼中闪过一丝"],
        "恐怖": ["毛骨悚然", "不寒而栗", "浑身发冷", "头皮发麻", "鸡皮疙瘩", "心跳加速"],
    },
    "en": {
        "通用": ["delve", "tapestry", "testament", "intricate", "pivotal", "vibrant",
                  "comprehensive", "nuanced", "embark", "foster", "underscore", "bolstered", "crucial"],
    },
    "universal": ["仿佛", "不禁", "宛如", "竟然", "delve", "tapestry", "vibrant", "nuanced"],
}


def get_inkos_genre(genre_name: str) -> dict:
    """根据体裁名获取 InkOS 配置"""
    for key, info in INKOS_GENRES.items():
        if info["name"] == genre_name or key == genre_name:
            return info
    return INKOS_GENRES.get("通用", {})


def get_fatigue_words(genre_name: str = "通用", lang: str = "zh") -> list:
    """获取体裁特定的疲劳词表"""
    info = get_inkos_genre(genre_name)
    words = list(info.get("fatigueWords", []))
    # 添加通用疲劳词
    for w in INKOS_FATIGUE_WORDS.get("universal", []):
        if w not in words:
            words.append(w)
    return words


def get_chapter_types(genre_name: str) -> list:
    """获取体裁特定的章节类型"""
    info = get_inkos_genre(genre_name)
    return info.get("chapterTypes", ["推进章", "布局章", "过渡章", "回收章"])


def build_inkos_reviewer_guide(genre_name: str = "通用") -> str:
    """用 InkOS 真实数据构建 Reviewer 审查指南"""
    info = get_inkos_genre(genre_name)
    dims = info.get("auditDimensions", [1,2,3,6,7,8,9,10,24,25,26])
    dim_names = []
    for d in dims[:12]:  # 最多12个维度
        name = INKOS_AUDIT_DIMENSIONS.get(d, f"维度{d}")
        dim_names.append(f"{d}. {name}")

    taboos = info.get("taboos", [])
    pacing = info.get("pacingRule", "")
    fatigue = info.get("fatigueWords", [])[:8]

    parts = [f"\n【InkOS {info['name']}体裁审查指南】"]
    parts.append(f"节奏规则：{pacing}")
    parts.append(f"审查维度：")
    parts.extend(f"  {d}" for d in dim_names)
    if taboos:
        parts.append(f"题材禁忌：{'；'.join(taboos[:4])}")
    if fatigue:
        parts.append(f"疲劳词（禁止滥用）：{'、'.join(fatigue)}")

    return "\n".join(parts)


def build_inkos_writer_guide(genre_name: str = "通用") -> str:
    """用 InkOS 真实数据构建 Worker 写作指南"""
    info = get_inkos_genre(genre_name)
    parts = [f"\n【InkOS {info['name']}写作规范】"]

    # 章节类型
    ctypes = info.get("chapterTypes", [])
    if ctypes:
        parts.append(f"章节类型：{' / '.join(ctypes)}")

    # 节奏
    parts.append(f"节奏规则：{info.get('pacingRule', '')}")

    # 爽点类型
    sat = info.get("satisfactionTypes", [])
    if sat:
        parts.append(f"爽点类型：{'、'.join(sat)}")

    # 语言规则
    rules = info.get("languageRules", [])
    if rules:
        parts.append("语言铁律：")
        for r in rules[:3]:
            parts.append(f"  - {r}")

    # 疲劳词
    fatigue = info.get("fatigueWords", [])[:6]
    if fatigue:
        parts.append(f"禁用词汇：{'、'.join(fatigue)}")

    # 叙事指导
    guidance = info.get("narrativeGuidance", "")
    if guidance:
        parts.append(f"叙事指导：{guidance}")

    return "\n".join(parts)
