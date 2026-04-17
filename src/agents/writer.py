# 文件路径: src/agents/writer.py

from typing import List, Optional

# 引入我们在 prompts/templates.py 中定义好的模板
from ..prompts.templates import (
    WRITER_SYSTEM_PROMPT,
    get_drafting_prompt,
    get_refining_prompt
)


def generate_draft(llm_client, target_words: list, style: str, reference_texts: Optional[list] = None, feedback: str = None) -> str:
    """
    Writer Agent: 负责生成文章初稿或根据反馈修改文章。

    :param llm_client: 封装好的大模型调用客户端
    :param target_words: 用户要求必须包含的单词列表
    :param style: 文章风格 (如 "科幻", "议论文")
    :param reference_texts: RAG 检索到的参考语料（可选）
    :param feedback: 如果是重写，这里会包含 Reviewer 给出的报错信息
    :return: 生成的文章字符串
    """
    words_str = ", ".join(target_words)

    # 1. 加载系统提示词 (确立角色和刚性约束)
    system_prompt = WRITER_SYSTEM_PROMPT

    # 2. 根据是否带有 feedback，动态组装用户指令
    if not feedback:
        # 第一轮生成 (无报错反馈)
        user_prompt = get_drafting_prompt(style, words_str, reference_texts)
    else:
        # 第 N 轮重写 (包含 Reviewer 的报错反馈)
        user_prompt = get_refining_prompt(style, words_str, feedback)

    # 3. 调用大模型客户端执行任务
    # 温度 (temperature) 设置为 0.7，保留一定的创造力，但不至于过度发散
    print("✍️  Writer Agent 正在奋笔疾书...")
    response_text = llm_client.chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.7
    )

    return response_text
