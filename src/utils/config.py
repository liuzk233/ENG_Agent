# 文件路径: src/utils/config.py
import os
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
env_path = '/root/rivermind-data/Eng_Agent/src/.env'
load_dotenv(dotenv_path=env_path)

# 阿里云 DashScope API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# 检查是否配置了 API Key，防止程序裸奔报错
if not DASHSCOPE_API_KEY:
    raise ValueError("🚨 致命错误: 未在 .env 文件中找到 DASHSCOPE_API_KEY。请检查配置！")

# 模型名称，默认使用你指定的千问最新版
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.6-plus-2026-04-02")

# API 请求的基础 URL (阿里云兼容 OpenAI 格式的地址)
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"