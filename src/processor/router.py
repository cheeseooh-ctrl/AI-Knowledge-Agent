# -*- coding: utf-8 -*-

# ==============================================================================
# 🔀 src/processor/router.py - 多智能体路由调度器 (Agent Router - v1.3.0 记忆赋能版)
#
# 【小白通俗理解】：
# 在 v1.3.0 中，Router 接入了【记忆中枢 (MemoryManager)】：
# 以前它对读者一无所知，也不记得昨天报了什么；
# 现在 Router 会首先向海马体（Memory）调取记忆：
# 1. 记忆过滤：自动找出最近两周已经报过的老新闻，降权防炒冷饭；
# 2. 兴趣对齐：按照读者的专属画像（如喜欢 Agent/MCP，讨厌纯公关融资）进行权重重构；
# 3. 深度研读：对最符合读者兴趣的 Top 3 重磅线索派发 DeepReader 进行全文穿透；
# 4. 专属文风生成：命令 Writer 按照读者的技术偏好语气撰稿，交由 Critic 审核；
# 5. 记忆沉淀：审核通过后，把今天发布的内容登记入库，供明天比对！
# ==============================================================================

import logging
from typing import List, Dict, Any, Optional
from src.collectors.base import NewsItem
from src.memory.memory_manager import MemoryManager
from src.processor.deep_reader_agent import DeepReaderAgent
from src.processor.writer_agent import WriterAgent
from src.processor.critic_agent import CriticAgent
from src.processor.mock_summarizer import MockSummarizer

logger = logging.getLogger("AIAgent.Router")


