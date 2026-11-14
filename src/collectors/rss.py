# -*- coding: utf-8 -*-

# ==============================================================================
# 📡 src/collectors/rss.py - 权威官方博客与专家专栏 RSS 采集器
#
# 【小白通俗理解】：
# RSS 是互联网上最古老也最纯粹的新闻订阅协议。
# 像 OpenAI、Google AI、Hugging Face 官方博客，每当他们发布新模型或战略公告时，
# 他们的服务器都会自动更新一个 XML 格式的“订阅广播清单（RSS Feed）”。
# 这个脚本负责每天去收听这些官方的广播清单，把它读下来，提取官方最新的权威发布，
# 避开社交媒体各种夸大其词的二次转述，直达第一手信源。
# 技术亮点：使用 Python 自带的 XML 解析引擎，零依赖解析 RSS 2.0 与 Atom 双重协议。
# ==============================================================================

import logging
import xml.etree.ElementTree as ET # Python 标准库内置的 XML 树状解析器
from typing import List, Dict, Any
from src.collectors.base import BaseCollector, NewsItem # 统一的数据模型基类
from src.utils import http_get                          # 通用网络请求函数

logger = logging.getLogger("AIAgent.RSS")


class RSSFeedCollector(BaseCollector):
    """
    权威 RSS 订阅源采集器具体实现。
    """

    @property
    def name(self) -> str:
        return "Authoritative RSS Feeds"

    def _strip_html(self, text: str) -> str:
        """
        【辅助清洗小工具】：
        RSS 广播里的正文常常夹杂着很多 HTML 排版标签（如 `<p>`, `<a>`, `<b>`）。
        这个函数用简单的正则表达式把所有的 `<...>` 标签剥离掉，只留下纯正文文字。
        """
        import re
        clean = re.sub(r"<[^>]+>", " ", text) # 把任何被尖括号包围的标签替换成空格
        clean = " ".join(clean.split())       # 压缩多余的连续空白字符
        return clean.strip()

    def _parse_feed(self, xml_text: str, feed_name: str, max_items: int) -> List[NewsItem]:
        """
        【核心 XML 解析逻辑】：
        由于世界上的 RSS 主要有两种格式：一种叫 RSS 2.0，另一种叫 Atom。
        这个函数能同时看懂这两种格式，自动向下兼容。
        """
        items: List[NewsItem] = []
        try:
            # 把下载回来的 XML 字符串加载成内存里的一棵树（Root 根节点）
            root = ET.fromstring(xml_text)
        except Exception as e:
            logger.warning(f"订阅源 '{feed_name}' 的 XML 语法解析异常: {e}")
            return []

        # ----------------------------------------------------------------------
        # 分支 1：如果是经典的 RSS 2.0 格式（结构是 <rss><channel><item>...）
        # ----------------------------------------------------------------------
        channel = root.find("channel")
        if channel is not None:
            # 找到所有的 <item> 文章节点，最多只取前 max_items 条
            for item_elem in channel.findall("item")[:max_items]:
                title = item_elem.findtext("title") or ""             # 提取标题
                link = item_elem.findtext("link") or ""               # 提取文章网址
                pub_date = item_elem.findtext("pubDate") or ""         # 提取发布时间
                description = item_elem.findtext("description") or "" # 提取正文内容

                if title and link:
                    # 剥掉 HTML 标签，并且为了防止内容太长，最多只保留前 250 个字符
                    clean_desc = self._strip_html(description)[:250]
                    items.append(
                        NewsItem(
                            title=title.strip(),
                            url=link.strip(),
                            source=feed_name,
                            summary=clean_desc,
                            published_at=pub_date.strip(),
                            score=10, # 官方发布默认给予基础保底权重 10 分
                        )
                    )
            return items

        # ----------------------------------------------------------------------
        # 分支 2：如果是更新的 Atom 协议格式（结构是 <feed><entry>...）
        # ----------------------------------------------------------------------
        # Atom 协议通常带有 XML 命名空间（xmlns）
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        if not entries:
            # 如果没有命名空间，就采用模糊匹配兜底
            entries = [child for child in root if child.tag.endswith("entry")]

        for entry in entries[:max_items]:
            # 提取文章标题
            title_elem = entry.find("atom:title", ns)
            if title_elem is None:
                title_elem = entry.find("title")
            title = title_elem.text if title_elem is not None and title_elem.text else ""

            # 提取文章超链接（在 Atom 里，链接往往写在属性里，如 <link href="..."/>）
            link = ""
            link_elem = entry.find("atom:link", ns)
            if link_elem is None:
                link_elem = entry.find("link")
            if link_elem is not None:
                link = link_elem.get("href") or link_elem.text or ""

            # 提取文章摘要或正文
            summary_elem = entry.find("atom:summary", ns) or entry.find("summary")
            if summary_elem is None:
                summary_elem = entry.find("atom:content", ns) or entry.find("content")
            summary = summary_elem.text if summary_elem is not None and summary_elem.text else ""

            # 提取更新时间
            updated_elem = entry.find("atom:updated", ns) or entry.find("updated")
            updated = updated_elem.text if updated_elem is not None and updated_elem.text else ""

            if title and link:
                items.append(
                    NewsItem(
                        title=title.strip(),
                        url=link.strip(),
                        source=feed_name,
                        summary=self._strip_html(summary)[:250],
                        published_at=updated.strip(),
                        score=15,
                    )
                )

        return items

    def collect(self) -> List[NewsItem]:
        """
        遍历我们在 config.json 里配置的所有 RSS 订阅网址，挨个下载并解析。
        """
        feeds = self.config.get("feeds", [])
        max_per_feed = self.config.get("max_items_per_feed", 3)
        all_items: List[NewsItem] = []

        for feed_info in feeds:
            feed_name = feed_info.get("name", "RSS") # 博客的名字（如 OpenAI Blog）
            feed_url = feed_info.get("url")          # 订阅源的具体 XML 地址
            if not feed_url:
                continue

            logger.info(f"正在拉取官方 RSS 广播: {feed_name}...")
            xml_text = http_get(feed_url, timeout=10)
            if not xml_text:
                logger.warning(f"未能抓取到 RSS 内容: {feed_name}")
                continue

            # 调用内部解析逻辑，把 XML 转换成我们熟悉的 NewsItem 列表
            parsed = self._parse_feed(xml_text, feed_name, max_per_feed)
            all_items.extend(parsed)

        logger.info(f"RSS 官方博客采集完成，共从 {len(feeds)} 个权威频道汇总了 {len(all_items)} 篇新资讯。")
        return all_items
