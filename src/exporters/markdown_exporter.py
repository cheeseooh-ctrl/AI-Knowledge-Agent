# -*- coding: utf-8 -*-

# ==============================================================================
# 📰 src/exporters/markdown_exporter.py - Markdown 日报生成与归档器（排版编辑部）
#
# 【小白通俗理解】：
# 这个文件是全系统的“报社美编与排版印刷厂”。
# 它从虚拟编辑部那里接收到规整的 JSON 提炼结果以及恶魔质检员的审稿档案，
# 负责把这些数据翻译成排版考究、视觉舒适的 GitHub Flavored Markdown 格式：
# 1. 顶部加上精美的日期与信源统计横幅；
# 2. 插入【恶魔质检总编的质检档案与综合打分徽章】；
# 3. 用 > [!IMPORTANT] 高亮框突出今日最重要的行业风向；
# 4. 为每条资讯打上分类 Emoji、星标 Badge 和超链接；
# 5. 把文件保存在 ./reports 目录下，并顺便备份一份纯 JSON 供以后检索。
# ==============================================================================

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("AIAgent.Exporter")


class MarkdownExporter:
    """
    负责将结构化数据导出为 Markdown 与 JSON 文件的类。
    """

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def export(self, data: Dict[str, Any], date_str: Optional[str] = None, save_json: bool = True) -> str:
        """
        【排版核心方法】：把数据拼接成一段长长的 Markdown 文本，并写入硬盘。
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        daily_focus = data.get("daily_focus", "暂无今日焦点总结")
        breakthroughs = data.get("breakthroughs", [])
        tools = data.get("open_source_tools", [])
        papers = data.get("trending_papers", [])
        discussions = data.get("hot_discussions", [])
        audit_report = data.get("audit_report", {}) # 提取恶魔质检员的审稿档案

        total_items = len(breakthroughs) + len(tools) + len(papers) + len(discussions)

        md_lines = []
        
        # 1. 顶部大标题与数据统计横幅
        md_lines.append(f"# 🪐 AI 全球前沿早报 | {date_str}\n")
        md_lines.append(f"> 📡 **自动聚合与提炼**：覆盖 Hacker News、Hugging Face Papers、GitHub 开源、官方权威发布 | 精选收录 **{total_items}** 条动态\n")

        # 2. 恶魔质检总编的审稿档案 (v1.1.0 新增特性)
        if audit_report:
            score = audit_report.get("overall_score", 85)
            rounds = audit_report.get("rounds", 1)
            dim = audit_report.get("dimension_scores", {})
            advice = audit_report.get("general_advice", "")

            md_lines.append("> [!TIP]")
            md_lines.append(f"> 🛡️ **虚拟编辑部审稿档案**：综合严谨度评分 **`{score} / 100`** ｜ 经历 **`{rounds} 轮`** 主笔与恶魔质检员博弈打磨")
            if dim:
                md_lines.append(f"> * 去公关化: `{dim.get('anti_pr', 85)}分` ｜ 技术实证度: `{dim.get('evidence_density', 85)}分` ｜ 落地启发性: `{dim.get('actionability', 85)}分` ｜ 辩证审视: `{dim.get('critical_balance', 85)}分`")
            if advice:
                md_lines.append(f"> * 总编评语: *\"{advice}\"*")
            md_lines.append("")

        # 3. 今日核心大势重点关注框
        md_lines.append("> [!IMPORTANT]")
        md_lines.append(f"> **今日核心风向**：{daily_focus}\n")

        # 4. 渲染第一版块：🚀 重磅突破与行业要闻
        if breakthroughs:
            md_lines.append("## 🚀 1. 重磅突破与行业要闻\n")
            for item in breakthroughs:
                title = item.get("title", "")
                orig_title = item.get("original_title", "")
                url = item.get("url", "#")
                source = item.get("source", "权威信源")
                why = item.get("why_it_matters", "")
                points = item.get("key_points", [])

                md_lines.append(f"### ✦ [{title}]({url})")
                if orig_title and orig_title != title:
                    md_lines.append(f"*原标: {orig_title}*")
                md_lines.append(f"- **信源与链接**：`{source}` ｜ [点击阅读原文 ↗]({url})")
                if why:
                    md_lines.append(f"- **为何重要**：{why}")
                if points:
                    md_lines.append("- **核心要点**：")
                    for pt in points:
                        md_lines.append(f"  - {pt}")
                md_lines.append("")

        # 5. 渲染第二版块：🛠️ 热门开源项目与智能体框架
        if tools:
            md_lines.append("## 🛠️ 2. 热门开源项目与智能体框架\n")
            for item in tools:
                name = item.get("name", "开源项目")
                url = item.get("url", "#")
                tag = item.get("stars_or_tag", "")
                desc = item.get("description", "")

                tag_badge = f"`{tag}` " if tag else ""
                md_lines.append(f"* **[{name}]({url})** {tag_badge}")
                md_lines.append(f"  {desc}")
            md_lines.append("")

        # 6. 渲染第三版块：📄 必读前沿学术论文
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

        # 7. 渲染第四版块：💬 极客社区深度讨论
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

        # 8. 页脚免责声明与生成时间戳
        md_lines.append("---")
        md_lines.append(f"*Generated automatically by AI Knowledge Agent (v1.1.0 Multi-Agent Editorial Board) at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        content = "\n".join(md_lines)
        file_path = os.path.join(self.output_dir, f"{date_str}_AI_Daily_Briefing.md")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Markdown 日报已成功生成并存盘: {file_path}")

        if save_json:
            json_path = os.path.join(self.output_dir, f"{date_str}_AI_Daily_Briefing.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"原始数据与审稿档案 JSON 副本已备份至: {json_path}")

        return file_path
