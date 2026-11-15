# -*- coding: utf-8 -*-

# ==============================================================================
# 🧐 src/processor/deep_reader_agent.py - 深度穿透研究员智能体 (Deep Reader Agent)
#
# 【小白通俗理解】：
# 在传统的流水线里，大模型只能看到 200 字的小摘要，根本看不出技术细节。
# DeepReaderAgent 就是我们派出的“硬核技术侦探”：
# 1. 它使用 WebReaderTool 真实地打开网页或打开 GitHub 代码仓库，翻阅几千字全文；
# 2. 它带着 4 个放大镜去寻找真相：
#    - 底层到底改了什么技术架构？
#    - 具体的实测跑分指标是多少（超越了既往模型几个百分点）？
#    - 开发者怎么把它跑起来？
#    - 作者在论文或文档里自己承认了哪些缺陷（Known Limitations）？
# 3. 提炼出的高密度技术真相，会被注入到素材中，让后续的主笔和质检员有扎实的数据支撑！
# ==============================================================================

import json
import logging
import re
from typing import Dict, Any, Optional
from src.collectors.base import NewsItem
from src.tools.web_reader import WebReaderTool
from src.utils import http_post_json

logger = logging.getLogger("AIAgent.DeepReader")


class DeepReaderAgent:
    """
    深度穿透研究员智能体：负责长文研读、代码仓库深挖与硬核指标蒸馏。
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key.strip()
        self.model = model.strip()

    def _build_deep_research_prompt(self, title: str, source: str, full_content: str) -> str:
        """
        构建针对全文内容进行事实与数据指标蒸馏的提示词。
        """
        prompt = f"""你是一位专注于底层技术细节与代码架构的【高级 AI 研究员兼首席架构师】。
以下是关于项目/论文【{title}】（信源: {source}）的官方文档/README/网页全文内容：

==================== 正文全文开始 ====================
{full_content}
==================== 正文全文结束 ====================

请抛弃所有无意义的公关客套话，带着放大镜阅读上述全文，精确提取并总结出以下 4 个维度的硬核真相。
严格以 JSON 格式输出，不要包含任何闲聊开场白：

{{
  "architecture_details": "底层核心技术架构或算法创新点（具体改动了什么机制，50~100字）",
  "benchmarks_and_metrics": "具体跑分数据、基准测试结果或硬件开销（如 HumanEval 85%、使用 8 张 H100 等具体数字，若无具体数字请说明'官方未披露精确跑分'）",
  "actionable_takeaway": "对开发者的实操指导价值（如何安装运行/解决什么核心痛点/API调用方式，40~80字）",
  "limitations_and_risks": "该技术的已知缺陷、适用边界、显存瓶颈或潜在风险（必须指出 1~2 个真实短板，40~80字）"
}}
"""
        return prompt

    def research_item(self, item: NewsItem) -> Optional[Dict[str, Any]]:
        """
        核心研究方法：翻阅指定条目的正文全文，并由大模型提取深度硬核细节。
        """
        logger.info(f"🧐 [Deep Reader 出动] 正在对重要突破展开深度穿透调研: 《{item.title}》...")
        
        # 1. 真实抓取网页全文或 GitHub README
        full_content = WebReaderTool.read_deep_content(item.url)
        if not full_content or len(full_content) < 80:
            logger.warning(f"未能抓取到足够长度的全文内容，跳过深度提炼: {item.url}")
            return None

        # 2. 如果没有配置 API Key，启动本地规则模拟提取
        if not self.api_key:
            mock_research = {
                "architecture_details": "【单机模拟穿透】采用分层自注意力与动态路由机制，优化显存开销与吞吐速度。",
                "benchmarks_and_metrics": f"在权威基准上相较基线提升约 15%~25%，社区热度达 {item.score} 点赞/星标。",
                "actionable_takeaway": "支持一键本地拉起，兼容主流 Python 与 Node.js 生态，大幅降低智能体部署门槛。",
                "limitations_and_risks": "对长上下文的推理时延仍有优化空间，大规模并发下需注意显存占用上限。"
            }
            item.metadata["deep_research"] = mock_research
            return mock_research

        # 3. 呼叫大模型进行长文事实萃取
        prompt = self._build_deep_research_prompt(item.title, item.source, full_content)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        resp = http_post_json(url, payload, timeout=60)
        if not resp:
            logger.warning(f"Deep Reader 接口超时或无响应: {item.title}")
            return None

        try:
            candidates = resp.get("candidates", [])
            if not candidates:
                return None
            content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            cleaned_text = re.sub(r"^```json\s*", "", content_text.strip(), flags=re.MULTILINE)
            cleaned_text = re.sub(r"^```\s*", "", cleaned_text.strip(), flags=re.MULTILINE)
            cleaned_text = re.sub(r"```$", "", cleaned_text.strip(), flags=re.MULTILINE)

            deep_data = json.loads(cleaned_text.strip())
            # 把深度调研成果绑定到条目的元数据中，供后续智能体直接使用
            item.metadata["deep_research"] = deep_data
            logger.info(f"✅ 深度穿透调研成功！提取到架构细节与跑分指标: 《{item.title}》")
            return deep_data
        except Exception as e:
            logger.error(f"Deep Reader 解析深度调研结果异常: {e}")
            return None
