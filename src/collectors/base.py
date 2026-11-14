# -*- coding: utf-8 -*-

# ==============================================================================
# 📐 src/collectors/base.py - 采集器基类与统一数据模型（海关标准）
#
# 【小白通俗理解】：
# 这个文件是全系统的“标准海关局”。
# 无论你是从 HackerNews 捞回来的英文讨论，还是从 HuggingFace 捞回来的论文，
# 或者是从 GitHub 捞回来的开源项目，格式都极其混乱。
# 这个文件定义了一个统一的“标准快递盒”——NewsItem。
# 所有的采集员（Collector）从网上抓到东西后，都必须把信息装进这个标准的盒子里，
# 这样后面的“清洗员”和“大模型”就只需要认识这一种盒子即可，大大降低系统复杂度。
# ==============================================================================

from dataclasses import dataclass, field # 数据类装饰器：让写 Python 对象像填表格一样简单
from typing import Dict, Any, List       # 类型注解提示
from abc import ABC, abstractmethod     # 抽象类工具：用来制定“下级必须遵守的硬性规章制度”


@dataclass
class NewsItem:
    """
    【标准新闻数据模型（快递盒）】：
    无论什么来源的新闻，最终都会被统一打包为包含以下 7 个属性的对象。
    """
    title: str                  # 必须有：新闻标题（如 "OpenAI 发布 ChatGPT Wallet"）
    url: str                    # 必须有：原文跳转链接（用于溯源与点击）
    source: str                 # 必须有：信源标记（如 "Hacker News", "Hugging Face"）
    summary: str = ""           # 选填项：原文简短摘要或官方描述，默认为空字符串
    score: int = 0              # 选填项：热度打分（如 GitHub Star数、HN 点赞数），默认 0
    published_at: str = ""      # 选填项：发布时间（如 "2026-11-14"），默认为空
    metadata: Dict[str, Any] = field(default_factory=dict) # 选填项：存放额外的附加信息字典

    def to_dict(self) -> Dict[str, Any]:
        """
        把这个对象转换成 Python 原生字典格式，方便后续转换成 JSON 存盘备份。
        """
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "summary": self.summary,
            "score": self.score,
            "published_at": self.published_at,
            "metadata": self.metadata,
        }


class BaseCollector(ABC):
    """
    【采集器抽象父类（岗前培训手册）】：
    这是一个模板类。任何具体的采集员（比如抓 GitHub 的、抓 HN 的）都必须“继承”这个类。
    利用 Python 的抽象基类特性，强制所有下级采集员必须做到两件事：
    1. 必须有自己的名字（name）
    2. 必须实现具体的抓取动作（collect 方法），且返回的必须是装满 NewsItem 的列表
    """
    def __init__(self, config: Dict[str, Any]):
        # 保存外部传入的配置参数（比如抓几个、关键词是什么）
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """所有子类必须声明自己的名字，比如 'Hacker News 采集器'"""
        pass

    @abstractmethod
    def collect(self) -> List[NewsItem]:
        """所有子类必须实现的核心抓取函数：去网上搜集数据，打包成 NewsItem 列表返回"""
        pass