class AgentRouter:
    """
    多智能体路由调度器 (Agent Router)：
    负责协调 MemoryManager、DeepReaderAgent、WriterAgent 与 CriticAgent 之间的复杂拓扑数据流转。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        pass_threshold: int = 80,
        max_revision_rounds: int = 2,
        deep_reader_enabled: bool = True,
        max_deep_items: int = 3,
        memory_enabled: bool = True,
        user_profile: Optional[Dict[str, Any]] = None,
        history_retention_days: int = 14
    ):
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.pass_threshold = pass_threshold
        self.max_revision_rounds = max_revision_rounds
        self.deep_reader_enabled = deep_reader_enabled
        self.max_deep_items = max_deep_items
        self.memory_enabled = memory_enabled

        # 挂载记忆中枢与三大子智能体
        self.memory = MemoryManager(
            history_retention_days=history_retention_days,
            user_profile=user_profile
        )
        self.deep_reader = DeepReaderAgent(self.api_key, model=self.model)
        self.writer = WriterAgent(self.api_key, model=self.model)
        self.critic = CriticAgent(self.api_key, model=self.model, pass_threshold=self.pass_threshold)
        self.mock_fallback = MockSummarizer()

    def _select_high_value_items(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        【线索研判算法】：从海量条目中挑选最值得启动深度穿透的候选者。
        """
        candidates = []
        for item in items:
            if any(k in item.source for k in ("OpenAI", "Google", "Hugging Face", "GitHub")):
                candidates.append(item)

        if not candidates:
            candidates = items

        return candidates[:self.max_deep_items]

    def route_and_process(self, items: List[NewsItem], report_date: str = "") -> Dict[str, Any]:
        """
        核心路由执行函数：控制数据在记忆、深度穿透与对抗审稿之间的流转。
        """
        suppressed_repeats = 0
        working_items = items

        # ----------------------------------------------------------------------
        # 第零阶段：记忆中枢介入 (Memory-Driven Personalization & Deduplication)
        # ----------------------------------------------------------------------
        if self.memory_enabled:
            logger.info("🧠 【记忆中枢介入】正在调取历史记忆与用户专属技术画像...")
            working_items, suppressed_repeats = self.memory.filter_and_rank_by_preference(items)
            logger.info(
                f"🧠 记忆偏好加权完毕：识别并压制 {suppressed_repeats} 条跨天重复线索，"
                f"读者画像定位为: 【{self.memory.user_profile.get('role', '开发者')}】"
            )

        # 1. 离线/无 API 路由分支
        if not self.api_key:
            logger.info("未检测到 API Key，Router 自动导流至本地 Mock 模拟节点...")
            for top_item in working_items[:self.max_deep_items]:
                self.deep_reader.research_item(top_item)

            result = self.mock_fallback.summarize(working_items)
            result["audit_report"] = {
                "overall_score": 88,
                "rounds": 1,
                "dimension_scores": {"anti_pr": 90, "evidence_density": 88, "actionability": 88, "critical_balance": 86},
                "critique_summary": "【单机模拟模式】通过离线路由校验，符合用户画像偏好。",
                "general_advice": "保持客观严谨。",
                "user_role": self.memory.user_profile.get("role", "开发者"),
                "suppressed_repeats": suppressed_repeats
            }
            if report_date and self.memory_enabled:
                self.memory.record_reported_items(result, report_date)
            return result

        logger.info("🔀 【Agent Router 启动调度】开始分发多智能体协作链路...")

        # ----------------------------------------------------------------------
        # 第一阶段：线索研判与深度穿透派发 (Deep Reading Route)
        # ----------------------------------------------------------------------
        if self.deep_reader_enabled:
            high_value_items = self._select_high_value_items(working_items)
            logger.info(f"🧐 Router 甄选出 {len(high_value_items)} 个重磅线索，启动 DeepReader 深度穿透...")
            for target_item in high_value_items:
                try:
                    self.deep_reader.research_item(target_item)
                except Exception as e:
                    logger.warning(f"穿透调研条目《{target_item.title}》失败: {e}")

        # ----------------------------------------------------------------------
        # 第二阶段：路由给 Writer Agent 撰写第一版草稿（注入画像偏好）
        # ----------------------------------------------------------------------
        draft = self.writer.write_draft(working_items)
        if not draft:
            logger.warning("Writer Agent 未能输出有效内容，Router 降级导流至备用节点")
            draft = self.mock_fallback.summarize(working_items)

        current_round = 1
        audit_history = []

        # ----------------------------------------------------------------------
        # 第三阶段：动态条件循环路由 (Conditional Feedback Loop)
        # ----------------------------------------------------------------------
        while current_round <= self.max_revision_rounds:
            logger.info(f"🔄 Router 分发至 Critic 节点 -> [进行第 {current_round} 轮严格审查]")
            
            # 路由给 Critic Agent 进行四维审计
            audit = self.critic.audit(draft)
            audit["round"] = current_round
            audit_history.append(audit)

            # 条件判断：是否达到放行分数线？
            if audit.get("passed", False):
                logger.info(f"✅ Router 审查判定：第 {current_round} 轮打分达标 ({audit.get('overall_score')} 分)，放行进入发布队列！")
                break

            # 如果未达标，判断是否还可以继续反思迭代
            if current_round < self.max_revision_rounds:
                logger.warning(
                    f"⚠️ Router 审查判定：第 {current_round} 轮未达标 ({audit.get('overall_score')} < {self.pass_threshold})。"
                    f"将批评反馈逆向路由回 Writer 节点进行反思重构！"
                )
                revised_draft = self.writer.revise_draft(draft, audit)
                if revised_draft:
                    draft = revised_draft
                else:
                    logger.warning("Writer 节点未返回修改内容，沿用当前草稿继续流转")
            else:
                logger.warning(f"达到 Router 预设的最大重试上限 ({self.max_revision_rounds} 轮)，终止迭代强制签发。")

            current_round += 1

        # ----------------------------------------------------------------------
        # 第四阶段：终点站——附带全链路质检与记忆档案
        # ----------------------------------------------------------------------
        final_audit = audit_history[-1] if audit_history else {}
        draft["audit_report"] = {
            "overall_score": final_audit.get("overall_score", 85),
            "rounds": len(audit_history),
            "dimension_scores": final_audit.get("dimension_scores", {}),
            "critique_summary": final_audit.get("critique_summary", "审核完成"),
            "critique_details": final_audit.get("critique_details", []),
            "general_advice": final_audit.get("general_advice", "客观严谨"),
            "deep_reader_enabled": self.deep_reader_enabled,
            "memory_enabled": self.memory_enabled,
            "user_role": self.memory.user_profile.get("role", "AI 架构师 / 全栈开发者"),
            "suppressed_repeats": suppressed_repeats
        }

        # ----------------------------------------------------------------------
        # 第五阶段：记忆沉淀入库 (Episodic Memory Persistence)
        # ----------------------------------------------------------------------
        if report_date and self.memory_enabled:
            self.memory.record_reported_items(draft, report_date)

        logger.info("🔀 【Agent Router 调度完成】记忆加权、深度研读与质检博弈全链路达成！")
        return draft


# 保持向后兼容
MultiAgentEditorialBoard = AgentRouter
