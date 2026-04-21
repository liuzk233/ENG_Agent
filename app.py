"""
Streamlit Web UI

使用 LangGraph 流程运行 VocabWeaver。
"""

import streamlit as st
import os
import uuid
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入 LangGraph 流程
from src.graph.graph import compile_graph, run_initialize, run_continue
from src.data_pipeline.parsers.extractor import load_syllabus_xls


# ==========================================
# 页面基础设置
# ==========================================

st.set_page_config(
    page_title="VocabWeaver 词语编织者",
    page_icon="🪄",
    layout="wide"
)


# ==========================================
# 全局资源缓存
# ==========================================

@st.cache_resource
def init_system():
    """初始化系统资源"""
    # 编译 Graph
    compiled_graph = compile_graph()

    # 加载大纲
    syllabus_path = "data/raw/syllabus/考研英语词汇表.xls"
    if not os.path.exists(syllabus_path):
        syllabus_path = r"D:\3_下载与相关数据\xwechat_files\wxid_31zdo0xdsmio22_fcd0\msg\file\2026-04\01.考研英语词汇正序版.xls"

    syllabus = set()
    if os.path.exists(syllabus_path):
        syllabus = load_syllabus_xls(syllabus_path)

    return compiled_graph, syllabus


# 获取缓存实例
compiled_graph, syllabus_set = init_system()


# ==========================================
# 会话状态管理
# ==========================================

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "user_id" not in st.session_state:
    st.session_state.user_id = f"web_user_{uuid.uuid4().hex[:8]}"
if "episode_results" not in st.session_state:
    st.session_state.episode_results = []


# ==========================================
# UI 布局
# ==========================================

# 侧边栏
with st.sidebar:
    st.header("⚙️ 生成设置面板")

    # 模式选择
    mode = st.radio(
        "运行模式",
        ["新故事 (Initialize)", "续写故事 (Continue)"],
        index=0
    )

    # 风格选择
    style = st.selectbox(
        "📝 请选择文章风格",
        ["adventure", "scifi", "mystery", "news", "exam_paper"]
    )

    # 集数设置
    total_episodes = st.number_input(
        "📚 总集数",
        min_value=1,
        max_value=10,
        value=1
    )

    # 目标词汇输入
    words_input = st.text_area(
        "🎯 输入目标单词 (逗号分隔)",
        value="explore, discover, adventure",
        height=100
    )

    target_words = [w.strip() for w in words_input.split(",") if w.strip()]

    # 显示当前会话状态
    st.divider()
    st.subheader("📊 会话状态")
    if st.session_state.session_id:
        st.info(f"Session: {st.session_state.session_id[:8]}...")
        st.info(f"已完成: {len(st.session_state.episode_results)} 集")
    else:
        st.warning("未创建会话")

# 主界面
st.title("🪄 VocabWeaver 词语编织者")
st.markdown("基于 **LangGraph** 的多智能体英语文章生成系统")
st.caption("Writer → Reviewer → 循环修正 → 生成不含超纲词的文章")

st.divider()


# ==========================================
# 核心交互逻辑
# ==========================================

col1, col2 = st.columns([3, 1])

with col1:
    if st.button("🚀 开始生成", type="primary", use_container_width=True):
        if not target_words:
            st.warning("⚠️ 请输入至少一个目标单词！")
        else:
            # 显示加载动画
            with st.spinner("🤖 LangGraph 流程运行中..."):
                try:
                    if mode == "新故事 (Initialize)" or not st.session_state.session_id:
                        # Initialize 模式
                        result = run_initialize(
                            compiled_graph,
                            user_id=st.session_state.user_id,
                            total_episodes=total_episodes,
                            target_words=target_words,
                            style=style,
                        )

                        # 保存会话
                        st.session_state.session_id = result.get("session_id")

                    else:
                        # Continue 模式
                        result = run_continue(
                            compiled_graph,
                            user_id=st.session_state.user_id,
                            session_id=st.session_state.session_id,
                            target_words=target_words,
                        )

                    # 保存结果
                    st.session_state.episode_results.append(result)

                    # 显示结果
                    st.success(f"🎉 生成完成！")
                    st.balloons()

                except Exception as e:
                    st.error(f"❌ 执行失败: {e}")
                    logger.exception("LangGraph 执行失败")

with col2:
    if st.button("🔄 重置会话", use_container_width=True):
        st.session_state.session_id = None
        st.session_state.episode_results = []
        st.rerun()


# ==========================================
# 结果展示
# ==========================================

if st.session_state.episode_results:
    st.divider()
    st.header("📜 生成结果")

    # 使用标签页展示各集结果
    tabs = st.tabs([f"第 {i+1} 集" for i in range(len(st.session_state.episode_results))])

    for i, (tab, result) in enumerate(zip(tabs, st.session_state.episode_results)):
        with tab:
            # 状态信息
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("重试次数", result.get("retry_count", 0))
            with col_b:
                st.metric("调整次数", result.get("adjust_count", 0))
            with col_c:
                fallback = "是" if result.get("fallback_mode") else "否"
                st.metric("兜底模式", fallback)

            # 超纲词
            if result.get("out_of_scope_words"):
                st.warning(f"⚠️ 超纲词: {', '.join(result['out_of_scope_words'])}")

            # 文章内容
            final_text = result.get("final_text") or result.get("draft_text", "")
            if final_text:
                st.markdown("### 📖 文章内容")
                st.info(final_text)


# ==========================================
# 调试信息
# ==========================================

with st.expander("🔧 调试信息"):
    st.json({
        "user_id": st.session_state.user_id,
        "session_id": st.session_state.session_id,
        "episode_count": len(st.session_state.episode_results),
        "syllabus_loaded": len(syllabus_set) if syllabus_set else 0,
    })
