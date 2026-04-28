"""
故事元素提取 Agent

负责从章节文本中提取：
1. 角色信息（characters）
2. 场景设定（settings）
3. 关键物品（items）
4. 情节要点（plot_points）
"""

import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def extract_story_elements(
    llm_client,
    chapter_text: str,
    existing_story_bible: dict = None
) -> Dict[str, Any]:
    """
    从章节文本中提取故事元素

    Args:
        llm_client: LLM 客户端
        chapter_text: 章节文本
        existing_story_bible: 现有的 story_bible（用于去重）

    Returns:
        提取结果字典
    """
    from src.prompts.templates import get_story_extraction_prompt

    # 获取已存在的元素名称（用于去重）
    existing_names = {
        "characters": set(),
        "settings": set(),
        "items": set()
    }
    if existing_story_bible:
        for char in existing_story_bible.get("characters", []):
            existing_names["characters"].add(char.get("name", "").lower())
        for setting in existing_story_bible.get("settings", []):
            existing_names["settings"].add(setting.get("name", "").lower())
        for item in existing_story_bible.get("items", []):
            existing_names["items"].add(item.get("name", "").lower())

    # 调用 LLM 提取
    prompt = get_story_extraction_prompt(chapter_text)
    response = llm_client.chat(
        system_prompt="你是一个专业的文学分析助手，擅长从文本中提取结构化信息。",
        user_prompt=prompt,
        temperature=0.3  # 低温度保证输出稳定
    )

    # 解析 JSON 响应
    try:
        # 清理可能的 markdown 代码块标记
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]

        result = json.loads(response.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"JSON 解析失败: {e}, 原始响应: {response[:200]}")
        result = {
            "new_characters": [],
            "new_settings": [],
            "new_items": [],
            "key_events": [],
            "chapter_summary": ""
        }

    # 去重：移除已存在的元素
    for key in ["new_characters", "new_settings", "new_items"]:
        category = key.replace("new_", "")
        result[key] = [
            item for item in result.get(key, [])
            if item.get("name", "").lower() not in existing_names[category]
        ]

    return result


def update_story_bible(
    story_bible: dict,
    extraction: dict,
    episode: int
) -> dict:
    """
    更新 story_bible

    Args:
        story_bible: 现有的 story_bible
        extraction: 提取结果
        episode: 当前章节号

    Returns:
        更新后的 story_bible
    """
    if story_bible is None:
        story_bible = {
            "characters": [],
            "settings": [],
            "items": [],
            "plot_points": [],
            "outline": [],
        }

    # 确保 story_bible 有必要的字段
    story_bible.setdefault("characters", [])
    story_bible.setdefault("settings", [])
    story_bible.setdefault("items", [])
    story_bible.setdefault("plot_points", [])
    story_bible.setdefault("outline", [])  # 保留大纲字段

    # 添加首次出场信息
    for char in extraction.get("new_characters", []):
        char["first_appearance"] = episode
        story_bible["characters"].append(char)

    for setting in extraction.get("new_settings", []):
        setting["first_appearance"] = episode
        story_bible["settings"].append(setting)

    for item in extraction.get("new_items", []):
        item["first_appearance"] = episode
        story_bible["items"].append(item)

    # 添加情节要点
    plot_point = {
        "episode": episode,
        "summary": extraction.get("chapter_summary", ""),
        "key_events": extraction.get("key_events", [])
    }
    story_bible["plot_points"].append(plot_point)

    return story_bible


def get_previous_summary(story_bible: dict, max_episodes: int = 1) -> str:
    """
    从 story_bible 生成前情提要

    Args:
        story_bible: 故事设定
        max_episodes: 最多包含多少集的摘要

    Returns:
        前情提要字符串
    """
    plot_points = story_bible.get("plot_points", [])
    if not plot_points:
        return ""

    # 取最近 max_episodes 集的摘要
    recent_points = plot_points[-max_episodes:]
    summaries = [p.get("summary", "") for p in recent_points if p.get("summary")]

    if not summaries:
        return ""

    return " ".join(summaries)
