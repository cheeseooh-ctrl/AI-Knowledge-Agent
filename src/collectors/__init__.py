from src.collectors.base import BaseCollector, NewsItem
from src.collectors.hackernews import HackerNewsCollector
from src.collectors.huggingface import HuggingFacePapersCollector
from src.collectors.github import GitHubTrendingCollector
from src.collectors.rss import RSSFeedCollector

__all__ = [
    "BaseCollector",
    "NewsItem",
    "HackerNewsCollector",
    "HuggingFacePapersCollector",
    "GitHubTrendingCollector",
    "RSSFeedCollector",
]
