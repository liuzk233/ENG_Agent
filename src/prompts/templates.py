# 文件路径: src/prompts/templates.py
"""
提示词模板统一管理中心

本模块集中管理所有 LLM 提示词，便于：
1. 版本控制与 A/B 测试
2. 快速迭代优化
3. 保持代码与提示词解耦
"""

# ============================================================
# Writer Agent 提示词
# ============================================================

WRITER_SYSTEM_PROMPT = """
你是一个极其专业的英语教育专家，擅长编写特定风格的英语短文。
【绝对规则】：
1. 你的文章必须严格只使用初中及高中基础英语词汇。
2. 绝对不能使用超出常规考试大纲的生僻词、复杂词汇。
3. 遇到需要表达复杂概念时，请使用基础词汇进行解释说明（paraphrase）。
"""

# Few-Shot 黄金范文：融入常见的倒装句、强调句、从句等考场高分句式
FEW_SHOT_EXAMPLES = """
【优质范例学习】
在正式创作前，请仔细体会以下两篇满分范文的句式结构与用词深度：

范例 1 (风格: 议论文 Argumentative)：
"It is universally acknowledged that technology plays an increasingly significant role in our daily lives. Not only does it bring convenience, but it also broadens our horizons. However, every coin has two sides. Only by utilizing it reasonably can we truly benefit from it."

范例 2 (风格: 科幻 Sci-Fi)：
"In the distant future, humanity's desire to explore the uncharted galaxy became unprecedentedly intense. Little did they know that the spaceship they built would face such immense danger. Suddenly, a mysterious light flashed outside the window."
-------------------------------------------
"""


# ============================================================
# Story Extraction 提示词
# ============================================================

STORY_EXTRACTION_PROMPT = """
你是一个故事分析专家。请分析以下故事章节，提取关键信息。

【章节内容】
{chapter_text}

请严格输出以下 JSON 格式（不要包含任何其他文字）：
{{
    "new_characters": [
        {{
            "name": "角色名",
            "role": "protagonist/antagonist/supporting",
            "description": "一句话描述（英文）"
        }}
    ],
    "new_settings": [
        {{
            "name": "地点名",
            "type": "location/building/region",
            "description": "一句话描述（英文）"
        }}
    ],
    "new_items": [
        {{
            "name": "物品名",
            "description": "一句话描述（英文）"
        }}
    ],
    "key_events": ["事件1", "事件2"],
    "chapter_summary": "50词以内的章节摘要（英文）"
}}

【重要规则】：
1. 只提取首次出现的新元素，已存在的不要重复
2. 角色名必须是专有名词（首字母大写）
3. 如果没有新角色/地点/物品，对应数组为空 []
4. 描述必须使用英文
"""


def get_story_extraction_prompt(chapter_text: str) -> str:
    """生成故事元素提取提示词"""
    return STORY_EXTRACTION_PROMPT.format(chapter_text=chapter_text)


