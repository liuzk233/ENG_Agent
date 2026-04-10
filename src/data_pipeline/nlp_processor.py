# 文件路径: src/data_pipeline/nlp_processor.py
import spacy
from collections import Counter

# 加载英文自然语言处理模型
# 这是一个预训练好的模型，它认识单词的词性、时态等语法结构
print("🧠 正在加载 spaCy 英文 NLP 模型...")
nlp = spacy.load("en_core_web_sm")

# 如果你的真题合并起来超过了 100万 字符，spaCy 默认会报错保护内存。
# 我们手动调大这个限制，比如设置为 500万。
nlp.max_length = 5000000 

def extract_high_freq_words(text: str, syllabus_set: set, top_n: int = 100) -> list:
    """
    对试卷文本进行深度 NLP 处理，提取在大纲内的核心高频词汇。
    
    :param text: 真题纯文本字符串
    :param syllabus_set: 考研大纲单词集合
    :param top_n: 我们希望返回前多少个高频词
    :return: 包含单词和频次的字典列表，如 [{'word': 'abandon', 'count': 50}, ...]
    """
    print("⚙️ 开始深度分析真题文本，这可能需要几十秒到几分钟，请耐心等待...")
    
    # 1. 将文本喂给 nlp 模型进行深度解析 (Tokenization & Parsing)
    doc = nlp(text)
    
    valid_words = []
    
    # 2. 遍历解析出来的每一个 "标记" (Token，即单词或符号)
    for token in doc:
        # 过滤规则 A：必须是纯字母（过滤掉数字、标点符号、特殊符号）
        if not token.is_alpha:
            continue
            
        # 过滤规则 B：不能是停用词 (the, a, is, on 这类无实义的词)
        if token.is_stop:
            continue
            
        # 关键步骤：词形还原 (Lemmatization)
        # 例如将 'went', 'going' 全部还原为 'go'
        # 必须转为小写，因为我们的大纲都是小写
        lemma_word = token.lemma_.lower()
        
        # 过滤规则 C：这个还原后的词，必须存在于我们的大纲集合中
        if lemma_word in syllabus_set:
            valid_words.append(lemma_word)
            
    print(f"📊 文本分析完毕，共提取出符合大纲的有效单词实例 {len(valid_words)} 个。")
    
    # 3. 统计词频
    # Counter 会自动帮我们数每个单词出现了多少次
    word_counts = Counter(valid_words)
    
    # 4. 获取出现频率最高的 top_n 个单词
    # most_common() 返回的格式是 [('go', 120), ('make', 95), ...]
    top_words_tuples = word_counts.most_common(top_n)
    
    # 为了后续传给大模型更方便，我们把它组装成结构化的字典列表
    result = [{"word": word, "count": count} for word, count in top_words_tuples]
    
    return result