"""体裁配置档案 (Genre Profiles)
来源: webnovel-writer/references/csv/裁决规则.csv + 题材与调性推理.csv + templates/genres/*.md
"""

# ============================================
# 体裁匹配标签
# ============================================
GENRE_TAGS = {
    "玄幻": ["玄幻", "修真", "修仙", "仙侠", "异界", "异世", "穿越异界", "东方玄幻", "传统玄幻"],
    "仙侠": ["仙侠", "修仙", "渡劫", "宗门", "飞升"],
    "都市": ["都市", "现代", "校花", "总裁", "神豪", "战神", "重生都市", "异能", "都市日常"],
    "系统": ["系统", "签到", "面板", "任务流", "系统流", "无限流"],
    "历史": ["历史", "权谋", "宫斗", "争霸", "科举", "谍战", "架空", "古代", "宅斗", "官场"],
    "科幻": ["科幻", "星际", "机甲", "赛博", "末世", "废土", "AI", "未来", "丧尸"],
    "悬疑": ["悬疑", "推理", "灵异", "恐怖", "惊悚", "侦探", "密室", "规则怪谈", "克苏鲁"],
    "言情": ["言情", "女频", "甜宠", "虐恋", "重生", "总裁文", "宅斗", "宫斗", "追妻"],
    "电竞": ["电竞", "游戏", "网游", "全息", "虚拟现实", "直播", "体育"],
    "武侠": ["武侠", "高武", "低武", "江湖", "都市高武"],
    "奇幻": ["奇幻", "西幻", "魔法", "剑与魔法", "龙与地下城"],
    "古言": ["古言", "宫斗宅斗", "古风世情", "古代言情"],
    "现言": ["现言", "甜宠", "豪门总裁", "娱乐圈", "豪门", "追妻", "火葬场"],
    "幻言": ["幻言", "玄幻言情", "仙侠言情", "宿命"],
    "年代": ["年代", "民国", "年代文", "四合院", "工厂", "票证"],
    "种田": ["种田", "经营", "基建", "种田文"],
    "快穿": ["快穿", "攻略系统", "小世界", "任务"],
    "衍生": ["衍生", "同人", "二创", "原作", "OOC"],
}

