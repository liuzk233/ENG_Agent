# 文件路径: src/utils/llm_client.py
import time
from openai import OpenAI
from .config import DASHSCOPE_API_KEY, MODEL_NAME, BASE_URL

class LLMClient:
    def __init__(self):
        """初始化千问客户端"""
        self.client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=BASE_URL
        )
        self.model = MODEL_NAME

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_retries: int = 3) -> str:
        """
        发送对话请求并返回结果，包含自动重试机制。
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        for attempt in range(1, max_retries + 1):
            try:
                # 调用千问大模型
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                )
                # 提取并返回生成的文本
                return response.choices[0].message.content
                
            except Exception as e:
                print(f"⚠️ API 请求失败 (尝试 {attempt}/{max_retries}): {e}")
                if attempt == max_retries:
                    raise Exception(f"❌ 大模型接口调用彻底失败: {e}")
                # 失败后等 2 秒再试，防止被服务器限流
                time.sleep(2)