# -*- coding: utf-8 -*-

# ==============================================================================
# 🧠 src/memory/memory_manager.py - 个性化记忆中枢 (Personalized Memory Manager)
#
# 【小白通俗理解】：
# 这个文件是 Agent 的“海马体与记事本”。
# 在没有记忆中枢前，Agent 有两大硬伤：
# 1. 健忘症（跨天重复）：今天报了 Dify，明天 Dify 还在榜上，它又一字不差地报一遍；
# 2. 大锅饭（千人一面）：不管读者是搞算法的、写前端的还是投资人，输出的内容千篇一律。
# 
# 有了 MemoryManager，它实现了双层记忆机制：
# 1. 【长期情景记忆 (Episodic History)】：自动记录过去 14 天报道过的新闻指纹，
#    发现连番上榜的内容自动降权或标记为“持续进展追踪”，彻底告别炒冷饭；
# 2. 【语义用户画像 (User Profile Memory)】：记住你的专属角色（如 AI 架构师）、
#    核心兴趣词（如 Agent, MCP, 本地模型）以及讨厌的话题（如 纯融资公关、元宇宙），
#    在清洗阶段为你的专属兴趣进行精准加权，实现真正的千人千面！
# ==============================================================================

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set, Tuple, Optional
from src.collectors.base import NewsItem

logger = logging.getLogger("AIAgent.Memory")


