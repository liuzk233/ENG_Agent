# 文件路径: src/data_pipeline/extractor.py
import pandas as pd

def load_syllabus_xls(file_path: str) -> set:
    """
    读取考研大纲 Excel 文件，并将其转化为一个 Set (集合)。
    
    为什么要用 Set？
    因为后续我们需要成千上万次地检查 "某个单词是否在大纲里"。
    在 Python 中，List 的查找速度是 O(n)（很慢），而 Set 的查找速度是 O(1)（瞬间完成）。
    """
    print(f"📦 正在加载词汇大纲: {file_path}")
    try:
        # header=None 表示第一行就是数据，没有表头
        # usecols=[0] 表示只读取第一列 (第0列)
        df = pd.read_excel(file_path, header=None, usecols=[0])
        
        # 提取第一列的数据转化为列表，过滤掉空值，统一转为小写
        words_list = df[0].dropna().astype(str).tolist()
        syllabus_set = {word.strip().lower() for word in words_list if word.strip()}
        
        print(f"✅ 成功加载大纲，共包含 {len(syllabus_set)} 个单词。\n")
        return syllabus_set
    
    except Exception as e:
        print(f"❌ 加载大纲失败: {e}")
        return set()

def load_test_paper(file_path: str) -> str:
    """
    读取试卷文本文件。
    """
    print(f"📄 正在加载历年真题: {file_path}")
    try:
        # 使用 utf-8 编码读取，防止中文或特殊字符乱码
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        print(f"✅ 成功加载真题，文本总长度为: {len(text)} 字符。\n")
        return text
    
    except Exception as e:
        print(f"❌ 加载真题失败: {e}")
        return ""