# ============================================
# 裁决规则 — 直接从 webnovel-writer CSV 提取
# ============================================
VERDICT_RULES = {
    "玄幻": {
        "keywords": GENRE_TAGS["玄幻"],
        "style_priority": ["热血冲突", "冷硬算计", "史诗铺陈"],
        "coolpoint_priority": ["等级压制", "逆境翻盘", "底牌揭晓"],
        "rhythm_strategy": "快推强爆 小境界短写 大冲突长写",
        "poison_weight": ["战力崩盘", "圣母病", "爽点软收尾"],
        "conflict_verdict": "爽点与节奏 > 金手指与设定 > 场景写法",
        "anti_patterns": ["战力体系混乱", "升级无代价", "打脸没有补刀"],
    },
    "仙侠": {
        "keywords": GENRE_TAGS["仙侠"],
        "style_priority": ["冷硬算计", "超然物外", "热血冲突"],
        "coolpoint_priority": ["境界碾压", "底牌揭晓", "因果兑现"],
        "rhythm_strategy": "慢蓄快爆 修炼段精简 斗法段拉满",
        "poison_weight": ["修炼水字数", "圣母病", "逻辑断裂"],
        "conflict_verdict": "爽点与节奏 > 桥段套路 > 场景写法",
        "anti_patterns": ["修炼变流水账", "境界突破无代价", "感悟靠顿悟标签"],
    },
    "科幻末世": {
        "keywords": GENRE_TAGS["科幻"],
        "style_priority": ["高压克制", "冷硬算计", "绝境反击"],
        "coolpoint_priority": ["绝境生存", "资源碾压", "智谋博弈"],
        "rhythm_strategy": "紧凑推进 危机不断 喘息极短",
        "poison_weight": ["主角无敌", "科技无代价", "末世无压迫感"],
        "conflict_verdict": "场景写法 > 爽点与节奏 > 写作技法",
        "anti_patterns": ["末世没有生存压力", "科技万能", "角色行为无逻辑"],
    },
    "都市日常": {
        "keywords": GENRE_TAGS["都市"],
        "style_priority": ["日常轻松", "温情治愈", "微妙张力"],
        "coolpoint_priority": ["情感共鸣", "生活逆袭", "社交碾压"],
        "rhythm_strategy": "慢节奏 情感铺垫长 冲突柔和",
        "poison_weight": ["假大空说教", "情绪标签化", "逻辑断裂"],
        "conflict_verdict": "写作技法 > 人设与关系 > 场景写法",
        "anti_patterns": ["情感靠标签", "日常无冲突", "角色千人一面"],
    },
    "都市高武": {
        "keywords": ["高武", "都市异能", "都市高武"],
        "style_priority": ["热血冲突", "冷硬算计", "力量美学"],
        "coolpoint_priority": ["实力碾压", "以弱胜强", "排名跃升"],
        "rhythm_strategy": "快节奏 战斗密集 过渡极短",
        "poison_weight": ["战力崩盘", "圣母病", "无脑开挂"],
        "conflict_verdict": "爽点与节奏 > 场景写法 > 桥段套路",
        "anti_patterns": ["战力体系自相矛盾", "升级无代价", "打斗无策略"],
    },
    "历史古代": {
        "keywords": GENRE_TAGS["历史"],
        "style_priority": ["沉稳厚重", "权谋算计", "家国情怀"],
        "coolpoint_priority": ["权谋碾压", "历史转折", "身份反转"],
        "rhythm_strategy": "慢铺快收 权谋段拉长 战争段紧凑",
        "poison_weight": ["现代价值观强加古人", "逻辑断裂", "历史常识错误"],
        "conflict_verdict": "写作技法 > 人设与关系 > 场景写法",
        "anti_patterns": ["用现代口语写古代", "权谋无逻辑", "历史事件随意篡改"],
    },
    "悬疑": {
        "keywords": GENRE_TAGS["悬疑"],
        "style_priority": ["高压克制", "信息控制", "冷硬推理"],
        "coolpoint_priority": ["真相揭示", "规则反用", "误导反转"],
        "rhythm_strategy": "慢给线索 快给危机 揭示分层",
        "poison_weight": ["凭空新证据", "谜底提前透光", "恐惧无代价"],
        "conflict_verdict": "场景写法 > 写作技法 > 桥段套路",
        "anti_patterns": ["线索不公平", "侦探神启", "规则没有惩罚"],
    },
    "游戏电竞": {
        "keywords": GENRE_TAGS["电竞"],
        "style_priority": ["竞技张力", "团队协作", "热血爆发"],
        "coolpoint_priority": ["逆风翻盘", "技术碾压", "团队配合"],
        "rhythm_strategy": "赛前短铺 比赛强推 赛后复盘压短",
        "poison_weight": ["规则不清", "胜负靠口号", "技术描写空泛"],
        "conflict_verdict": "场景写法 > 人设与关系 > 爽点与节奏",
        "anti_patterns": ["比赛机制含糊", "团队只喊口号", "胜负没有策略因果"],
    },
    "古言": {
        "keywords": GENRE_TAGS["古言"],
        "style_priority": ["礼法压迫", "权谋博弈", "情感暗流"],
        "coolpoint_priority": ["身份反转", "名声反击", "权谋碾压"],
        "rhythm_strategy": "慢铺证据 快收反击 礼法后果不断线",
        "poison_weight": ["现代口语", "权谋无证据", "礼法失效"],
        "conflict_verdict": "人设与关系 > 写作技法 > 场景写法",
        "anti_patterns": ["现代价值观硬套", "宅斗无证据", "身份礼法无约束"],
    },
    "现言": {
        "keywords": GENRE_TAGS["现言"],
        "style_priority": ["情感张力", "现实质感", "轻喜互动"],
        "coolpoint_priority": ["关系推进", "身份揭露", "情绪反转"],
        "rhythm_strategy": "情感铺垫密集 冲突短促 关系变化要可见",
        "poison_weight": ["工业糖精", "误会硬拖", "角色行为悬浮"],
        "conflict_verdict": "人设与关系 > 写作技法 > 场景写法",
        "anti_patterns": ["只写心跳脸红", "霸总工具人化", "现实逻辑悬浮"],
    },
    "幻言": {
        "keywords": GENRE_TAGS["幻言"],
        "style_priority": ["情感抉择", "力量代价", "宿命张力"],
        "coolpoint_priority": ["情感牺牲", "境界突破", "身份揭示"],
        "rhythm_strategy": "感情线与力量线同步推进 虐点必须改变立场",
        "poison_weight": ["恋爱主线脱节", "宿命万能", "女主被代打"],
        "conflict_verdict": "人设与关系 > 金手指与设定 > 爽点与节奏",
        "anti_patterns": ["感情和主线两张皮", "宿命替代行动", "成长被男主代打"],
    },
    "年代": {
        "keywords": GENRE_TAGS["年代"],
        "style_priority": ["时代质感", "情感克制", "生存选择"],
        "coolpoint_priority": ["时代冲击", "关系守护", "事业积累"],
        "rhythm_strategy": "日常细节慢铺 关键事件快收 时代后果必须落地",
        "poison_weight": ["时代背景装饰化", "现代价值观硬套", "物质条件失真"],
        "conflict_verdict": "场景写法 > 人设与关系 > 写作技法",
        "anti_patterns": ["年份只是标签", "消费观现代化", "时代压力不影响选择"],
    },
    "种田": {
        "keywords": GENRE_TAGS["种田"],
        "style_priority": ["积累满足", "共同体扩张", "低烈度冲突"],
        "coolpoint_priority": ["成果展示", "资源解锁", "关系互惠"],
        "rhythm_strategy": "小目标快兑现 大目标慢积累 阶段成果要可见",
        "poison_weight": ["流水账", "没有资源瓶颈", "成果不可见"],
        "conflict_verdict": "场景写法 > 金手指与设定 > 爽点与节奏",
        "anti_patterns": ["经营只记账", "发财无阻力", "共同体没有变化"],
    },
    "快穿": {
        "keywords": GENRE_TAGS["快穿"],
        "style_priority": ["任务约束", "情感选择", "主线回收"],
        "coolpoint_priority": ["身份反转", "任务完成", "记忆揭示"],
        "rhythm_strategy": "世界开局快立目标 中段加限制 结尾回收主线",
        "poison_weight": ["小世界重复", "系统代替思考", "通关无主线价值"],
        "conflict_verdict": "人设与关系 > 金手指与设定 > 桥段套路",
        "anti_patterns": ["每个世界同模板", "系统直接给答案", "攻略对象工具人化"],
    },
    "奇幻": {
        "keywords": GENRE_TAGS["奇幻"],
        "style_priority": ["史诗感", "冷硬算计", "日常轻松"],
        "coolpoint_priority": ["实力碾压", "逆境翻盘", "智谋博弈"],
        "rhythm_strategy": "快推慢收 对峙段拉长 过渡段压短",
        "poison_weight": ["圣母病", "情绪标签化", "逻辑断裂"],
        "conflict_verdict": "爽点与节奏 > 场景写法 > 写作技法",
        "anti_patterns": ["情绪标签化", "角色行为无逻辑", "战斗无代价"],
    },
}

