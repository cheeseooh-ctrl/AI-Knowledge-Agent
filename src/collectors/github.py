# -*- coding: utf-8 -*-

# ==============================================================================
# 🛠️ src/collectors/github.py - GitHub 热门开源 AI 项目采集器
#
# 【小白通俗理解】：
# GitHub 是全世界最大的开源代码托管平台，几乎所有革命性的 AI 框架（如 LangChain、
# AutoGen、Dify、Unsloth）都是在这里诞生的。
# 这个脚本负责调用 GitHub 官方的 Search API，搜索近期带有 "agent"、"llm" 标签、
# 且 Star 数（收藏星标）快速蹿升的热门代码仓库，抓取项目名称、星标数、主语言和功能描述。
# ==============================================================================

import json           # 解析 GitHub 返回的 JSON 字典
import logging        # 打印日志
from typing import List
from src.collectors.base import BaseCollector, NewsItem # 统一的数据盒子模型
from src.utils import http_get                          # 通用网络请求工具

logger = logging.getLogger("AIAgent.GitHub")


class GitHubTrendingCollector(BaseCollector):
    """
    GitHub 开源项目采集器具体实现。
    """

    @property
    def name(self) -> str:
        return "GitHub AI Projects"

    def collect(self) -> List[NewsItem]:
        # 从配置中读取最多抓几个开源项目（默认 6 个）
        max_items = self.config.get("max_items", 6)
        # 用户关心的 GitHub 主题标签（如 agent、llm、ai、mcp、rag）
        topics = self.config.get("topics", ["llm", "agent", "ai", "mcp", "rag"])

        # ----------------------------------------------------------------------
        # 构造 GitHub 搜索语法 Query
        # ----------------------------------------------------------------------
        # 语法解释：
        # stars:>200        -> 这个项目必须至少有 200 个 Star（过滤掉个人随手建的垃圾空项目）
        # topic:llm+topic:agent -> 项目被打上了 llm 或 agent 的主题标签
        # sort=updated&order=desc -> 按最近有代码更新的时间倒序排，确保项目依然活跃维护
        import urllib.parse
        topic_clause = "+".join([f"topic:{t}" for t in topics[:3]])
        query = f"stars:>200+{topic_clause}"
        url = f"https://api.github.com/search/repositories?q={query}&sort=updated&order=desc&per_page=12"

        logger.info("正在通过 GitHub Search API 扫描活跃的开源 AI Agent 与底层框架...")
        
        # 按照 GitHub API 的规范，带上官方推荐的 Accept 协议头
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }

        raw_text = http_get(url, headers=headers)
        if not raw_text:
            logger.warning("未能从 GitHub 获取数据（可能是 GitHub 触发了每分钟的未登录频次限制）")
            return []

        try:
            data = json.loads(raw_text)
            items = data.get("items", []) # "items" 列表存放着一个个仓库的具体信息
        except Exception as e:
            logger.error(f"解析 GitHub 返回的 JSON 数据失败: {e}")
            return []

        results: List[NewsItem] = []
        for item in items:
            name = item.get("full_name") or ""           # 仓库全名（例如：bytedance/deer-flow）
            html_url = item.get("html_url") or ""        # 仓库的主页网址
            description = item.get("description") or "暂无项目描述" # 官方简介
            stars = item.get("stargazers_count") or 0    # 项目收获的 Star 星星总数
            language = item.get("language") or "Code"    # 主要编程语言（如 Python、TypeScript）
            created_at = item.get("created_at") or ""    # 仓库创建时间

            # 拼装格式优美的摘要文本
            summary = f"[{language}] ⭐️ {stars:,} stars - {description}"

            # 存入标准快递盒 NewsItem 中
            results.append(
                NewsItem(
                    title=f"{name} (⭐️ {stars:,})",
                    url=html_url,
                    source="GitHub Trending",
                    summary=summary,
                    score=stars, # 将 Star 星标数作为该开源项目的质量热度打分
                    published_at=created_at,
                    metadata={
                        "repo_name": name,
                        "stars": stars,
                        "language": language,
                    }
                )
            )

            # 抓够了预定数量就停止
            if len(results) >= max_items:
                break

        logger.info(f"GitHub 采集完成，成功收录 {len(results)} 个活跃开源项目。")
        return results
