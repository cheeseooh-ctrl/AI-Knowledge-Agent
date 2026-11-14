# -*- coding: utf-8 -*-

# ==============================================================================
# 🔀 src/processor/router.py - 多智能体路由调度器 (Agent Router)
#
# 【小白通俗理解】：
# 在计算机与智能体架构中，"Router" (路由器/调度器) 就像是十字路口的交警或中枢调度员。
# 它本身不生产内容，它的核心职责是：【根据状态，把数据导流给不同的智能体】。
# 
# 它的路由流转逻辑非常清晰：
# 1. 路由给生产节点：把清洗好的原始素材 -> 路由给 Writer Agent (负责写稿)
# 2. 路由给审查节点：把初稿 -> 路由给 Critic Agent (负责打分挑刺)
# 3. 条件分流判断 (Conditional Routing)：
#    - 如果质检合格 (Score >= 80) -> 路由流向终点，交给 Exporter 发布！
#    - 如果质检不合格 (Score < 80) -> 把错误反馈原路路由打回给 Writer Agent，开始第二轮重写！
# ==============================================================================

import logging
from typing import List, Dict, Any, Optional
from src.collectors.base import NewsItem
from src.processor.writer_agent import WriterAgent
from src.processor.critic_agent import CriticAgent
from src.processor.mock_summarizer import MockSummarizer

logger = logging.getLogger("AIAgent.Router")


class AgentRouter:
    """
    多智能体路由调度器 (Agent Router)：
    负责在 Writer Agent 与 Critic Agent 之间进行任务分发、条件分支判断与回环路由。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        pass_threshold: int = 80,
        max_revision_rounds: int = 2
    ):
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.pass_threshold = pass_threshold
        self.max_revision_rounds = max_revision_rounds

        # 挂载受其调度的子智能体
        self.writer = WriterAgent(self.api_key, model=self.model)
        self.critic = CriticAgent(self.api_key, model=self.model, pass_threshold=self.pass_threshold)
        self.mock_fallback = MockSummarizer()

    def route_and_process(self, items: List[NewsItem]) -> Dict[str, Any]:
        """
        核心路由执行函数：控制数据在各个 Sub-Agent 之间的流转。
        """
        # 1. 离线/无 API 路由分支
        if not self.api_key:
            logger.info("未检测到 API Key，Router 自动导流至本地 Mock 模拟节点...")
            result = self.mock_fallback.summarize(items)
            result["audit_report"] = {
                "overall_score": 88,
                "rounds": 1,
                "dimension_scores": {"anti_pr": 90, "evidence_density": 85, "actionability": 88, "critical_balance": 88},
                "critique_summary": "【单机模拟模式】通过离线路由校验，符合输出标准。",
                "general_advice": "保持精炼客观。"
            }
            return result

        logger.info("🔀 【Agent Router 启动调度】开始分发多智能体协作链路...")

        # 2. 第一站：路由给 Writer Agent 撰写第一版草稿
        draft = self.writer.write_draft(items)
        if not draft:
            logger.warning("Writer Agent 未能输出有效内容，Router 降级导流至备用节点")
            draft = self.mock_fallback.summarize(items)

        current_round = 1
        audit_history = []

        # 3. 动态条件循环路由 (Conditional Feedback Loop)
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

        # 4. 终点站：附带全链路质检档案，打包交付下游 Exporter
        final_audit = audit_history[-1] if audit_history else {}
        draft["audit_report"] = {
            "overall_score": final_audit.get("overall_score", 85),
            "rounds": len(audit_history),
            "dimension_scores": final_audit.get("dimension_scores", {}),
            "critique_summary": final_audit.get("critique_summary", "审核完成"),
            "critique_details": final_audit.get("critique_details", []),
            "general_advice": final_audit.get("general_advice", "客观严谨"),
        }

        logger.info("🔀 【Agent Router 调度完成】全链路质检完毕，数据正式流向发布器！")
        return draft


# 保持向后兼容（防止老代码引用报错）
MultiAgentEditorialBoard = AgentRouter