def get_drafting_prompt(
    style: str,
    words_str: str,
    reference_texts: list = None,
    story_bible: dict = None,
    previous_summary: str = None,
    episode_outline: str = None
) -> str:
    """
    生成初稿的用户提示词（融合 Few-Shot 与 RAG 参考语料）

    Args:
        style: 目标风格（如 "exam_paper", "科幻"）
        words_str: 目标单词字符串（逗号分隔）
        reference_texts: RAG 检索到的参考语料列表
        story_bible: 故事设定（包含角色、场景、物品等）
        previous_summary: 前情提要
        episode_outline: 当前章节大纲

    Returns:
        str: 完整的用户提示词
    """
    prompt = FEW_SHOT_EXAMPLES

    # 注入故事设定
    if story_bible:
        prompt += "\n【故事世界设定】\n"

        # 角色信息
        characters = story_bible.get("characters", [])
        if characters:
            prompt += "已有角色:\n"
            for char in characters:
                prompt += f"  - {char.get('name', 'Unknown')} ({char.get('role', 'supporting')}): {char.get('description', '')}\n"

        # 场景信息
        settings = story_bible.get("settings", [])
        if settings:
            prompt += "已有场景:\n"
            for setting in settings:
                prompt += f"  - {setting.get('name', 'Unknown')}: {setting.get('description', '')}\n"

        # 物品信息
        items = story_bible.get("items", [])
        if items:
            prompt += "关键物品:\n"
            for item in items:
                prompt += f"  - {item.get('name', 'Unknown')}: {item.get('description', '')}\n"

        if characters or settings or items:
            prompt += "⚠️ 请保持与以上设定的一致性，新角色/场景可以引入但不要与已有设定冲突。\n"

    # 注入当前章节大纲（关键：确保故事连贯性）
    if episode_outline:
        prompt += f"\n【本章大纲】\n{episode_outline}\n"
        prompt += "⚠️ 必须严格按照以上大纲编写本章内容，确保剧情走向符合规划。\n"

    # 注入前情提要
    if previous_summary:
        prompt += f"\n【前情提要】\n{previous_summary}\n"
        prompt += "请确保新章节与前面的情节自然衔接。\n"

    # 动态注入 RAG 检索到的参考语料
    if reference_texts:
        ref_section = "\n【风格参考语料】\n"
        ref_section += "以下是目标风格的参考文本，请仔细学习其句式、用词和语调：\n\n"

        for i, text in enumerate(reference_texts[:3], 1):
            ref_section += f"参考 {i}:\n{text}\n\n"

        ref_section += "⚠️ 重要：你的文章必须模仿以上参考文本的风格特征，但不要直接复制内容！\n"
        prompt += ref_section

    prompt += (
        f"【你的任务】\n"
        f"请用【{style}】风格写一篇英语短文（约 200-300 词）。\n"
        f"文章中必须自然地包含以下单词：[{words_str}]。\n"
        f"请直接输出文章主体，不要包含任何多余的解释、标题或问候语。"
    )
    return prompt


def get_refining_prompt(style: str, words_str: str, feedback: str) -> str:
    """
    生成重写提示词（包含 Reviewer 的报错反馈）

    Args:
        style: 目标风格
        words_str: 目标单词字符串
        feedback: Reviewer 给出的报错信息

    Returns:
        str: 完整的重写提示词
    """
    return (
        f"你之前生成了一篇【{style}】风格的文章，但质检员发现了严重的问题：\n\n"
        f"【质检反馈】：\n{feedback}\n\n"
        f"请根据上述反馈，彻底重写整篇文章。\n"
        f"任务要求：\n"
        f"1. 仍然必须包含目标单词：[{words_str}]。\n"
        f"2. 【绝对要求】：必须将质检反馈中指出的超纲词汇，替换为极其简单的基础词汇！\n"
        f"请直接输出修改后的完整文章，不要包含其他废话。"
    )


# ============================================================
# Reviewer Agent 提示词
# ============================================================

REVIEWER_SYSTEM_PROMPT = """
你是一个精通英语词汇学与中国大陆英语教育体系的 NLP 专家。
你的任务是对疑似超纲的英语单词进行多维度分析。
请严格输出 JSON 格式数据，绝对不要包含任何其他说明文字或 Markdown 标记。
"""


def get_smart_filter_prompt(words_list: list) -> str:
    """
    生成 LLM 智能过滤提示词（用于判断嫌疑词是否为简单词）

    Args:
        words_list: 疑似超纲单词列表

    Returns:
        str: 智能分析提示词
    """
    return f"""
请分析以下疑似超纲的英文单词列表：{words_list}

你需要对每个单词进行两个维度的判断：
1. "lemma": 给出它在词典中最基础的形态（如剥离副词后缀、过去式，或将英式拼写统一为美式/英式常用词根）。
2. "is_simple": 判断该词（或其基础形态）是否属于中国大陆初中、高中水平的常见基础词汇。如果是，则为 true；如果是生僻词、高级词汇，则为 false。

请严格输出一段合法的 JSON，格式如下例所示：
{{
    "slowly": {{"lemma": "slow", "is_simple": true}},
    "checked": {{"lemma": "check", "is_simple": true}},
    "colour": {{"lemma": "color", "is_simple": true}},
    "extraterrestrial": {{"lemma": "extraterrestrial", "is_simple": false}}
}}
"""


