# 文件路径: src/agents/reviewer.py
import spacy
import json
from lemminflect import getLemma
from snowballstemmer import stemmer

# 引入集中管理的 Prompt 模板
from prompts.templates import REVIEWER_SYSTEM_PROMPT, get_smart_filter_prompt

nlp = spacy.load("en_core_web_sm")
en_stemmer = stemmer("english")

def normalize_uk_us_spelling(word: str) -> set:
    variants = {word}
    if "our" in word: variants.add(word.replace("our", "or"))
    if "or" in word: variants.add(word.replace("or", "our"))
    if "ise" in word: variants.add(word.replace("ise", "ize"))
    if "ize" in word: variants.add(word.replace("ize", "ise"))
    if word.endswith("re"): variants.add(word[:-2] + "er")
    if word.endswith("er"): variants.add(word[:-2] + "re")
    if word.endswith("ce"): variants.add(word[:-2] + "se")
    if word.endswith("se"): variants.add(word[:-2] + "ce")
    if "ll" in word: variants.add(word.replace("ll", "l"))
    
    irregulars = {"grey": "gray", "gray": "grey", "programme": "program", "program": "programme"}
    if word in irregulars:
        variants.add(irregulars[word])
    return variants

def prepare_syllabus_caches(syllabus_set: set) -> tuple:
    syllabus_stemmed = {en_stemmer.stemWord(w) for w in syllabus_set}
    return syllabus_set, syllabus_stemmed

def llm_smart_filter(llm_client, suspected_words: set, syllabus_set: set) -> set:
    """
    终极兜底方案：调用大模型进行（词根提取 + 英美拼写归一 + 基础词汇常识判定）
    """
    if not suspected_words or not llm_client:
        return suspected_words
        
    print(f"🤖 触发大模型智能复核，当前嫌疑词: {suspected_words}")
    words_list = list(suspected_words)
    
    # 使用从 templates 导入的模板
    system_prompt = REVIEWER_SYSTEM_PROMPT
    user_prompt = get_smart_filter_prompt(words_list)
    
    try:
        # 必须设为 0 温度，要求分类和提取绝对稳定
        response_text = llm_client.chat(system_prompt, user_prompt, temperature=0.0)
        clean_json_str = response_text.replace("```json", "").replace("```", "").strip()
        smart_analysis = json.loads(clean_json_str)
        print(f"   💡 大模型分析结果: {smart_analysis}")
        
    except Exception as e:
        print(f"⚠️ 大模型复核失败，退回严格模式: {e}")
        return suspected_words

    final_bad_words = set()
    for original_word, analysis in smart_analysis.items():
        # 如果大模型凭借其常识，认为它是中国高中生都懂的简单词，直接豁免！
        if analysis.get("is_simple") is True:
            continue
            
        # 如果大模型认为它不是无脑简单词，我们拿它提取的 lemma 再去大纲里查最后一次
        smart_lemma = analysis.get("lemma", "").lower()
        if smart_lemma not in syllabus_set:
            # 走到这里的，才是真正的、无处遁形的超纲生僻词
            final_bad_words.add(original_word)
            
    return final_bad_words

def check_vocabulary(text: str, syllabus_set: set, target_words: list, llm_client=None) -> tuple:
    print("🔍 Reviewer Agent 正在进行多维度词汇安检 (级联架构版)...")
    
    doc = nlp(text)
    out_of_syllabus_words = set()
    
    target_set = {w.lower() for w in target_words}
    syllabus_set, syllabus_stemmed = prepare_syllabus_caches(syllabus_set)
    target_stemmed = {en_stemmer.stemWord(w) for w in target_set}
    
    valid_exact_set = syllabus_set | target_set
    valid_stem_set = syllabus_stemmed | target_stemmed

    for token in doc:
        if not token.is_alpha or token.pos_ == "PROPN" or token.is_stop or len(token.text) <= 1:
            continue
            
        raw_word = token.text.lower()
        spacy_lemma = token.lemma_.lower()
        
        word_variants = normalize_uk_us_spelling(raw_word)
        word_variants.update(normalize_uk_us_spelling(spacy_lemma))

        is_valid = False

        for variant in word_variants:
            if variant in valid_exact_set:
                is_valid = True
                break
                
            lemmas_as_verb = getLemma(variant, upos='VERB')
            lemmas_as_noun = getLemma(variant, upos='NOUN')
            lemmas_as_adj  = getLemma(variant, upos='ADJ')
            lemmas_as_adv  = getLemma(variant, upos='ADV')
            
            all_forced_lemmas = set(lemmas_as_verb + lemmas_as_noun + lemmas_as_adj + lemmas_as_adv)
            
            if any(lemma in valid_exact_set for lemma in all_forced_lemmas):
                is_valid = True
                break

            if en_stemmer.stemWord(variant) in valid_stem_set:
                is_valid = True
                break

        if not is_valid:
            out_of_syllabus_words.add(token.text)

    # 引入大模型兜底防线
    if out_of_syllabus_words and llm_client:
        out_of_syllabus_words = llm_smart_filter(llm_client, out_of_syllabus_words, syllabus_set)

    if not out_of_syllabus_words:
        return True, "Perfect! 没有发现超纲词汇。"
        
    bad_words_str = ", ".join(out_of_syllabus_words)
    feedback = (
        f"你的文章中包含了以下 {len(out_of_syllabus_words)} 个大纲外的高级词汇或生僻词：\n"
        f"[{bad_words_str}]\n"
        f"请立刻找到并删除这些词，用最基础的词汇重写表达！"
    )
    
    return False, feedback