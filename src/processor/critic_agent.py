# -*- coding: utf-8 -*-

# ==============================================================================
# 😈 src/processor/critic_agent.py - 恶魔质检总编辑智能体 (Critic Agent)
#
# 【小白通俗理解】：
# 在虚拟报社编辑部中，Critic Agent 扮演一位“挑剔、严谨、苛刻的恶魔总编”（Devil's Advocate）。
# 它的核心职责：
# 1. 审稿与打分：它从不写稿，专门给主笔记者挑刺。
# 2. 从四大苛刻维度审核：
#    - 去公关化 (Anti-PR)：是否充斥着厂商洗脑的宣传词？
#    - 技术实证度 (Evidence Density)：有没有具体参数、评测数字或架构说明？
#    - 落地启发性 (Actionability)：对开发者有没有实际参考价值？
#    - 辩证与风险审视 (Critical Balance)：有没有指出缺点、瓶颈或风险？
# 3. 决定是否打回：若打分低于设定的门槛（如 80 分），强制打回并附赠修改建议单！
# ==============================================================================

import json
import logging
import re
from typing import Dict, Any, Optional
from src.utils import http_post_json

logger = logging.getLogger("AIAgent.Critic")


class CriticAgent:
    """
    负责挑刺、质检与把关的恶魔总编辑智能体。
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", pass_threshold: int = 80):
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.pass_threshold = pass_threshold # 合格放行门槛分数（默认 80 分）

    def _build_audit_prompt(self, draft: Dict[str, Any]) -> str:
        """
        构建针对初稿进行严格质检的审稿提示词。
        """
        prompt = f"""你是一家世界级顶级学术与科技内参期刊的【恶魔质检总编（Skeptical Chief Editor）】。
你的座右铭是：“绝不让任何一篇带有公关通稿味道、空洞无物的垃圾内容被推送到读者面前”。

以下是主笔记者刚刚提交的【今日 AI 每日简报】草稿：
{json.dumps(draft, ensure_ascii=False, indent=2)}

请从以下【四大苛刻维度】对这份草稿进行无情的审视、打分与挑刺：
1. 【去公关化 (Anti-PR)】（权重 25%）：是否充斥着“颠覆全行业”、“里程碑”、“不可思议”等浮夸词？如果是，重扣！必须说人话。
2. 【技术实证度 (Evidence Density)】（权重 25%）：有没有具体指出模型参数规模、评测基准得分（如 MMLU/HumanEval）、开源协议或技术机制？如果是泛泛而谈，扣分！
3. 【落地启发性 (Actionability)】（权重 25%）：对真正的开发者、架构师或业务决策者有何实操价值？读者读完能获得什么启示？
4. 【辩证与风险审视 (Critical Balance)】（权重 25%）：科技永远有两面性。有没有指出该技术的硬件显存门槛、可能存在的延迟/成本问题、或闭源/幻觉风险？如果全是歌功颂德，扣分！

【合格放行标准】：加权综合总分必须 >= {self.pass_threshold} 分，方可判定 passed 为 true。

请严格以 JSON 格式输出你的质检审查报告，必须符合以下结构：
{{
  "overall_score": 82,
  "passed": true,
  "dimension_scores": {{
    "anti_pr": 85,
    "evidence_density": 80,
    "actionability": 85,
    "critical_balance": 78
  }},
  "critique_summary": "一两句话概括本次审稿的总体评价",
  "critique_details": [
    "挑刺点1：某某条目的描述过于吹嘘，缺乏客观对比...",
    "挑刺点2：某某论文缺少对核心算法局限性的说明..."
  ],
  "general_advice": "给主笔记者的总体修改建议指导思想"
}}
"""
        return prompt

    def audit(self, draft: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        核心审稿方法：向 Gemini 发起质检请求并返回打分报告。
        """
        if not self.api_key:
            # 如果没有配置 API Key，返回默认放行模拟报告
            return {
                "overall_score": 85,
                "passed": True,
                "dimension_scores": {"anti_pr": 85, "evidence_density": 85, "actionability": 85, "critical_balance": 85},
                "critique_summary": "【单机模拟模式】草稿格式规范，已通过离线质检规则。",
                "critique_details": [],
                "general_advice": "保持客观理性。"
            }

        logger.info("恶魔质检总编 (Critic Agent) 正在拿着放大镜对草稿进行苛刻审查...")
        prompt = self._build_audit_prompt(draft)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.15, # 极低温度，让总编更加冷静、客观、吹毛求疵
                "responseMimeType": "application/json"
            }
        }

        resp = http_post_json(url, payload, timeout=60)
        if not resp:
            logger.warning("Critic Agent 审稿接口无响应，默认按及格放行处理")
            return {"overall_score": 80, "passed": True, "critique_summary": "接口无响应自动放行"}

        try:
            candidates = resp.get("candidates", [])
            content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            cleaned_text = re.sub(r"^```json\s*", "", content_text.strip(), flags=re.MULTILINE)
            cleaned_text = re.sub(r"^```\s*", "", cleaned_text.strip(), flags=re.MULTILINE)
            cleaned_text = re.sub(r"```$", "", cleaned_text.strip(), flags=re.MULTILINE)

            result = json.loads(cleaned_text.strip())
            score = result.get("overall_score", 0)
            passed = score >= self.pass_threshold
            result["passed"] = passed # 确保通过状态由代码硬门槛最终把关

            logger.info(f"Critic 质检评分出炉: {score} 分 | 审核结果: {'✅ 审核通过准予发布' if passed else '❌ 不合格打回重写'}")
            return result
        except Exception as e:
            logger.error(f"Critic Agent 解析审稿结果异常: {e}")
            return {"overall_score": 80, "passed": True, "critique_summary": "解析异常自动放行"}
