# 文件路径: src/data_pipeline/parsers/epub_md_parser.py
import os
import re
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from markdownify import markdownify as md

class EpubMarkdownParser:
    """
    极简版 EPUB 解析器：
    直接将 EPUB 转化为纯 Markdown 文本，放弃细粒度 JSON 元数据，
    配合 LlamaIndex 的 SimpleDirectoryReader 目录读取使用。
    """

    # 我们关心的 HTML 块级标签
    BLOCK_TAGS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'table', 'blockquote'}

    def parse_to_file(self, file_path: str, output_dir: str):
        """
        解析 EPUB 并直接保存为 .md 文件
        """
        print(f"📚 启动 EPUB 解析器，开始提取纯 Markdown: {file_path}")
        
        file_name = os.path.basename(file_path)
        # 将 .epub 后缀替换为 .md
        md_file_name = os.path.splitext(file_name)[0] + ".md"
        output_path = os.path.join(output_dir, md_file_name)

        try:
            book = epub.read_epub(file_path, options={'ignore_ncx': True})
        except Exception as e:
            print(f"❌ 读取 EPUB 文件失败 {file_path}: {e}")
            return False

        full_markdown_lines = []

        # 遍历 EPUB 里的每一个 HTML 文档（通常对应一个章节）
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            content = item.get_content()
            soup = BeautifulSoup(content, 'html.parser')

            # =========================================
            # 步骤 1：推断并插入章节标题，充当物理分割线
            # =========================================
            chapter_name = ""
            if soup.title and soup.title.string:
                chapter_name = soup.title.string.strip()
            else:
                first_heading = soup.find(['h1', 'h2'])
                if first_heading and first_heading.get_text(strip=True):
                    chapter_name = first_heading.get_text(strip=True)

            # 如果找到了章节名，把它作为 Markdown 的一级标题加进去
            if chapter_name:
                full_markdown_lines.append(f"\n\n# {chapter_name}\n\n")

            # 找到正文容器
            body = soup.find('body')
            if not body:
                continue

            # =========================================
            # 步骤 2：精准提取块级元素，转为 Markdown
            # =========================================
            for tag in body.find_all(self.BLOCK_TAGS):
                
                # 防嵌套查重
                if tag.find_parent(self.BLOCK_TAGS):
                    continue

                raw_text = tag.get_text(strip=True)
                if not raw_text:
                    continue

                # 优雅降维：HTML 转 Markdown
                md_text = md(str(tag), heading_style="ATX").strip()
                if not md_text:
                    continue

                # =========================================
                # 步骤 3：清洗噪声数据 (例如超长的目录列表)
                # =========================================
                link_pattern = re.compile(r'\[.*?\]\(.*?\)')
                link_count = len(link_pattern.findall(md_text))

                if link_count > 20: 
                    continue 

                # 将干净的 Markdown 段落加入列表，并保留空行分隔
                full_markdown_lines.append(md_text + "\n\n")

        # =========================================
        # 步骤 4：将所有收集到的 Markdown 行写入文件
        # =========================================
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        final_markdown_text = "".join(full_markdown_lines)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_markdown_text)

        print(f"✅ 解析完成！Markdown 已保存至: {output_path}")
        return True