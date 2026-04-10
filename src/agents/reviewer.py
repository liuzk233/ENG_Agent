# 文件路径: src/agents/reviewer.py
import spacy

# 复用我们上一阶段的模型
nlp = spacy.load("en_core_web_sm")

def check_vocabulary(text: str, syllabus_set: set, target_words: list) -> tuple:
    """
    Reviewer Agent: 严格检查文章中是否有超纲词汇。
    
    :param text: Writer 生成的文章
    :param syllabus_set: 我们在 Phase 1 提取的官方词汇大纲集合
    :param target_words: 用户指定要用的词 (这些词天然被认为是合法的)
    :return: (是否通过校验布尔值, 质检反馈字符串)
    """
    print("🔍 Reviewer Agent 正在拿着放大镜逐词校验...")
    
    doc = nlp(text)
    out_of_syllabus_words = set()
    
    # 为了防止大小写问题，将 target_words 也转为小写集合
    target_set = {w.lower() for w in target_words}
    
    for token in doc:
        # 只检查纯字母的实词
        if not token.is_alpha:
            continue
            
        # 跳过专有名词（人名、地名等，它们首字母通常大写，在 spacy 中标签为 PROPN）
        if token.pos_ == "PROPN":
            continue
            
        # 提取词根并转小写
        lemma_word = token.lemma_.lower()
        
        # 核心校验逻辑：
        # 如果这个词既不在大纲里，也不是用户强制要求加的词，它就是超纲词！
        if lemma_word not in syllabus_set and lemma_word not in target_set:
            out_of_syllabus_words.add(token.text) # 记录原文中的词态，方便报错
            
    if not out_of_syllabus_words:
        return True, "Perfect! 没有发现超纲词汇。"
        
    # 如果发现了超纲词，组装一封“措辞严厉”的报错信
    bad_words_str = ", ".join(out_of_syllabus_words)
    feedback = (
        f"你的文章中包含了以下 {len(out_of_syllabus_words)} 个大纲外的高级词汇或生僻词：\n"
        f"[{bad_words_str}]\n"
        f"这严重违反了规则！请立刻找到并删除这些词，用最基础的词汇重写表达！"
    )
    
    return False, feedback