# -*- coding: utf-8 -*-

# ==============================================================================
# 📄 src/collectors/huggingface.py - Hugging Face 前沿学术论文采集器
#
# 【小白通俗理解】：
# Hugging Face 是当今全球开源 AI 模型与算法的“麦加圣地”。
# 它的 Daily Papers（每日论文榜单）由全球顶尖学者与前沿研究员共同投票产生。
# 这个脚本负责从该榜单的官方接口中，拉取今天全世界最受推崇的几篇重磅论文，
# 抓取它们的论文标题、ArXiv 编号、摘要、以及社区点赞数 (Upvotes)。
# ==============================================================================

import json           # 负责解析 JSON 数据
import logging        # 负责日志记录
from typing import List
from src.collectors.base import BaseCollector, NewsItem # 统一的数据模型基类
from src.utils import http_get                          # 通用网络请求函数

logger = logging.getLogger("AIAgent.HuggingFace")


class HuggingFacePapersCollector(BaseCollector):
    """
    Hugging Face 每日论文采集器实现类。
    """

    @property
    def name(self) -> str:
        return "Hugging Face Daily Papers"

    def collect(self) -> List[NewsItem]:
        # 从配置中读取最多抓取几篇论文（默认 8 篇）
        max_items = self.config.get("max_items", 8)
        # Hugging Face 官方开放的每日论文公开接口地址
        url = "https://huggingface.co/api/daily_papers"

        logger.info("正在连接 Hugging Face 官方 API 获取今日最新学术论文榜单...")
        raw_text = http_get(url)
        if not raw_text:
            logger.warning("未能从 Hugging Face API 获取到响应")
            return []

        # 把纯文本解析成 Python 的列表
        try:
            items = json.loads(raw_text)
            if not isinstance(items, list):
                logger.warning("Hugging Face API 返回的数据格式异常（不是预期的列表）")
                return []
        except Exception as e:
            logger.error(f"解析 Hugging Face 响应失败: {e}")
            return []

        results: List[NewsItem] = []

        # 定义一个小辅助函数：帮我们准确提取出某篇论文被点了多少个赞 (Upvotes)
        def get_upvotes(item):
            paper = item.get("paper", {})
            return paper.get("upvotes") or item.get("upvotes") or 0

        # 按社区点赞数从多到少排序，赞越多的突破性研究排在最前面
        sorted_items = sorted(items, key=get_upvotes, reverse=True)

        for item in sorted_items:
            # 兼容两种常见的数据嵌套层级（有时字段在 paper 里，有时在外层）
            paper = item.get("paper", {})
            paper_id = paper.get("id") or item.get("id") or ""         # ArXiv 论文唯一编号 (如 2611.15777)
            title = paper.get("title") or item.get("title") or ""       # 论文英文原标题
            summary = paper.get("summary") or item.get("summary") or "" # 论文的 Abstract 摘要
            upvotes = paper.get("upvotes") or item.get("upvotes") or 0  # 论文获得的点赞数
            published_at = paper.get("publishedAt") or item.get("publishedAt") or "" # 发表时间

            # 如果论文连标题都没有，说明是异常脏数据，直接丢弃
            if not title:
                continue

            # 对超长的论文摘要做一些初步的整容清洗：
            # 把正文里的换行符变成空格，如果摘要超过 250 个字符就截断加省略号，防止内容过长撑爆后续大模型
            clean_summary = summary.replace("\n", " ").strip()
            if len(clean_summary) > 250:
                clean_summary = clean_summary[:247] + "..."

            # 拼出这篇论文在 Hugging Face 网站上的专属网页地址
            paper_url = f"https://huggingface.co/papers/{paper_id}" if paper_id else "https://huggingface.co/papers"

            # 封装进统一的标准快递盒 NewsItem 中
            results.append(
                NewsItem(
                    title=title,
                    url=paper_url,
                    source="Hugging Face Papers",
                    summary=f"论文摘要: {clean_summary} (HF Upvotes: {upvotes})",
                    score=upvotes, # 把论文点赞数作为该项目的质量得分
                    published_at=published_at,
                    metadata={
                        "arxiv_id": paper_id,
                        "upvotes": upvotes,
                    }
                )
            )

            # 达到设定的数量上限就收工
            if len(results) >= max_items:
                break

        logger.info(f"Hugging Face 论文采集完成，成功收录 {len(results)} 篇高赞研究。")
        return results
