# -*- coding: utf-8 -*-

# ==============================================================================
# 🔀 src/processor/router.py - 多智能体路由调度器 (Agent Router - v1.2.0 深度穿透版)
#
# 【小白通俗理解】：
# 在 v1.2.0 中，Router 的调度中枢能力大幅增强：
# 以前它只负责在 Writer 和 Critic 之间击鼓传花；
# 现在它拥有了【线索研判与深度任务派发能力】：
# 1. 甄别重点：从清洗好的 27 条素材中，挑选出最具突破潜力的 Top 3 条重磅线索；
# 2. 派发深度任务：把这 3 条线索派发给 DeepReaderAgent，去真实翻阅网页/README全文；
# 3. 注入一手证据：把 DeepReader 挖到的底层架构和实测数据，塞给 Writer Agent；
# 4. 驱动博弈：组织 Writer 和 Critic 进行审查与反思循环；
# 5. 终点放行：把高质量定稿与质检档案交付给下游发布模块。
# ==============================================================================

import logging
from typing import List, Dict, Any, Optional
from src.collectors.base import NewsItem
from src.processor.deep_reader_agent import DeepReaderAgent
from src.processor.writer_agent import WriterAgent
from src.processor.critic_agent import CriticAgent
from src.processor.mock_summarizer import MockSummarizer

logger = logging.getLogger("AIAgent.Router")


class AgentRouter:
    """
    多智能体路由调度器 (Agent Router)：
    负责协调 DeepReaderAgent、WriterAgent 与 CriticAgent 之间的复杂拓扑数据流转。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        pass_threshold: int = 80,
        max_revision_rounds: int = 2,
        deep_reader_enabled: bool = True,
        max_deep_items: int = 3
    ):
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.pass_threshold = pass_threshold
        self.max_revision_rounds = max_revision_rounds
        self.deep_reader_enabled = deep_reader_enabled
        self.max_deep_items = max_deep_items

        # 挂载受其调度的三大子智能体
        self.deep_reader = DeepReaderAgent(self.api_key, model=self.model)
        self.writer = WriterAgent(self.api_key, model=self.model)
        self.critic = CriticAgent(self.api_key, model=self.model, pass_threshold=self.pass_threshold)
        self.mock_fallback = MockSummarizer()

    def _select_high_value_items(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        【线索研判算法】：从海量条目中智能挑选最值得启动深度穿透的候选者。
        优先级：官方博客要闻 > 高星 GitHub 核心库 > 高赞学术论文。
        """
        # 优先挑官方来源和高分条目
        candidates = []
        for item in items:
            # 官方信源、或者 GitHub 顶级项目、或者 HF 论文
            if any(k in item.source for k in ("OpenAI", "Google", "Hugging Face", "GitHub")):
                candidates.append(item)

        # 如果没有匹配到特定源，直接按热度排序前几个
        if not candidates:
            candidates = items

        return candidates[:self.max_deep_items]

    def route_and_process(self, items: List[NewsItem]) -> Dict[str, Any]:
        """
        核心路由执行函数：控制数据在各个 Sub-Agent 之间的流转。
        """
        # 1. 离线/无 API 路由分支
        if not self.api_key:
            logger.info("未检测到 API Key，Router 自动导流至本地 Mock 模拟节点...")
            # 同样为 Mock 注入深度穿透模拟数据
            for top_item in items[:self.max_deep_items]:
                self.deep_reader.research_item(top_item)

            result = self.mock_fallback.summarize(items)
            result["audit_report"] = {
                "overall_score": 88,
                "rounds": 1,
                "dimension_scores": {"anti_pr": 90, "evidence_density": 88, "actionability": 88, "critical_balance": 86},
                "critique_summary": "【单机模拟模式】通过离线路由校验，已注入模拟深度技术参数。",
                "general_advice": "保持客观严谨。"
            }
            return result

        logger.info("🔀 【Agent Router 启动调度】开始分发多智能体协作链路...")

        # ----------------------------------------------------------------------
        # 第一阶段：线索研判与深度穿透派发 (Deep Reading Route)
        # ----------------------------------------------------------------------
        if self.deep_reader_enabled:
            high_value_items = self._select_high_value_items(items)
            logger.info(f"🧐 Router 甄选出 {len(high_value_items)} 个重磅线索，启动 DeepReader 深度穿透...")
            for target_item in high_value_items:
                try:
                    self.deep_reader.research_item(target_item)
                except Exception as e:
                    logger.warning(f"穿透调研条目《{target_item.title}》失败: {e}")

        # ----------------------------------------------------------------------
        # 第二阶段：路由给 Writer Agent 撰写第一版草稿
        # ----------------------------------------------------------------------
        draft = self.writer.write_draft(items)
        if not draft:
            logger.warning("Writer Agent 未能输出有效内容，Router 降级导流至备用节点")
            draft = self.mock_fallback.summarize(items)

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
        # 第四阶段：终点站——附带全链路质检档案，打包交付下游 Exporter
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
        }

        logger.info("🔀 【Agent Router 调度完成】全链路深度穿透与多轮博弈质检完毕，数据流向发布器！")
        return draft


# 保持向后兼容
MultiAgentEditorialBoard = AgentRouter
