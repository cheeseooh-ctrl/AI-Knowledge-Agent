# -*- coding: utf-8 -*-

# ==============================================================================
# 📰 src/exporters/markdown_exporter.py - Markdown 日报生成与归档器（排版编辑部）
#
# 【小白通俗理解】：
# 这个文件是全系统的“报社美编与排版印刷厂”。
# 它从大模型那里接收到规整的 JSON 提炼结果（有重点、有分类、有要点），
# 负责把这些数据翻译成排版考究、视觉舒适的 GitHub Flavored Markdown 格式：
# 1. 顶部加上精美的日期与信源统计横幅；
# 2. 用 > [!IMPORTANT] 高亮框突出今日最重要的行业风向；
# 3. 为每条资讯打上分类 Emoji、星标 Badge 和超链接；
# 4. 把文件保存在 ./reports 目录下，并顺便备份一份纯 JSON 供以后检索。
# ==============================================================================

import os             # 负责创建目录和路径拼接
import json           # 负责将数据写入 .json 备份文件
import logging        # 负责日志记录
from datetime import datetime # 负责获取生成时间
from typing import Dict, Any, Optional

logger = logging.getLogger("AIAgent.Exporter")


class MarkdownExporter:
    """
    负责将结构化数据导出为 Markdown 与 JSON 文件的类。
    """

    def __init__(self, output_dir: str = "./reports"):
        # 设定报告保存的根文件夹（默认保存在 ./reports 目录下）
        self.output_dir = output_dir
        # os.makedirs 负责自动在电脑上建文件夹。exist_ok=True 表示如果文件夹已经存在，就不要报错
        os.makedirs(self.output_dir, exist_ok=True)

    def export(self, data: Dict[str, Any], date_str: Optional[str] = None, save_json: bool = True) -> str:
        """
        【排版核心方法】：把数据拼接成一段长长的 Markdown 文本，并写入硬盘。
        """
        # 如果调用者没给日期，就默认使用电脑今天的日期（如 2026-11-14）
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # ----------------------------------------------------------------------
        # 第一步：把大模型提炼出来的各个模块安全地取出来
        # ----------------------------------------------------------------------
        daily_focus = data.get("daily_focus", "暂无今日焦点总结") # 一句话今日看点
        breakthroughs = data.get("breakthroughs", [])           # 重磅突破列表
        tools = data.get("open_source_tools", [])               # 开源工具列表
        papers = data.get("trending_papers", [])                # 论文列表
        discussions = data.get("hot_discussions", [])           # 社区讨论列表

        # 计算今天总共收录了多少条精选资讯
        total_items = len(breakthroughs) + len(tools) + len(papers) + len(discussions)

        # ----------------------------------------------------------------------
        # 第二步：开始一行行拼装 Markdown 文档
        # ----------------------------------------------------------------------
        md_lines = [] # 用一个列表来逐行存放要写的文字
        
        # 1. 顶部大标题与数据统计横幅
        md_lines.append(f"# 🪐 AI 全球前沿早报 | {date_str}\n")
        md_lines.append(f"> 📡 **自动聚合与提炼**：覆盖 Hacker News、Hugging Face Papers、GitHub 开源、官方权威发布 | 精选收录 **{total_items}** 条动态\n")

        # 2. 今日核心大势重点关注框（采用 GitHub 规范的 Callout 语法）
        md_lines.append("> [!IMPORTANT]")
        md_lines.append(f"> **今日核心风向**：{daily_focus}\n")

        # 3. 渲染第一版块：🚀 重磅突破与行业要闻
        if breakthroughs:
            md_lines.append("## 🚀 1. 重磅突破与行业要闻\n")
            for item in breakthroughs:
                title = item.get("title", "")
                orig_title = item.get("original_title", "")
                url = item.get("url", "#")
                source = item.get("source", "权威信源")
                why = item.get("why_it_matters", "")
                points = item.get("key_points", [])

                # 带有超链接的子标题
                md_lines.append(f"### ✦ [{title}]({url})")
                # 如果有英文原标题，用斜体附在下方方便对照
                if orig_title and orig_title != title:
                    md_lines.append(f"*原标: {orig_title}*")
                md_lines.append(f"- **信源与链接**：`{source}` ｜ [点击阅读原文 ↗]({url})")
                if why:
                    md_lines.append(f"- **为何重要**：{why}")
                if points:
                    md_lines.append("- **核心要点**：")
                    for pt in points:
                        md_lines.append(f"  - {pt}")
                md_lines.append("") # 插入一个空行拉开段落距离

        # 4. 渲染第二版块：🛠️ 热门开源项目与智能体框架
        if tools:
            md_lines.append("## 🛠️ 2. 热门开源项目与智能体框架\n")
            for item in tools:
                name = item.get("name", "开源项目")
                url = item.get("url", "#")
                tag = item.get("stars_or_tag", "")
                desc = item.get("description", "")

                # 徽章 Badge 标签
                tag_badge = f"`{tag}` " if tag else ""
                md_lines.append(f"* **[{name}]({url})** {tag_badge}")
                md_lines.append(f"  {desc}")
            md_lines.append("")

        # 5. 渲染第三版块：📄 必读前沿学术论文
        if papers:
            md_lines.append("## 📄 3. 必读前沿学术论文 (Hugging Face Papers)\n")
            for item in papers:
                title = item.get("title", "")
                orig = item.get("original_title", "")
                url = item.get("url", "#")
                takeaway = item.get("takeaway", "")

                md_lines.append(f"* **[{title}]({url})**")
                if orig and orig != title:
                    md_lines.append(f"  *Original: {orig}*")
                if takeaway:
                    md_lines.append(f"  > **创新亮点**：{takeaway}")
            md_lines.append("")

        # 6. 渲染第四版块：💬 极客社区深度讨论
        if discussions:
            md_lines.append("## 💬 4. 极客社区深度讨论 (Hacker News)\n")
            for item in discussions:
                title = item.get("title", "")
                url = item.get("url", "#")
                summary = item.get("summary", "")

                md_lines.append(f"* **[{title}]({url})**")
                if summary:
                    md_lines.append(f"  {summary}")
            md_lines.append("")

        # 7. 页脚免责声明与生成时间戳
        md_lines.append("---")
        md_lines.append(f"*Generated automatically by AI Knowledge Agent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        # ----------------------------------------------------------------------
        # 第三步：将拼接好的字符串写入硬盘文件
        # ----------------------------------------------------------------------
        # 把每一行用换行符 \n 缝合起来，组成一整篇大文章
        content = "\n".join(md_lines)
        file_path = os.path.join(self.output_dir, f"{date_str}_AI_Daily_Briefing.md")

        # 打开文件写入 UTF-8 内容
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Markdown 日报已成功生成并存盘: {file_path}")

        # 如果开启了 JSON 备份，把原始字典原封不动地也存一份
        if save_json:
            json_path = os.path.join(self.output_dir, f"{date_str}_AI_Daily_Briefing.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"原始数据 JSON 副本已备份至: {json_path}")

        # 返回生成好的 Markdown 绝对文件路径
        return file_path
