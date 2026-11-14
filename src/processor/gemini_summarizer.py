# -*- coding: utf-8 -*-

# ==============================================================================
# 🧠 src/processor/gemini_summarizer.py - Google Gemini 大模型智能提炼器
#
# 【小白通俗理解】：
# 这个文件是全系统的“智能大脑与主编”。
# 它拿到前面清洗出来的干货数据后，通过网络向 Google 官方的数据中心发起呼叫，
# 命令 Gemini 大模型发挥它高超的语义理解、英汉跨语言翻译、信息浓缩和行业洞察能力。
# 技术亮点：
# 1. 原生 REST 请求：不需要安装庞大的第三方 SDK，直接通过 HTTP 发送数据。
# 2. 强制 JSON 模式（responseMimeType）：命令大模型闭嘴，不许有任何闲聊，
#    必须严格按照我们规定的 JSON 格式吐出结构化结果，彻底根除程序崩溃隐患。
# 3. 自动降级容灾：如果 gemini-2.5-flash 遇到拥堵，自动切换备用模型重试。
# ==============================================================================

import json           # 负责字典与 JSON 字符串转换
import logging        # 负责日志记录
import re             # 正则表达式
from typing import List, Dict, Any, Optional
from src.collectors.base import NewsItem # 统一的数据模型盒子
from src.utils import http_post_json     # 通用 POST 请求网络工具

logger = logging.getLogger("AIAgent.Summarizer")


class GeminiSummarizer:
    """
    负责调用 Google Gemini 大模型完成每日早报提炼总结的类。
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key.strip()  # 用户的 Gemini API 密钥
        self.model = model.strip()      # 默认调用的模型型号名称

    def _build_prompt(self, items: List[NewsItem]) -> str:
        """
        【提示词工程（Prompt Engineering）构建器】：
        负责把清洗好的数据包装成一段严谨、专业的指示令，告诉大模型它的身份、输入数据以及期望的输出格式。
        """
        # 第一步：把我们的 NewsItem 列表压缩成精简的输入格式，避免向大模型发送无用字段，节省 Token 费用
        input_data = []
        for i, item in enumerate(items, 1):
            input_data.append({
                "id": i,
                "title": item.title,
                "url": item.url,
                "source": item.source,
                "score": item.score,
                "snippet": item.summary[:300] if item.summary else "",
            })

        # 第二步：精心设计的结构化 Prompt 模板
        prompt = f"""你是一位全球顶级 AI 技术专家、资深开源架构师与前沿科技主编。
以下是今天从 Hacker News、Hugging Face Papers、GitHub 开源、官方权威博客（OpenAI、Anthropic 等）采集到的原始 AI 动态列表：

{json.dumps(input_data, ensure_ascii=False, indent=2)}

请对上述信息进行去粗取精、去伪存真的分析，生成一份结构化且富有洞察力的【今日 AI 每日简报】。
严格以 JSON 格式输出，不要包含任何多余的开场白或解释。

JSON 结构必须严格符合以下字段规范：
{{
  "daily_focus": "今日核心大势（一句话精准概括今天的核心技术风向或最重磅事件，20~40字）",
  "breakthroughs": [
    {{
      "title": "中文通俗且专业的标题",
      "original_title": "原始英文标题",
      "url": "对应原文链接",
      "source": "信源名称",
      "why_it_matters": "核心价值与行业影响（为什么值得关注，对开发者或业务有何启发）",
      "key_points": [
        "核心要点1",
        "核心要点2"
      ]
    }}
  ],
  "open_source_tools": [
    {{
      "name": "项目名称",
      "url": "仓库链接",
      "stars_or_tag": "如: ⭐️ 1,200 | Python",
      "description": "一两句话准确说明这个工具解决了什么问题、有哪些亮点"
    }}
  ],
  "trending_papers": [
    {{
      "title": "论文中文标题",
      "original_title": "英文标题",
      "url": "论文链接 (HF 或 ArXiv)",
      "takeaway": "核心创新点与实证结论（通俗易懂地说明有何突破）"
    }}
  ],
  "hot_discussions": [
    {{
      "title": "讨论主题",
      "url": "链接 (HN/论坛)",
      "summary": "社区的核心分歧、热议观点或避坑经验"
    }}
  ]
}}
"""
        return prompt

    def summarize(self, items: List[NewsItem]) -> Optional[Dict[str, Any]]:
        """
        【主执行函数】：发起网络连接，将提示词发送给 Gemini 服务器并取回解析后的结果。
        """
        # 如果 API Key 为空，直接拦截，不浪费网络请求
        if not self.api_key:
            logger.error("未检测到有效的 GEMINI_API_KEY，无法调用大模型")
            return None

        # 组装完整的 Prompt
        prompt = self._build_prompt(items)
        # 拼装 Google Gemini 官方开放接口的 REST 请求地址
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        # 构造发给 Google 服务器的数据载荷（Payload）
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt} # 我们要对大模型说的话
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2, # 采样温度（0~1）：设得比较低（0.2），让大模型更加严谨客观，减少天马行空的胡思乱想
                "responseMimeType": "application/json" # 强约束：强制大模型以标准 JSON 格式回复
            }
        }

        logger.info(f"正在呼叫 Google Gemini API ({self.model}) 提炼数据...")
        # 发送网络请求
        resp = http_post_json(url, payload, timeout=60)

        # ----------------------------------------------------------------------
        # 容灾降级机制：如果主模型 (2.5-flash) 失败，自动尝试备用模型 (2.0-flash)
        # ----------------------------------------------------------------------
        if not resp:
            fallback = "gemini-2.0-flash" if self.model != "gemini-2.0-flash" else "gemini-1.5-flash"
            logger.warning(f"使用主模型 {self.model} 请求失败，正在自动切换备用模型 {fallback} 重试...")
            url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/{fallback}:generateContent?key={self.api_key}"
            resp = http_post_json(url_fallback, payload, timeout=60)
            if not resp:
                logger.error("备用模型也未能成功返回，大模型处理宣告失败。")
                return None

        # ----------------------------------------------------------------------
        # 解析大模型返回的数据
        # ----------------------------------------------------------------------
        try:
            candidates = resp.get("candidates", [])
            if not candidates:
                logger.error(f"Gemini 返回的报文中缺少候选内容 (candidates): {resp}")
                return None

            # 从层层嵌套的响应字典中，把大模型说的核心文本字符串拿出来
            content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            # 防御性清洗：有些大模型即使你强调了，它偶尔还是会在开头加上 ```json 和在结尾加上 ```
            # 下面这几行用正则把这些 Markdown 代码块外壳剥掉
            cleaned_text = re.sub(r"^```json\s*", "", content_text.strip(), flags=re.MULTILINE)
            cleaned_text = re.sub(r"^```\s*", "", cleaned_text.strip(), flags=re.MULTILINE)
            cleaned_text = re.sub(r"```$", "", cleaned_text.strip(), flags=re.MULTILINE)

            # 把纯文本 JSON 转换成 Python 可以直接使用的字典结构
            data = json.loads(cleaned_text.strip())
            logger.info("成功完成大模型深度提炼，JSON 格式校验完全通过！")
            return data
        except Exception as e:
            logger.error(f"将 Gemini 的回复解析为 JSON 时出错: {e}\n原始回复内容: {resp}")
            return None
