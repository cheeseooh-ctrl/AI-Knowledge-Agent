# -*- coding: utf-8 -*-

# ==============================================================================
# 🛠️ src/tools/web_reader.py - 网页与开源仓库穿透抽取工具 (Web Reader Tool)
#
# 【小白通俗理解】：
# 这个文件是给 Agent 戴上的一副“超级放大镜”。
# 以前我们只能看到一个新闻的标题和 200 字摘要；
# 有了这个工具，Agent 可以真正像人类程序员一样：
# 1. 如果遇到 GitHub 链接 -> 它自动穿透去把官方 README.md 全文抓下来；
# 2. 如果遇到官方博客链接 -> 它自动剔除网页导航栏和广告，只抓取核心正文；
# 3. 内置体积防护栏：最多只截取前 4,000 个词，严防网页过长撑爆内存或浪费 Token。
# 特点：纯 Python 3 原生标准库实现，零第三方依赖！
# ==============================================================================

import re
import json
import logging
import urllib.parse
from html.parser import HTMLParser
from typing import Optional, Dict, Any
from src.utils import http_get

logger = logging.getLogger("AIAgent.WebReader")


class SimpleHTMLTextExtractor(HTMLParser):
    """
    【HTML 纯正文剥离提取器】：
    利用 Python 标准库 html.parser，安全地丢弃 <script>、<style>、<nav>、<footer>，
    只提取真正的段落和文本内容。
    """
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.ignore_tags = {"script", "style", "nav", "header", "footer", "aside", "svg", "noscript"}
        self.current_ignore_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.ignore_tags:
            self.current_ignore_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in self.ignore_tags and self.current_ignore_depth > 0:
            self.current_ignore_depth -= 1

    def handle_data(self, data):
        if self.current_ignore_depth == 0:
            text = data.strip()
            if text:
                self.text_parts.append(text)

    def get_text(self) -> str:
        return " ".join(self.text_parts)


class WebReaderTool:
    """
    网页与代码仓库全文穿透提取工具箱。
    """

    @staticmethod
    def _is_github_repo(url: str) -> Optional[tuple]:
        """
        判断是否是 GitHub 仓库地址，若是则提取 (owner, repo)。
        例如: https://github.com/bytedance/deer-flow -> ('bytedance', 'deer-flow')
        """
        parsed = urllib.parse.urlparse(url)
        if "github.com" in parsed.netloc:
            parts = [p for p in parsed.path.strip("/").split("/") if p]
            if len(parts) >= 2 and parts[0] not in ("topics", "features", "explore", "trending"):
                return parts[0], parts[1]
        return None

    @classmethod
    def fetch_github_readme(cls, owner: str, repo: str) -> Optional[str]:
        """
        【GitHub 原生穿透】：直接抓取官方 README.md 文本全文。
        """
        # 尝试两个最常见的主分支名：main 和 master
        for branch in ("main", "master"):
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
            content = http_get(raw_url, timeout=12)
            if content and len(content) > 100:
                logger.info(f"成功穿透 GitHub 仓库并抓取 README.md 全文 ({owner}/{repo}, 分支 {branch})")
                return content
        return None

    @classmethod
    def fetch_web_article(cls, url: str) -> Optional[str]:
        """
        【官方博客与网页文章穿透】：抓取 HTML 并提取高密度正文。
        """
        raw_html = http_get(url, timeout=15)
        if not raw_html:
            return None

        # 使用 HTML 解析器剥离噪点标签
        parser = SimpleHTMLTextExtractor()
        try:
            parser.feed(raw_html)
            text = parser.get_text()
            # 压缩多余的连续空格和换行
            cleaned = " ".join(text.split())
            return cleaned
        except Exception as e:
            logger.warning(f"解析 HTML 正文失败: {e}")
            # 如果解析失败，使用简单正则兜底
            clean = re.sub(r"<[^>]+>", " ", raw_html)
            return " ".join(clean.split())

    @classmethod
    def read_deep_content(cls, url: str, max_chars: int = 4000) -> Optional[str]:
        """
        【统一穿透入口】：
        自动识别目标链接是 GitHub 还是普通博客网页，获取正文全文，
        并安全截断至设定的最大字符数（默认 4,000 字符），防止撑爆 Token。
        """
        if not url or url == "#":
            return None

        # 1. 尝试 GitHub 专属通道
        gh_info = cls._is_github_repo(url)
        content = None
        if gh_info:
            owner, repo = gh_info
            logger.info(f"🔍 识别到 GitHub 仓库，启动 README 穿透器: {owner}/{repo}")
            content = cls.fetch_github_readme(owner, repo)

        # 2. 如果不是 GitHub，或者 GitHub 抓取失败，走标准文章抽取通道
        if not content:
            logger.info(f"🔍 启动通用网页正文穿透器: {url}")
            content = cls.fetch_web_article(url)

        if not content:
            logger.warning(f"未能抓取到全文正文: {url}")
            return None

        # 3. 安全长度截断防护
        if len(content) > max_chars:
            content = content[:max_chars] + "\n...(全文过长，已做安全防护截断)..."

        return content
