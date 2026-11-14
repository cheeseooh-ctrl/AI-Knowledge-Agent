# -*- coding: utf-8 -*-

# ==============================================================================
# 💬 src/collectors/hackernews.py - Hacker News 极客讨论采集器
#
# 【小白通俗理解】：
# Hacker News (简称 HN) 是全球顶尖程序员、创业者和极客最活跃的论坛。
# 这里的人眼光挑剔、评价犀利。
# 这个脚本负责每天去 HN 论坛翻找：“今天讨论最激烈、点赞最多的 AI 话题是什么？”
# 技术亮点：它没有用繁琐的网页爬虫，而是利用了 HN 官方提供的免费高速 API (Algolia)，
# 既不需要注册账号，也不会被对方网站当成恶意爬虫封 IP。
# ==============================================================================

import json           # 负责解析接口返回的 JSON 格式文本
import time           # 负责处理时间戳
import logging        # 负责打印日志
import urllib.parse   # 负责把中文或特殊字符转码成符合网址规范的编码（URL Encoding）
from typing import List, Dict, Any
from src.collectors.base import BaseCollector, NewsItem # 引入统一的数据盒子和父类模板
from src.utils import http_get                          # 引入通用网络请求工具

logger = logging.getLogger("AIAgent.HackerNews")


class HackerNewsCollector(BaseCollector):
    """
    Hacker News 采集器具体实现类。
    继承自 BaseCollector，负责完成 HN 社区 AI 话题的抓取。
    """

    @property
    def name(self) -> str:
        # 给自己起个响亮的名字，打印日志时显示
        return "Hacker News (AI)"

    def collect(self) -> List[NewsItem]:
        """
        核心抓取方法：发起网络请求，提取数据并封装为标准 NewsItem 列表。
        """
        # 从配置文件中读取：至少要多少个赞才收录？（默认 20 赞以上才算高质量）
        min_points = self.config.get("min_points", 20)
        # 最多抓取几条？（默认 8 条）
        max_items = self.config.get("max_items", 8)
        # 用户关心的核心关键词列表
        keywords = self.config.get("keywords", ["AI", "LLM", "Agent", "GPT", "Claude", "Gemini", "DeepSeek"])

        # ----------------------------------------------------------------------
        # 构造搜索请求的网址 (URL)
        # ----------------------------------------------------------------------
        # 组合关键词成搜索条件，例如："LLM OR AI Agent OR Claude OR OpenAI"
        query_str = "LLM OR AI Agent OR Claude OR OpenAI OR DeepSeek OR Gemini"
        # 为什么要做 url 编码？因为网址里如果直接写空格或特殊字符，网络请求会报错
        encoded_query = urllib.parse.quote_plus(query_str)
        
        # 拼装最终的 API 请求地址：只搜索故事(tags=story)，点赞数必须大于等于 min_points
        url = (
            f"https://hn.algolia.com/api/v1/search?"
            f"tags=story&numericFilters=points%3E={min_points}"
            f"&query={encoded_query}&hitsPerPage=20"
        )

        logger.info(f"正在从 Hacker News 检索点赞数 >= {min_points} 的热门讨论...")
        raw_text = http_get(url) # 发送网络请求，带回数据文本
        if not raw_text:
            logger.warning("未能从 Hacker News 接口获取到数据（可能是网络暂时波动）")
            return []

        # 将接口返回的纯文本字符串解析成 Python 字典
        try:
            data = json.loads(raw_text)
            hits = data.get("hits", []) # "hits" 列表里存放着一条条讨论帖子
        except Exception as e:
            logger.error(f"解析 Hacker News 返回的 JSON 数据失败: {e}")
            return []

        results: List[NewsItem] = []
        seen_urls = set() # 准备一个“去重黑名单”，防止同一个帖子抓两次

        # 按点赞数从高到低降序排序（点赞越多越排在前面）
        hits = sorted(hits, key=lambda x: x.get("points") or 0, reverse=True)

        # 逐个审查每一条帖子
        for hit in hits:
            title = hit.get("title") or ""             # 贴子标题
            target_url = hit.get("url")                # 贴子指向的原文章链接
            object_id = hit.get("objectID")            # HN 给这个帖子分配的唯一编号
            # 拼出 HN 社区内部的评论区讨论链接
            hn_discussion_url = f"https://news.ycombinator.com/item?id={object_id}"

            # 如果某些帖子只是社区问答（如 Ask HN），它没有外部 URL，我们就把评论区当成原文链接
            if not target_url:
                target_url = hn_discussion_url

            # 如果这个链接之前已经收录过了，直接跳过
            if target_url in seen_urls:
                continue
            seen_urls.add(target_url)

            points = hit.get("points") or 0           # 点赞数
            num_comments = hit.get("num_comments") or 0 # 评论数
            created_at = hit.get("created_at") or ""    # 发帖时间

            # 拼凑一段通俗易懂的简短摘要
            summary = f"HN 讨论热度: {points} 点赞 / {num_comments} 条评论。讨论链接: {hn_discussion_url}"

            # 把这篇帖子的关键信息装入标准“快递盒” NewsItem 中
            results.append(
                NewsItem(
                    title=title,
                    url=target_url,
                    source="Hacker News",
                    summary=summary,
                    score=points,
                    published_at=created_at,
                    metadata={
                        "hn_id": object_id,
                        "hn_url": hn_discussion_url,
                        "points": points,
                        "num_comments": num_comments,
                        "author": hit.get("author", ""),
                    }
                )
            )

            # 如果已经抓够了用户指定的数量（比如 8 条），就立即停止，不再多抓
            if len(results) >= max_items:
                break

        logger.info(f"Hacker News 采集完毕，精选收录 {len(results)} 条高分讨论。")
        return results