class MemoryManager:
    """
    负责管理用户画像偏好与跨天历史事件去重的记忆中枢管理器。
    """

    def __init__(
        self,
        memory_dir: str = "./data/memory",
        history_retention_days: int = 14,
        user_profile: Optional[Dict[str, Any]] = None
    ):
        self.memory_dir = memory_dir
        self.history_retention_days = history_retention_days
        self.history_file = os.path.join(self.memory_dir, "reported_history.json")
        self.profile_file = os.path.join(self.memory_dir, "user_profile.json")

        # 确保数据存储目录存在
        os.makedirs(self.memory_dir, exist_ok=True)

        # 1. 初始化或加载用户偏好画像
        self.user_profile = self._load_or_init_profile(user_profile)

        # 2. 加载历史已报道事件指纹字典 {item_hash: {"title": ..., "date": ...}}
        self.history = self._load_history()

    def _load_or_init_profile(self, default_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """加载或初始化用户专属画像"""
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"读取用户画像文件失败: {e}")

        # 默认的高质量技术架构师画像
        profile = default_profile or {
            "role": "AI 架构师 / 全栈开发者",
            "interests": ["agent", "mcp", "local-models", "rag", "open-source", "tool-use"],
            "disliked_topics": ["crypto", "nft", "funding-only", "metaverse", "web3"],
            "tone_preference": "极客硬核、重实战、无公关套话"
        }

        # 保存到本地文件
        try:
            with open(self.profile_file, "w", encoding="utf-8") as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"初始化用户画像写入失败: {e}")

        return profile

    def _load_history(self) -> Dict[str, Any]:
        """加载并自动清理超期的历史报道指纹"""
        if not os.path.exists(self.history_file):
            return {}

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"读取历史记忆文件失败: {e}")
            return {}

        # 自动修剪：淘汰超过 retention_days 的老记忆
        cutoff_date = (datetime.now() - timedelta(days=self.history_retention_days)).strftime("%Y-%m-%d")
        cleaned_history = {}
        for h, info in data.items():
            if info.get("reported_date", "") >= cutoff_date:
                cleaned_history[h] = info

        return cleaned_history

    def _save_history(self):
        """将更新后的历史记忆持久化到硬盘"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"持久化历史记忆失败: {e}")

    @staticmethod
    def compute_fingerprint(item: NewsItem) -> str:
        """
        计算条目的唯一语义指纹（基于规范化 URL 或 核心标题）。
        使用 MD5 散列保证短小且唯一。
        """
        raw_key = f"{item.url.strip().lower()}_{item.title.strip().lower()[:30]}"
        return hashlib.md5(raw_key.encode("utf-8")).hexdigest()

    def filter_and_rank_by_preference(self, items: List[NewsItem]) -> Tuple[List[NewsItem], int]:
        """
        【记忆中枢核心赋能】：
        1. 识别并降权/过滤最近 7~14 天已经报道过的内容（避免炒冷饭）；
        2. 根据 User Profile 的兴趣标签进行加权提权；
        3. 对包含负面排斥词（如纯区块链、纯融资报道）的内容进行强力降权或剔除。
        返回：(个性化排序后的条目列表, 过滤掉的重复炒冷饭条目数)
        """
        interests = [w.lower() for w in self.user_profile.get("interests", [])]
        dislikes = [w.lower() for w in self.user_profile.get("disliked_topics", [])]

        filtered_items = []
        suppressed_repeat_count = 0

        for item in items:
            fingerprint = self.compute_fingerprint(item)
            content_corpus = f"{item.title} {item.summary}".lower()

            # ------------------------------------------------------------------
            # 规则 1：检查是否是最近刚报过的“重复炒冷饭”
            # ------------------------------------------------------------------
            if fingerprint in self.history:
                last_info = self.history[fingerprint]
                # 记录为重复内容并进行大幅度降权（减 80% 得分）
                item.score = int(item.score * 0.2)
                item.metadata["repeat_tracking"] = True
                item.metadata["first_reported_date"] = last_info.get("reported_date")
                suppressed_repeat_count += 1
                logger.info(f"🔁 记忆中枢识别到已报道历史线索: 《{item.title}》 (初次收录: {last_info.get('reported_date')})")

            # ------------------------------------------------------------------
            # 规则 2：用户厌恶话题过滤 (Disliked Topics Penalty)
            # ------------------------------------------------------------------
            has_dislike = any(d in content_corpus for d in dislikes)
            if has_dislike:
                # 命中讨厌话题，直接斩首 90% 得分或跳过
                item.score = int(item.score * 0.1)
                item.metadata["dislike_penalized"] = True

            # ------------------------------------------------------------------
            # 规则 3：用户专属兴趣加权 (Personalized Boost)
            # ------------------------------------------------------------------
            interest_hits = sum(1 for w in interests if w in content_corpus)
            if interest_hits > 0:
                # 命中兴趣点，给予阶梯式加分奖励 (每命中一个加成 25%)
                boost_multiplier = 1.0 + min(interest_hits * 0.25, 1.0)
                item.score = int(item.score * boost_multiplier)
                item.metadata["interest_boost"] = f"+{int((boost_multiplier - 1.0)*100)}%"

            filtered_items.append(item)

        # 重新根据个性化加权后的分数进行总排序
        filtered_items.sort(key=lambda x: x.score, reverse=True)
        return filtered_items, suppressed_repeat_count

    def record_reported_items(self, items_or_draft: Any, report_date: str):
        """
        在早报发布完毕后，将最终登报的条目记录入长期记忆库，供明后天比对。
        """
        count = 0
        # 兼容处理字典结构中的条目
        if isinstance(items_or_draft, dict):
            # 从各分类中提取 URL 和 Title
            candidate_list = []
            for sec in ("breakthroughs", "open_source_tools", "trending_papers", "hot_discussions"):
                for it in items_or_draft.get(sec, []):
                    candidate_list.append(it)

            for c in candidate_list:
                title = c.get("title") or c.get("name") or ""
                url = c.get("url") or "#"
                if url and url != "#":
                    fake_item = NewsItem(title=title, url=url, source="digest")
                    fp = self.compute_fingerprint(fake_item)
                    self.history[fp] = {
                        "title": title,
                        "url": url,
                        "reported_date": report_date
                    }
                    count += 1
        elif isinstance(items_or_draft, list):
            for item in items_or_draft:
                fp = self.compute_fingerprint(item)
                self.history[fp] = {
                    "title": item.title,
                    "url": item.url,
                    "reported_date": report_date
                }
                count += 1

        self._save_history()
        logger.info(f"🧠 [长期记忆沉淀] 今日已成功将 {count} 条精选情报登记入历史记忆库 (存留期: {self.history_retention_days} 天)")