# ============================================
# 体裁 profile — 合并裁决规则 + 模板详述
# ============================================
def _make_profile(verdict_key: str, style_notes: str = "", taboos: list = None) -> dict:
    """从裁决规则构建完整 profile"""
    r = VERDICT_RULES.get(verdict_key, VERDICT_RULES["玄幻"])
    profile = {
        "tags": r["keywords"],
        "style_priority": r["style_priority"],
        "coolpoint_priority": r["coolpoint_priority"],
        "rhythm_strategy": r["rhythm_strategy"],
        "poison_weight": r["poison_weight"],
        "conflict_verdict": r["conflict_verdict"],
        "anti_patterns": r["anti_patterns"],
        "style_notes": style_notes,
        "taboos": taboos or r["anti_patterns"],
    }
    # 为向后兼容提供简化访问
    profile["hook_config"] = {
        "preferred_types": _map_hooks(r.get("style_priority", [])),
        "strength_baseline": "strong" if "热血" in r["rhythm_strategy"] or "快推" in r["rhythm_strategy"] else "medium",
        "chapter_end_required": True,
        "transition_allowance": 2 if "快" in r["rhythm_strategy"] else 3,
    }
    profile["coolpoint_config"] = {
        "preferred_patterns": [p for p in r["coolpoint_priority"] if not p.startswith("爽点")],
        "density_per_chapter": "high" if "快" in r["rhythm_strategy"] else "medium",
        "combo_interval": 5 if "快" in r["rhythm_strategy"] else 10,
        "milestone_interval": 15 if "快" in r["rhythm_strategy"] else 25,
    }
    profile["micropayoff_config"] = {
        "preferred_types": ["信息兑现", "能力兑现", "认可兑现"],
        "min_per_chapter": 2 if "high" in profile["coolpoint_config"]["density_per_chapter"] else 1,
        "transition_min": 1,
    }
    profile["pacing_config"] = {
        "stagnation_threshold": 2 if "紧凑" in r["rhythm_strategy"] or "快" in r["rhythm_strategy"] else 3,
        "strand_quest_max": 5,
        "strand_fire_gap_max": 10,
        "transition_max_consecutive": 1 if "紧凑" in r["rhythm_strategy"] else 2,
    }
    return profile


