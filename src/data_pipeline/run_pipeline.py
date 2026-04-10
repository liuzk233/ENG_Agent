# 文件路径: src/data_pipeline/run_pipeline.py
import json
import os
from extractor import load_syllabus_xls, load_test_paper
from nlp_processor import extract_high_freq_words

# 1. 定义你给出的硬编码路径
SYLLABUS_PATH = "/root/rivermind-data/Eng_Agent/data/raw/outline_vocabulary/01.考研英语词汇正序版.xls"
TEST_PAPER_PATH = "/root/rivermind-data/Eng_Agent/data/raw/test_paper/text.txt"

# 定义输出路径（处理好的数据保存在这里）
OUTPUT_DIR = "/root/rivermind-data/Eng_Agent/data/processed/"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "high_freq_words.json")

def main():
    # 确保输出目录存在，如果不存在则自动创建
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 第一步：搬运数据
    syllabus_set = load_syllabus_xls(SYLLABUS_PATH)
    test_text = load_test_paper(TEST_PAPER_PATH)
    
    # 如果读取失败，中断执行
    if not syllabus_set or not test_text:
        print("🚨 数据加载失败，请检查文件路径和内容。")
        return

    # 第二步： NLP 分析，提取前 100 个高频词
    # 你可以把 100 改成 500 或其他数字
    high_freq_results = extract_high_freq_words(test_text, syllabus_set, top_n=100)
    
    # 第三步：将结果保存为 JSON 文件，供下一个阶段的 Agent 使用
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # indent=4 让保存的 JSON 文件具有良好的缩进，方便人类阅读
        json.dump(high_freq_results, f, ensure_ascii=False, indent=4)
        
    print(f"\n🎉 大功告成！处理后的高频词库已保存至: {OUTPUT_FILE}")
    
    # 打印出前 10 个看看效果
    print("\n🏆 Top 10 核心高频词预览:")
    for i, item in enumerate(high_freq_results[:10]):
        print(f"  {i+1}. {item['word']} (出现 {item['count']} 次)")

if __name__ == "__main__":
    main()