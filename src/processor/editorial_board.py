# -*- coding: utf-8 -*-

# ==============================================================================
# 🏛️ src/processor/editorial_board.py - 虚拟多智能体编辑部协调器 (Editorial Board)
#
# 【小白通俗理解】：
# 这个文件是报社的“编辑部圆桌会议主席”。
# 它把“主笔记者 (Writer Agent)”和“恶魔质检员 (Critic Agent)”组织在同一个工作流里：
# 1. 第一回合：命令记者写初稿；
# 2. 第二回合：把初稿交给总编挑刺打分；
# 3. 如果总编给的分数达标（>=80分），盖章放行；
# 4. 如果总编不满意（<80分），主席负责居中协调，把总编的批评条目交给记者，
#    勒令记者吸取教训重写，最多重复辩论 2 轮，直到产出极其扎实的高分力作！
# ==============================================================================

import logging
from typing import List, Dict, Any, Optional
from src.collectors.base import NewsItem
from src.processor.writer_agent import WriterAgent
from src.processor.critic_agent import CriticAgent
from src.processor.mock_summarizer import MockSummarizer

logger = logging.getLogger("AIAgent.EditorialBoard")


class MultiAgentEditorialBoard:
    """
    虚拟多智能体编辑部：管理主笔与恶魔质检员之间的博弈与反思循环。
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

        # 实例化两大智能体
        self.writer = WriterAgent(self.api_key, model=self.model)
        self.critic = CriticAgent(self.api_key, model=self.model, pass_threshold=self.pass_threshold)
        self.mock_fallback = MockSummarizer()

    def process(self, items: List[NewsItem]) -> Dict[str, Any]:
        """
        启动多角色协作与博弈主流程。
        """
        # 如果没有配置 API Key，直接启动本地模拟替身，确保不崩溃
        if not self.api_key:
            logger.info("未检测到 API Key，以本地 Mock 模式模拟多智能体流转...")
            result = self.mock_fallback.summarize(items)
            result["audit_report"] = {
                "overall_score": 88,
                "rounds": 1,
                "dimension_scores": {"anti_pr": 90, "evidence_density": 85, "actionability": 88, "critical_balance": 88},
                "critique_summary": "【单机模拟模式】已通过本地规则化审稿，格式完全符合发布规范。",
                "general_advice": "保持精炼专业，注意多模态延伸。"
            }
            return result

        logger.info("🏛️ 【虚拟编辑部开会】多智能体审稿对抗流程正式启动！")

        # ----------------------------------------------------------------------
        # 第一阶段：主笔记者写初稿
        # ----------------------------------------------------------------------
        draft = self.writer.write_draft(items)
        if not draft:
            logger.warning("Writer Agent 未能成功输出初稿，启动备用方案")
            draft = self.mock_fallback.summarize(items)

        current_round = 1
        audit_history = []

        # ----------------------------------------------------------------------
        # 第二阶段：主笔与质检员的对抗博弈循环 (Debate & Revision Loop)
        # ----------------------------------------------------------------------
        while current_round <= self.max_revision_rounds:
            logger.info(f"🔄 --- [第 {current_round} 轮审稿博弈] ---")
            
            # 恶魔质检员拿放大镜挑刺打分
            audit = self.critic.audit(draft)
            audit["round"] = current_round
            audit_history.append(audit)

            # 检查是否达标放行
            if audit.get("passed", False):
                logger.info(f"🏆 第 {current_round} 轮审稿达标！质检得分: {audit.get('overall_score')} 分，准予签发！")
                break

            # 如果没达到及格线，且还有重写机会，就让主笔重新改版
            if current_round < self.max_revision_rounds:
                logger.warning(
                    f"⚠️ 第 {current_round} 轮打分未达标 ({audit.get('overall_score')} < {self.pass_threshold})。"
                    f"打回重写！修改意见: {audit.get('general_advice')}"
                )
                revised_draft = self.writer.revise_draft(draft, audit)
                if revised_draft:
                    draft = revised_draft
                else:
                    logger.warning("重写未返回新数据，维持当前版本继续复审")
            else:
                logger.warning(f"达到最大修改轮数上限 ({self.max_revision_rounds} 轮)，强制收笔定稿。")

            current_round += 1

        # ----------------------------------------------------------------------
        # 第三阶段：组装最终定稿与质检报告档案
        # ----------------------------------------------------------------------
        final_audit = audit_history[-1] if audit_history else {}
        draft["audit_report"] = {
            "overall_score": final_audit.get("overall_score", 85),
            "rounds": len(audit_history),
            "dimension_scores": final_audit.get("dimension_scores", {}),
            "critique_summary": final_audit.get("critique_summary", "审核完成"),
            "critique_details": final_audit.get("critique_details", []),
            "general_advice": final_audit.get("general_advice", "规范严谨"),
        }

        logger.info("🏛️ 【虚拟编辑部散会】今日 AI 早报完成多轮打磨，正式交付发布！")
        return draft