def _map_hooks(styles: list) -> list:
    """风格优先级 → 推荐钩子类型"""
    mapping = {
        "热血": "危机钩",
        "冷硬": "悬念钩",
        "史诗": "渴望钩",
        "情感": "情绪钩",
        "高压": "危机钩",
        "日常": "情绪钩",
        "竞技": "选择钩",
        "礼法": "选择钩",
        "时代": "情绪钩",
        "积累": "渴望钩",
        "任务": "渴望钩",
    }
    hooks = []
    for s in styles:
        for k, v in mapping.items():
            if k in s and v not in hooks:
                hooks.append(v)
    if not hooks:
        hooks = ["危机钩", "渴望钩"]
    return hooks[:3]


# ============================================
# 构建完整 GENRE_PROFILES
# ============================================
GENRE_PROFILES = {
    "玄幻/仙侠": _make_profile("玄幻", style_notes=(
        "修炼体系分层清晰；每15章一个里程碑胜利；"
        "三章一爽点，五章一高潮；战力体系必须前后一致。"
    )),
    "都市/现代": _make_profile("都市日常", style_notes=(
        "现代背景+超凡力量；身份揭晓节奏：铺垫→冲突→反转→打脸；"
        "每章至少一个小爽点；都市异能需解释遮蔽机制。"
    )),
    "都市高武": _make_profile("都市高武", style_notes=(
        "快节奏战斗密集；实力碾压为主旋律；打斗必须有策略有代价。"
    )),
    "科幻/末世": _make_profile("科幻末世", style_notes=(
        "设定先行，冲突驱动；科技树有逻辑递进；末世需管理资源稀缺性。"
    )),
    "历史/权谋": _make_profile("历史古代", style_notes=(
        "谋略先行，武力兜底；大事件配小伏笔；每卷一个核心冲突；等级制度需明确。"
    )),
    "悬疑/灵异": _make_profile("悬疑", style_notes=(
        "草蛇灰线，伏笔千里；线索密度每章1-2个；大反转每卷1-2次；"
        "恐怖来源于未知和规则，不只是血腥堆砌。"
    )),
    "言情/现言": _make_profile("现言", style_notes=(
        "感情线为主；甜虐交替，每5-10章一个感情节点；"
        "男女主各有独立事业线；感情发展有逻辑有波折。"
    )),
    "古言/宫斗": _make_profile("古言", style_notes=(
        "礼法压迫+权谋博弈；后宫/宅院等级制度需明确；人物关系网复杂但清晰。"
    )),
    "种田/经营": _make_profile("种田", style_notes=(
        "积累满足感；小目标快兑现大目标慢积累；资源瓶颈必须真实。"
    )),
    "游戏/电竞": _make_profile("游戏电竞", style_notes=(
        "比赛/副本→升级→新挑战循环；每章给1个可验证决策点与后果。"
    )),
    "幻言/仙侠言情": _make_profile("幻言", style_notes=(
        "感情线与力量线同步推进；虐点必须改变立场；女主的成长不能由男主代打。"
    )),
    "年代": _make_profile("年代", style_notes=(
        "时代质感必须真实；物质条件不能失真；时代压力要影响角色选择。"
    )),
    "快穿": _make_profile("快穿", style_notes=(
        "每个世界开局快立目标；中段加限制；结尾回收主线；避免模板化重复。"
    )),
    "奇幻": _make_profile("奇幻", style_notes=(
        "史诗感营造；对峙段拉长过渡段压短；战斗必须有真实代价。"
    )),
}

# 默认通用
DEFAULT_GENRE = _make_profile("玄幻")  # 以玄幻为基底的通用模板
DEFAULT_GENRE["name"] = "通用"
DEFAULT_GENRE["tags"] = []
DEFAULT_GENRE["style_notes"] = "通用网文写作规范：三章一爽点，五章一高潮。"