def get_violation_feedback(out_of_syllabus_words: set) -> str:
    """
    生成超纲词汇违规反馈（供 Writer 重写时参考）

    Args:
        out_of_syllabus_words: 超纲词汇集合

    Returns:
        str: 格式化的反馈字符串
    """
    bad_words_str = ", ".join(out_of_syllabus_words)
    return (
        f"你的文章中包含了以下 {len(out_of_syllabus_words)} 个大纲外的高级词汇或生僻词：\n"
        f"[{bad_words_str}]\n"
        f"请立刻找到并删除这些词，用最基础的词汇重写表达！"
    )


# ============================================================
# Planner Agent 提示词
# ============================================================

PLANNER_SYSTEM_PROMPT = """
你是一个专业的英语教育故事编剧，擅长规划多集连续故事大纲。

【绝对规则】：
1. 每集大纲必须清晰描述剧情走向。
2. 确保故事连贯性，每集之间有自然的过渡。
3. 目标词汇需要在各集中均匀分布。
4. 使用简洁的英语描述每集剧情概要。
"""


def get_planning_prompt(
    total_episodes: int,
    target_words: list,
    style: str,
    story_bible: dict = None,
) -> str:
    """
    生成大纲规划提示词（支持故事设定注入）

    Args:
        total_episodes: 总集数
        target_words: 目标词汇列表
        style: 风格设定
        story_bible: 故事设定（包含角色、场景、物品等）

    Returns:
        str: 规划提示词
    """
    words_str = ", ".join(target_words)

    prompt = f"请为一篇{style}风格的多集连续故事生成 {total_episodes} 集极简大纲。\n\n"
    prompt += f"【目标词汇】：[{words_str}]\n这些词汇需要在故事中自然出现。\n\n"

    # 注入已有设定（续写时可能已有角色）
    if story_bible:
        characters = story_bible.get("characters", [])
        if characters:
            prompt += "【已有角色】：\n"
            for char in characters[:3]:
                prompt += f"  - {char.get('name', 'Unknown')}: {char.get('description', '')}\n"
            prompt += "请保持角色设定的一致性。\n\n"

        settings = story_bible.get("settings", [])
        if settings:
            prompt += "【已有场景】：\n"
            for setting in settings[:3]:
                prompt += f"  - {setting.get('name', 'Unknown')}\n"
            prompt += "可以沿用或合理扩展场景。\n\n"

        plot_points = story_bible.get("plot_points", [])
        if plot_points:
            prompt += "【已发生剧情】：\n"
            for pp in plot_points[-3:]:
                prompt += f"  - 第{pp.get('episode', '?')}集: {pp.get('summary', '')}\n"
            prompt += "新剧情应与前文自然衔接。\n\n"

    prompt += """【输出格式】（每行一集，简洁英文描述）：
Episode 1: [剧情概要]
Episode 2: [剧情概要]
...

【要求】：
1. 故事有完整的起承转合
2. 每集剧情相对独立但前后呼应
3. 每集概要在 50 词以内
"""
    return prompt


def get_summary_prompt(episode_text: str) -> str:
    """
    生成前情提要提示词

    Args:
        episode_text: 本集完整文本

    Returns:
        str: 摘要提示词
    """
    return f"""
请将以下故事内容压缩为一段简洁的"前情提要"（50-100词）：

{episode_text}

【要求】：
1. 保留关键事件和人物
2. 突出重要转折点
3. 使用简洁的英语
"""


# ============================================================
# 导出清单（便于外部模块按需导入）
# ============================================================

__all__ = [
    # Writer prompts
    "WRITER_SYSTEM_PROMPT",
    "FEW_SHOT_EXAMPLES",
    "get_drafting_prompt",
    "get_refining_prompt",
    # Story extraction prompts
    "STORY_EXTRACTION_PROMPT",
    "get_story_extraction_prompt",
    # Reviewer prompts
    "REVIEWER_SYSTEM_PROMPT",
    "get_smart_filter_prompt",
    "get_violation_feedback",
    # Planner prompts
    "PLANNER_SYSTEM_PROMPT",
    "get_planning_prompt",
    "get_summary_prompt",
]
