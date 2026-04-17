# 文件路径: src/data_pipeline/parsers/pdf_md_parser.py
import os
import sys
from pathlib import Path
# 修复 Windows 终端编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from src.utils.config import DASHSCOPE_API_KEY, MODEL_NAME, BASE_URL

class NativeHybridPdfParser:
    """
    使用 Marker 官方原生架构的 Hybrid PDF 解析器
    底层：Surya 视觉模型族
    纠错层：Qwen 大模型 (通过原生 OpenAI 兼容服务接入)
    """
    def __init__(self):
        print("⏳ 正在加载 Marker 视觉模型权重到内存/显存 (首次启动较慢)...")
        # 预加载 Marker 需要的所有本地模型 (Surya OCR, Layout, Order 等)
        self.artifact_dict = create_model_dict()

    def parse_to_file(self, file_path: str, output_dir: str):
        print(f"🚀 启动 Marker 原生 Hybrid 解析: {file_path}")
        
        # 1. 构建官方配置字典，强制接管 OpenAI 配置为千问接口
        config = {
            "use_llm": True, 
            "openai_api_key": DASHSCOPE_API_KEY,
            "openai_base_url": BASE_URL,
            "openai_model": "qwen3-vl-flash-2026-01-22"
        }

        # 2. 实例化原生的 PdfConverter (依赖注入式组装)
        converter = PdfConverter(
            artifact_dict=self.artifact_dict,
            renderer="marker.renderers.markdown.MarkdownRenderer",  # 指定输出格式为纯 Markdown
            llm_service="marker.services.openai.OpenAIService",     # 挂载 OpenAI 兼容服务
            config=config
        )

        # 3. 执行端到端解析 (自动执行：物理切块 -> 局部大模型修复 -> 全局合并)
        rendered_result = converter(file_path)

        # 使用官方函数解包：得到文本、(忽略的元数据)、图片字典
        text, _, images = text_from_rendered(rendered_result)

        # 4. 落盘保存
        os.makedirs(output_dir, exist_ok=True)
        file_name = os.path.basename(file_path)
        md_file_name = os.path.splitext(file_name)[0] + ".md"
        output_path = os.path.join(output_dir, md_file_name)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
            
        print(f"✅ 解析完成！原生 Hybrid Markdown 已保存至: {output_path}")
        return True

    def parse_directory(self, input_dir: str, output_dir: str):
        """
        批量解析整个文件夹的 PDF 文件

        Args:
            input_dir: PDF 文件所在的目录
            output_dir: Markdown 输出目录
        """
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"❌ 输入目录不存在: {input_dir}")
            return

        # 获取所有 PDF 文件
        pdf_files = list(input_path.glob("*.pdf"))
        if not pdf_files:
            print(f"❌ 目录中没有找到 PDF 文件: {input_dir}")
            return

        print(f"📂 找到 {len(pdf_files)} 个 PDF 文件待处理...")
        print("-" * 50)

        success_count = 0
        failed_files = []

        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] 处理: {pdf_file.name}")
            try:
                self.parse_to_file(str(pdf_file), output_dir)
                success_count += 1
            except Exception as e:
                print(f"❌ 处理失败: {e}")
                failed_files.append((pdf_file.name, str(e)))

        print("-" * 50)
        print(f"\n📊 处理完成！")
        print(f"✅ 成功: {success_count}/{len(pdf_files)}")
        if failed_files:
            print(f"❌ 失败: {len(failed_files)}")
            for name, error in failed_files:
                print(f"   - {name}: {error}")

# 测试入口
if __name__ == "__main__":
    parser = NativeHybridPdfParser()
    parser.parse_directory(
        input_dir=r"D:\0_workspace\1_project\10_Eng_agent\ENG_Agent\data\raw\corpus\exam_paper",
        output_dir=r"D:\0_workspace\1_project\10_Eng_agent\ENG_Agent\data\processed\markdown\exam_paper"
    )