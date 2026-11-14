# -*- coding: utf-8 -*-

# ==============================================================================
# 🎭 src/processor/mock_summarizer.py - 本地模拟提炼器（替身演员）
#
# 【小白通俗理解】：
# 这个文件是全系统的“单机备用发电机”或“替身演员”。
# 在软件工程中，“Mock” 的意思就是“模拟仿真”。
# 当你在以下场景时，它就会发挥巨大作用：
# 1. 你刚下载完项目，还没来得及去申请 Google API Key；
# 2. 你的电脑处于离线断网状态，或者大模型服务器突发故障；
# 3. 你只想测一测爬虫和排版代码好不好使，不想浪费大模型的 Token 额度。
# 这个脚本完全不调用任何外部网络，仅用 Python 代码，把采集到的原始新闻字段拼装成
# 和 Gemini 输出一模一样的结构化字典，确保下游的 Markdown 导出器能正常出报纸。
# ==============================================================================

from typing import List, Dict, Any
from src.collectors.base import NewsItem # 统一的数据盒子模型


class MockSummarizer:
    """
    本地规则模拟提炼器类。
    不需要联网，不需要 API Key，纯单机规则实现。
    """

    def summarize(self, items: List[NewsItem]) -> Dict[str, Any]:
        """
        根据信源标签，把新闻快速归类到 4 个不同的分类格子里。
        """
        breakthroughs = [] # 重磅突破分类
        tools = []         # 开源项目分类
        papers = []        # 论文分类
        discussions = []   # 讨论分类

        # 遍历所有清洗好的条目，按来源打标签归类
        for item in items:
            source = item.source
            # 如果来自 Hugging Face，就分到论文库
            if "Hugging Face" in source:
                papers.append({
                    "title": item.title,
                    "original_title": item.title,
                    "url": item.url,
                    "takeaway": item.summary or "聚焦最新架构或训练方法突破，社区热度较高。"
                })
            # 如果来自 GitHub，就分到开源工具库
            elif "GitHub" in source:
                tools.append({
                    "name": item.title,
                    "url": item.url,
                    "stars_or_tag": f"⭐️ {item.score}",
                    "description": item.summary or "热门开源项目，提升开发者效率与智能体协作体验。"
                })
            # 如果来自 Hacker News，就分到极客讨论库
            elif "Hacker News" in source:
                discussions.append({
                    "title": item.title,
                    "url": item.url,
                    "summary": item.summary or "社区极客对该主题展开了深度实测与工程架构讨论。"
                })
            # 其余来自官方博客（如 OpenAI、Google）的，分到行业重磅要闻库
            else:
                breakthroughs.append({
                    "title": item.title,
                    "original_title": item.title,
                    "url": item.url,
                    "source": source,
                    "why_it_matters": "权威机构发布的最新技术动态或重大模型升级。",
                    "key_points": [
                        item.summary[:100] if item.summary else "官方最新发布与进展更新",
                        f"来自权威发布渠道：{source}"
                    ]
                })

        # 构造并返回一个和 Gemini 一模一样的标准字典
        return {
            "daily_focus": "【预览演示模式】今日 AI 领域涵盖了学术前沿突破、热门开源智能体项目以及开发者社区深度实测。",
            "breakthroughs": breakthroughs[:4], # 各分类最多挑选前 4~5 个精华
            "open_source_tools": tools[:5],
            "trending_papers": papers[:4],
            "hot_discussions": discussions[:4],
        }
