# -*- coding: utf-8 -*-

# ==============================================================================
# ✍️ src/processor/writer_agent.py - 主笔撰稿记者智能体 (Writer Agent)
#
# 【小白通俗理解】：
# 在虚拟报社编辑部中，Writer Agent 是“科技主笔记者”。
# 它的核心职责：
# 1. 负责初稿撰写：通读原始素材（特别是包含 Deep Reader 挖掘出来的深度正文细节），
#    用生动专业的技术语言撰写第一版草稿。
# 2. 负责修改重写：当后面的“恶魔质检员 (Critic Agent)”对草稿提出挑刺和修改意见时，
#    主笔必须虚心接受批评，针对性地补充实测数据、删掉夸大其词的公关词汇，完成二次打磨。
# ==============================================================================

import json
import logging
import re
from typing import List, Dict, Any, Optional
from src.collectors.base import NewsItem
from src.utils import http_post_json

logger = logging.getLogger("AIAgent.Writer")


class WriterAgent:
    """
    负责撰写与修改初稿的记者智能体。
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key.strip()
        self.model = model.strip()

    def _build_draft_prompt(self, items: List[NewsItem]) -> str:
        """
        构建初稿撰写的提示词。
        自动整合 DeepReaderAgent 穿透挖掘出的深度技术架构、实测跑分与缺陷局限。
        """
        condensed_items = []
        for i, item in enumerate(items, 1):
            entry = {
                "id": i,
                "title": item.title,
                "url": item.url,
                "source": item.source,
                "score": item.score,
                "snippet": item.summary[:300] if item.summary else "",
            }
            # 如果深度穿透研究员已经扒到了网页全文硬核真相，直接注入给主笔
            if "deep_research" in item.metadata:
                entry["deep_technical_facts"] = item.metadata["deep_research"]

            condensed_items.append(entry)

        prompt = f"""你是一家全球顶级技术媒体的【资深科技主笔记者】。
你的任务是将以下今天搜集到的 AI 动态（部分重要项目已附带【深度穿透硬核细节 deep_technical_facts】），
撰写成一份高质量、有深度、易读的【今日 AI 每日简报】初稿。

【输入素材列表】：
{json.dumps(condensed_items, ensure_ascii=False, indent=2)}

【撰写特别要求】：
1. 优先消化深度事实：对于带有 `deep_technical_facts` 的条目，必须将具体跑分数字、底层架构创新与已知缺陷/局限性自然地融合进 key_points 和 why_it_matters 中！
2. 严禁空洞的公关辞令：少用“史诗级”、“颠覆全行业”等虚词，多讲实际技术方案与架构改变。
3. 严格以 JSON 格式输出，不要包含任何闲聊开场白。

【JSON 必须符合以下结构】：
{{
  "daily_focus": "今日核心大势（一句话概括今天最重要的技术风向，20~40字）",
  "breakthroughs": [
    {{
      "title": "中文通俗且专业的标题",
      "original_title": "英文原标题",
      "url": "原文链接",
      "source": "信源",
      "why_it_matters": "核心价值与行业影响（结合实测数据说明为什么值得关注）",
      "key_points": [
        "核心架构与机制要点",
        "实测跑分/参数/硬件指标",
        "已知短板与局限性思考"
      ],
      "has_deep_dive": true
    }}
  ],
  "open_source_tools": [
    {{
      "name": "项目名称",
      "url": "代码仓库链接",
      "stars_or_tag": "如: ⭐️ 1,200 | Python",
      "description": "一两句话准确说明该工具解决了什么痛点、核心亮点"
    }}
  ],
  "trending_papers": [
    {{
      "title": "中文论文标题",
      "original_title": "英文原标题",
      "url": "论文链接",
      "takeaway": "核心创新点与实证结论"
    }}
  ],
  "hot_discussions": [
    {{
      "title": "讨论主题",
      "url": "链接",
      "summary": "社区核心观点与避坑经验"
    }}
  ]
}}
"""
        return prompt

    def _build_revision_prompt(self, current_draft: Dict[str, Any], feedback: Dict[str, Any]) -> str:
        """
        构建根据质检员挑刺意见进行修改重写的提示词。
        """
        prompt = f"""你是一家全球顶级技术媒体的【资深科技主笔记者】。
你刚才撰写的初稿，被【恶魔质检总编辑 (Critic Agent)】严厉打回了！
质检总编的综合评分为：{feedback.get('score', 0)} / 100 分。

【质检总编的挑刺与修改意见】：
{json.dumps(feedback.get('critique_details', []), ensure_ascii=False, indent=2)}
总体修改指导思想：{feedback.get('general_advice', '去公关化，增加实证数据与客观辩证思考')}

【你刚才撰写的上一版草稿】：
{json.dumps(current_draft, ensure_ascii=False, indent=2)}

【你的重写改版任务】：
请针对质检总编提出的所有挑刺点进行针对性重构：
1. 删去所有浮夸辞令，换成具体的数字、指标、架构名或官方声明；
2. 如果缺少局限性说明，请在 key_points 里主动指出该技术的潜在瓶颈（如：显存消耗、代码尚未完全开源、推理时延等）；
3. 严格输出修改后的完整 JSON 数据，保持相同的数据结构。
"""
        return prompt

    def _call_gemini(self, prompt: str) -> Optional[Dict[str, Any]]:
        """底层通用的 Gemini API 发送与 JSON 安全解析"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.25,
                "responseMimeType": "application/json"
            }
        }
        resp = http_post_json(url, payload, timeout=60)
        if not resp:
            return None

        try:
            candidates = resp.get("candidates", [])
            if not candidates:
                return None
            content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            cleaned_text = re.sub(r"^```json\s*", "", content_text.strip(), flags=re.MULTILINE)
            cleaned_text = re.sub(r"^```\s*", "", cleaned_text.strip(), flags=re.MULTILINE)
            cleaned_text = re.sub(r"```$", "", cleaned_text.strip(), flags=re.MULTILINE)
            return json.loads(cleaned_text.strip())
        except Exception as e:
            logger.error(f"Writer Agent 解析 JSON 异常: {e}")
            return None

    def write_draft(self, items: List[NewsItem]) -> Optional[Dict[str, Any]]:
        """动作 1：撰写初稿"""
        logger.info("主笔记者 (Writer Agent) 正在吸收素材与深度穿透事实，撰写第一版草稿...")
        prompt = self._build_draft_prompt(items)
        return self._call_gemini(prompt)

    def revise_draft(self, current_draft: Dict[str, Any], feedback: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """动作 2：针对质检员意见重构草稿"""
        logger.info("主笔记者 (Writer Agent) 正在吸收质检总编的挑刺意见，深度重写润色...")
        prompt = self._build_revision_prompt(current_draft, feedback)
        return self._call_gemini(prompt)
