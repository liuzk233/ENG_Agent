# 文件路径: src/data_pipeline/extractor.py
import pandas as pd

# 文件路径: src/data_pipeline/extractor.py
import pandas as pd

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