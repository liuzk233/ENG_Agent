import os
import json
from .pdf_parser import PDFParser
from .epub_parser import EpubParser

class DocumentIngestionRouter:
    def __init__(self):
        # 注册解析器映射表 (工厂模式)
        self.parsers = {
            '.pdf': PDFParser(),
            '.epub': EpubParser()
        }

    def process_file(self, file_path: str) -> list:
        """主入口：根据扩展名自动路由，返回标准化的字典列表"""
        ext = os.path.splitext(file_path)[1].lower()
        
        parser = self.parsers.get(ext)
        if not parser:
            raise ValueError(f"🚨 不支持的文件格式: {ext}")
            
        print(f"🔄 正在使用 {parser.__class__.__name__} 解析文件: {file_path}")
        
        # 无论底层怎么解析，最终都返回统一的标准化数据结构
        standardized_data = parser.parse(file_path)
        return standardized_data

# 使用示例 (一次性清洗所有数据)
if __name__ == "__main__":
    router = DocumentIngestionRouter()
    all_data = []
    
    # 假设有个文件夹放满了 pdf 和 epub
    for file in os.listdir("data/1_raw/corpus/"):
        file_path = os.path.join("data/1_raw/corpus/", file)
        
        # 路由会自动分发任务
        data = router.process_file(file_path)
        all_data.extend(data)
        
    # 将清洗结果一次性存入 JSON 数据湖，供下游 LlamaIndex 使用
    with open("data/2_processed/corpus_ir.json", "w") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)