# =====================================================================
# 模块：异构词汇大纲解析器 (Heterogeneous Syllabus Parser)，离线
# =====================================================================
# 【业务痛点】
# 来源广泛的单词大纲（中考、高考、四六级、考研）存在极高的“格式非标准性”：
#   1. 文件类型多变：可能是 Excel、PDF、TXT 等完全不同的载体。
#   2. 内部结构混乱：即使同为 Excel，目标单词所在的列、是否包含表头、是否有脏数据等均不可预测。
#
# 【当前方案】
# 目前提供基础的硬编码提取逻辑（例如 load_syllabus_xls 假定单词始终在第一列）。
#
# 【未来演进方向】
# 计划引入 Agent 架构（如 OpenClaw 或其他具备 Code Interpreter 能力的智能体）。
# 利用大模型的逻辑推理能力，先“观察”文件样本，动态识别单词所在的具体位置，
# 从而彻底消除 if/else 规则的硬编码，实现真正的高泛化文档解析。
#
# 【示例】
#   from openclaw import Agent

#   agent = Agent()
#   prompt = """
#   请联网寻找今年的考研英语二大纲词汇。
#   要求：
#   1. 清洗掉所有的中文释义、音标和特殊符号。
#   2. 将单词去重并全部转换为小写。
#   3. 将最终的纯单词列表保存为 JSON 数组格式。
#   4. 将文件保存到我本地的 `data/processed/syllabus_current.json` 中。
#   """
#   agent.run(prompt)
# 
# =====================================================================

# 文件路径: src/data_pipeline/extractor.py
import pandas as pd

def load_syllabus_xls(file_path: str) -> set:
    """
    精简版：读取大纲并处理特殊符号 (/, -, \xa0)
    """
    try:
        df = pd.read_excel(file_path, header=None, usecols=[0])
        syllabus_set = set()
        
        # 遍历第一列去重、去空后的数据
        for item in df[0].dropna().astype(str):
            # 1. 转小写，去除两端空白，并将 \xa0 (不间断空格) 替换为普通空格
            clean_item = item.strip().lower().replace('\xa0', ' ')
            
            # 2. 针对 / 进行切割 (如 'a/an' 会被切分为 ['a', 'an'])
            # 带有 - 的单词 (如 'grown-up') 因为没有 /，会被当作整体直接放入
            syllabus_set.update(word.strip() for word in clean_item.split('/') if word.strip())
            
        return syllabus_set
        
    except Exception as e:
        print(f"❌ 加载大纲失败: {e}")
        return set()
