# -*- coding: utf-8 -*-

# ==============================================================================
# 🧹 src/processor/cleaner.py - 数据清洗与去重器（保洁部）
#
# 【小白通俗理解】：
# 采集员从网上捞回来的原始数据，就像是刚从地里拔出来的土豆，带着很多泥沙：
# 1. 链接后面带着一长串追踪尾巴（如 ?utm_source=twitter...）
# 2. 不同的渠道报道了同一件事，标题大同小异（重复信息）
# 3. 有的信息质量高，有的信息只是水贴
# 这个脚本负责把泥沙洗掉：剁掉追踪尾巴、合并重复新闻、按照热度从高到低排好队，
# 只有干干净净、最有价值的数据，才会被端给后续的大模型去深度提炼。
# ==============================================================================

import re             # 正则表达式工具：用来做高级的文本模式匹配与替换
import urllib.parse   # 网址解析工具：能把一个完整的 URL 拆解成协议、域名、路径和参数
from typing import List, Set
from src.collectors.base import NewsItem # 统一的新闻数据盒子


def normalize_url(url: str) -> str:
    """
    【URL 归一化（剁掉追踪尾巴）】：
    很多网站为了追踪用户来源，会在网址后面加上尾巴，比如：
    原网址：https://example.com/ai?utm_source=twitter&utm_medium=social&ref=123
    如果直接去重，它和从微信分享出来的链接会被误判为两个不同的网页！
    这个函数负责把所有 utm_ 开头、ref、fbclid、gclid 等广告和追踪参数通通剥离，
    还原出最纯净的唯一原始网址：https://example.com/ai
    """
    try:
        # 把网址肢解为 6 个部分：协议、域名、路径、参数、查询条件、锚点
        parsed = urllib.parse.urlparse(url)
        # 把查询字符串（?后面的部分）解析成字典，例如 {'utm_source': ['twitter'], 'id': ['123']}
        query_dict = urllib.parse.parse_qs(parsed.query)

        # 核心过滤：只要这个参数名字不是以 utm_ 开头，也不是 ref / 广告追踪，就保留它
        cleaned_query = {
            k: v for k, v in query_dict.items()
            if not k.startswith("utm_") and k not in ("ref", "fbclid", "gclid")
        }

        # 重新把纯净的各个部分拼装回一个标准的新网址
        clean_url = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/"), # 顺便去掉路径末尾多余的斜杠 /
            parsed.params,
            urllib.parse.urlencode(cleaned_query, doseq=True),
            "" # 剥离锚点
        ))
        return clean_url
    except Exception:
        # 如果解析中途遇到什么奇葩格式，就直接简单去掉末尾空格返回，保证不崩溃
        return url.strip().rstrip("/")


def clean_and_deduplicate(items: List[NewsItem]) -> List[NewsItem]:
    """
    【双重清洗去重与质量排序核心流水线】：
    输入：一大批可能存在重复、杂乱的新闻数据列表
    输出：精选去重后、按照质量打分从高到低排好序的纯净数据列表
    """
    seen_urls: Set[str] = set()    # 用来记录“已经收录过的纯净网址”集合（哈希表，查重极快）
    seen_titles: Set[str] = set()  # 用来记录“已经收录过的简化标题”集合
    cleaned_items: List[NewsItem] = []

    for item in items:
        # ----------------------------------------------------------------------
        # 过滤关卡 1：通过归一化后的纯净 URL 去重
        # ----------------------------------------------------------------------
        norm_url = normalize_url(item.url)
        if norm_url in seen_urls:
            # 如果这个网址之前已经收录过，说明是重复新闻，直接扔掉
            continue

        # ----------------------------------------------------------------------
        # 过滤关卡 2：通过消除大小写和标点后的“极简标题”去重
        # ----------------------------------------------------------------------
        # 例如："Show HN: Juggler!" 和 "juggler" 可能会被识别为讲同一件事
        simplified_title = re.sub(r"[^\w\s]", "", item.title.lower()).strip()
        if simplified_title in seen_titles:
            continue

        # 如果通过了上面两重考验，就把它记入黑名单，并放入最终的合格列表中
        seen_urls.add(norm_url)
        seen_titles.add(simplified_title)
        cleaned_items.append(item)

    # --------------------------------------------------------------------------
    # 质量排序：按照 score（点赞数、Star数）从大到小降序排列
    # 这样能保证排在前面的永远是全球最具热度、最有影响力的内容
    # --------------------------------------------------------------------------
    cleaned_items.sort(key=lambda x: x.score, reverse=True)
    return cleaned_items
