# -*- coding: utf-8 -*-
from src.processor.cleaner import clean_and_deduplicate
from src.processor.writer_agent import WriterAgent
from src.processor.critic_agent import CriticAgent
from src.processor.router import AgentRouter
from src.processor.gemini_summarizer import GeminiSummarizer # 保留 v1.0.0 单次总结器作为向下兼容组件
from src.processor.mock_summarizer import MockSummarizer

__all__ = [
    "clean_and_deduplicate",
    "WriterAgent",
    "CriticAgent",
    "AgentRouter",
    "GeminiSummarizer",
    "MockSummarizer",
]
