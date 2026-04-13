# 文件路径: app.py
import streamlit as st
import os

# 导入我们之前写好的核心后端逻辑
from src.utils.llm_client import LLMClient
from src.agents.orchestrator import run_agent_workflow
from src.data_pipeline.extractor import load_syllabus_xls

# ==========================================
# 1. 页面基础设置 (必须写在最前面)
# ==========================================
st.set_page_config(
    page_title="VocabWeaver 词语编织者",
    page_icon="🪄",
    layout="wide" # 使用宽屏模式
)

# ==========================================
# 2. 全局资源缓存 (🚨 资深工程师核心心法)
# ==========================================
# Streamlit 的运行机制是：用户每次点击按钮，整个 Python 脚本会从头到尾重新运行一次！
# 如果不加 @st.cache_resource，每次点击都会重新加载一次大模型客户端和几千词的 Excel 大纲，导致极度卡顿。
# 加了缓存装饰器，这些沉重的初始化操作只会在网页第一次打开时执行一次。
@st.cache_resource
def init_system():
    # 初始化 LLM 客户端
    llm = LLMClient()
    
    # 加载大纲 (请确保路径正确，建议使用相对路径)
    # 根据你之前的结构，大纲应该在项目根目录的 data 文件夹下
    syllabus_path = "data/raw/outline_vocabulary/01.考研英语词汇正序版.xls"
    
    # 如果相对路径找不到，可以使用你之前的绝对路径 fallback
    if not os.path.exists(syllabus_path):
        syllabus_path = r"D:\3_下载与相关数据\xwechat_files\wxid_31zdo0xdsmio22_fcd0\msg\file\2026-04\01.考研英语词汇正序版.xls"
        
    syllabus = load_syllabus_xls(syllabus_path)
    return llm, syllabus

# 获取缓存好的实例
llm_client, syllabus_set = init_system()

# ==========================================
# 3. UI 布局与组件 (左侧控制面板)
# ==========================================
# st.sidebar 会自动在网页左侧生成一个漂亮的侧边栏
with st.sidebar:
    st.header("⚙️ 生成设置面板")
    
    # 下拉选择框
    style = st.selectbox(
        "📝 请选择文章风格", 
        ["科幻 (Sci-Fi)", "议论文 (Argumentative)", "童话 (Fairy Tale)", "新闻报道 (News)", "悬疑 (Mystery)"]
    )
    
    # 多行文本输入框
    words_input = st.text_area(
        "🎯 输入你想记忆的单词 (用逗号分隔)", 
        value="galaxy, spaceship, explore, suddenly, carefully",
        height=150
    )
    
    # 处理用户输入的单词，去除空格和空字符串
    target_words = [w.strip() for w in words_input.split(",") if w.strip()]

# ==========================================
# 4. UI 布局与组件 (右侧主界面)
# ==========================================
st.title("🪄 VocabWeaver 词语编织者")
st.markdown("输入你想要记忆的单词，AI Agent 将自动为你编织一篇**绝对不含超纲词汇**的专属短文！")

# 画一条分割线
st.divider() 

# 核心交互逻辑：当用户点击这个按钮时，下方代码才会执行
if st.button("🚀 召唤 AI 开始编织文章", type="primary"):
    
    if not target_words:
        st.warning("⚠️ 请至少输入一个目标单词！")
    elif not syllabus_set:
        st.error("🚨 致命错误：词汇大纲加载失败，请检查文件路径！")
    else:
        # 显示一个加载中的动画
        with st.spinner("🤖 AI Writer 正在挥洒创意，Reviewer 正在严格把关，请稍候..."):
            
            # 调用我们在 Phase 2 写好的核心调度器
            result = run_agent_workflow(
                llm_client=llm_client,
                target_words=target_words,
                style=style.split(" ")[0], # 把 "科幻 (Sci-Fi)" 切成 "科幻" 传给模型
                syllabus_set=syllabus_set,
                max_retries=3
            )
            
        # 根据返回的状态更新 UI
        if result["status"] == "success":
            # 绿色成功提示框
            st.success(f"🎉 任务完美完成！(历经 {result['attempts']} 轮修改与审核)")
            
            # 使用 Markdown 美化文章展示区域
            st.markdown("### 📜 你的专属文章")
            
            # 使用 info 框包裹文章内容，看起来更像一个阅读面板
            st.info(result["content"])
            
            # 你甚至可以加一个炫酷的庆祝动画
            st.balloons() 
            
        else:
            # 红色错误提示框
            st.error(f"❌ 生成失败！已达到最大重试次数。Agent 无法在限制内消除所有超纲词汇。")
            st.markdown("### 📜 最后一次尝试的文章 (可能包含超纲词):")
            st.warning(result["content"])