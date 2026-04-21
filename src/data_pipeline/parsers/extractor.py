# =====================================================================
# 模块：异构词汇大纲解析器 (Heterogeneous Syllabus Parser)，离线
# =====================================================================
# 【业务痛点】
# 来源广泛的单词大纲（中考、高考、四六级、考研）存在极高的"格式非标准性"：
#   1. 文件类型多变：可能是 Excel、PDF、TXT 等完全不同的载体。
#   2. 内部结构混乱：即使同为 Excel，目标单词所在的列、是否包含表头、是否有脏数据等均不可预测。
#
# 【当前方案】
# 提供 XLS 解析 + JSON 导出功能，支持词汇元数据扩展。
#
# 【数据格式】
# 输出 JSON 结构：
# {
#   "version": "1.0",
#   "source": "考研英语大纲",
#   "word_count": 5500,
#   "words": ["a", "abandon", ...]
# }
#
# 【未来演进方向】
# 计划引入 Agent 架构（如 OpenClaw 或其他具备 Code Interpreter 能力的智能体）。
# 利用大模型的逻辑推理能力，先"观察"文件样本，动态识别单词所在的具体位置，
# 从而彻底消除 if/else 规则的硬编码，实现真正的高泛化文档解析。
# =====================================================================

import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

import pandas as pd


# ============================================================
# XLS 解析
# ============================================================

def load_syllabus_xls(file_path: str) -> set:
    """
    从 XLS 文件加载大纲词汇到 set。

    处理特殊符号：/（切割）、\xa0（不间断空格）

    Args:
        file_path: XLS 文件路径

    Returns:
        词汇集合（小写、去重）
    """
    try:
        df = pd.read_excel(file_path, header=None, usecols=[0])
        syllabus_set = set()

        for item in df[0].dropna().astype(str):
            # 1. 转小写，去除两端空白，并将 \xa0 替换为普通空格
            clean_item = item.strip().lower().replace('\xa0', ' ')

            # 2. 针对 / 进行切割 (如 'a/an' -> ['a', 'an'])
            syllabus_set.update(word.strip() for word in clean_item.split('/') if word.strip())

        return syllabus_set

    except Exception as e:
        print(f"[ERROR] Failed to load syllabus: {e}")
        return set()


# ============================================================
# JSON 导出/加载
# ============================================================

def save_syllabus_json(
    words: set,
    output_path: str,
    source: str = "未知来源",
    version: str = "1.0"
) -> bool:
    """
    将词汇集合保存为 JSON 格式。

    Args:
        words: 词汇集合
        output_path: 输出文件路径
        source: 词汇来源（如"考研英语大纲"）
        version: 数据版本

    Returns:
        是否保存成功
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 构建数据结构
        data = {
            "version": version,
            "source": source,
            "created_at": datetime.now().isoformat(),
            "word_count": len(words),
            "words": sorted(list(words))  # 排序便于 diff 和查看
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] Syllabus saved: {output_path}")
        print(f"     Source: {source}")
        print(f"     Words: {len(words)}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to save: {e}")
        return False


def load_syllabus_json(file_path: str) -> set:
    """
    从 JSON 文件加载词汇集合。

    Args:
        file_path: JSON 文件路径

    Returns:
        词汇集合
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        words = set(data.get("words", []))
        print(f"[OK] Loaded {len(words)} words from JSON (source: {data.get('source', 'unknown')})")
        return words

    except FileNotFoundError:
        print(f"[ERROR] File not found: {file_path}")
        return set()
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse failed: {e}")
        return set()
    except Exception as e:
        print(f"[ERROR] Failed to load: {e}")
        return set()


# ============================================================
# 便捷函数
# ============================================================

def convert_xls_to_json(
    xls_path: str,
    json_path: str,
    source: str = "考研英语大纲"
) -> bool:
    """
    将 XLS 大纲转换为 JSON 格式。

    Args:
        xls_path: XLS 文件路径
        json_path: JSON 输出路径
        source: 词汇来源描述

    Returns:
        是否转换成功
    """
    # 1. 从 XLS 加载
    words = load_syllabus_xls(xls_path)
    if not words:
        print(f"❌ XLS 加载失败或为空")
        return False

    # 2. Save as JSON
    return save_syllabus_json(words, json_path, source)


def get_syllabus_path(name: str = "kaoyan") -> str:
    """
    获取标准化的词汇表 JSON 路径。

    Args:
        name: 词汇表名称 (kaoyan, cet4, cet6, etc.)

    Returns:
        标准化路径
    """
    base_dir = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "dicts"
    return str(base_dir / f"{name}_syllabus.json")


def load_syllabus(
    name: str = "kaoyan",
    fallback_xls_path: Optional[str] = None
) -> set:
    """
    智能加载词汇表：优先 JSON，回退到 XLS。

    Args:
        name: 词汇表名称
        fallback_xls_path: JSON 不存在时的 XLS 回退路径

    Returns:
        词汇集合
    """
    json_path = get_syllabus_path(name)

    # 1. 尝试加载 JSON
    if os.path.exists(json_path):
        return load_syllabus_json(json_path)

    # 2. JSON 不存在，尝试从 XLS 转换
    if fallback_xls_path and os.path.exists(fallback_xls_path):
        print(f"[WARN] JSON 不存在，从 XLS 转换...")
        words = load_syllabus_xls(fallback_xls_path)
        if words:
            save_syllabus_json(words, json_path, source=f"{name} 词汇表")
        return words

    print(f"[ERROR] 无法加载词汇表: {name}")
    return set()


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="词汇大纲解析与转换工具")
    parser.add_argument("--xls", type=str, help="输入 XLS 文件路径")
    parser.add_argument("--output", type=str, help="输出 JSON 文件路径")
    parser.add_argument("--name", type=str, default="kaoyan", help="词汇表名称")
    parser.add_argument("--source", type=str, default="考研英语大纲", help="词汇来源描述")

    args = parser.parse_args()

    if args.xls:
        # 指定了 XLS 文件，进行转换
        output_path = args.output or get_syllabus_path(args.name)
        convert_xls_to_json(args.xls, output_path, args.source)
    else:
        # 测试加载
        words = load_syllabus(args.name)
        print(f"[INFO] 加载结果: {len(words)} 词")
        if words:
            sample = sorted(list(words))[:10]
            print(f"       示例: {sample}")
