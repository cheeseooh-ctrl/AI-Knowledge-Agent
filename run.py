#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# 🎯 run.py - 项目的主入口脚本 (v1.2.0 Deep Reader 深度穿透版)
#
# 【小白通俗理解】：
# 这个文件是总调度指挥中心。
# 在 v1.2.0 中，核心升级如下：
# 1. 组建采集队伍（HN, HF, GitHub, RSS）
# 2. 调度清洗模块（Cleaner 去重归一化）
# 3. 呼叫核心路由器（Agent Router）：
#    - 自动筛选 Top 3 重磅线索，派出 DeepReaderAgent 穿透翻阅网页全文与代码 README；
#    - 组织 Writer Agent 与 Critic Agent 基于一手硬核事实进行多轮博弈打磨；
# 4. 调度排版器（Markdown 导出）：为深度研读条目打上专属角标并格式化呈现；
# 5. 可选自动将当天产出的早报同步推送到 GitHub 云端知识库。
# ==============================================================================

import os
import sys
import subprocess
import argparse
import logging
from datetime import datetime

# 路径初始化：确保能顺利导入 src 下的所有模块
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.utils import load_env, load_config, logger
from src.collectors import (
    HackerNewsCollector,
    HuggingFacePapersCollector,
    GitHubTrendingCollector,
    RSSFeedCollector,
)
from src.processor import clean_and_deduplicate, AgentRouter
from src.exporters import MarkdownExporter


def auto_git_push(report_file: str, date_str: str):
    """
    【可选自动化功能】：将刚生成的日报自动 commit 并 push 到 GitHub。
    """
    print("\n📦 正在将今日早报自动同步推送至 GitHub 远端知识库...")
    try:
        subprocess.run(["git", "add", "reports/"], check=True, capture_output=True)
        commit_msg = f"docs: 自动同步 {date_str} AI 每日情报早报 [v1.2.0 Deep Reader]"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True, text=True)
        print("🚀 GitHub 云端知识库同步成功！可在网页端即时查看。")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Git 自动同步跳过或出错 (可能没有新变动或网络波动): {e}")


def run_pipeline(
    mock: bool = False,
    test_collect: bool = False,
    git_push: bool = False,
    no_deep: bool = False,
    date_str: str = None,
    config_path: str = "config.json"
):
    """执行 AI Knowledge Agent 每日流水线"""
    env_vars = load_env(".env")
    config = load_config(config_path)

    gemini_api_key = os.environ.get("GEMINI_API_KEY") or env_vars.get("GEMINI_API_KEY", "")
    gemini_model = os.environ.get("GEMINI_MODEL") or config.get("summarizer", {}).get("default_model", "gemini-2.5-flash")

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    print("\n" + "=" * 65)
    print(f"🔬 AI Knowledge Agent [v1.2.0 深度穿透版] 启动 | {date_str}")
    print("=" * 65 + "\n")

    # 1. 组建采集队伍
    sources_cfg = config.get("sources", {})
    collectors = []

    if sources_cfg.get("hackernews", {}).get("enabled", True):
        collectors.append(HackerNewsCollector(sources_cfg.get("hackernews", {})))

    if sources_cfg.get("huggingface_papers", {}).get("enabled", True):
        collectors.append(HuggingFacePapersCollector(sources_cfg.get("huggingface_papers", {})))

    if sources_cfg.get("github_trending", {}).get("enabled", True):
        collectors.append(GitHubTrendingCollector(sources_cfg.get("github_trending", {})))

    if sources_cfg.get("rss_feeds", {}).get("enabled", True):
        collectors.append(RSSFeedCollector(sources_cfg.get("rss_feeds", {})))

    # 2. 执行网络抓取
    raw_items = []
    print(f"📡 正在从 {len(collectors)} 个多维信源拉取最新 AI 动态...")
    for collector in collectors:
        try:
            items = collector.collect()
            print(f"  ✓ [{collector.name}] 成功获取 {len(items)} 条")
            raw_items.extend(items)
        except Exception as e:
            logger.error(f"Collector {collector.name} error: {e}")

    # 3. 数据清洗与去重
    cleaned_items = clean_and_deduplicate(raw_items)
    print(f"\n✨ 数据预处理完成：原始数据 {len(raw_items)} 条，清洗去重后精选 {len(cleaned_items)} 条。")

    if test_collect:
        print("\n[--test-collect 模式] 前 5 条采集样例：")
        for i, item in enumerate(cleaned_items[:5], 1):
            print(f"  {i}. [{item.source}] {item.title} ({item.url})")
        print("\n测试采集结束。")
        return

    # 4. 多智能体核心路由与深度穿透调度 (Agent Router)
    router_cfg = config.get("router", {})
    pass_threshold = router_cfg.get("pass_threshold", 80)
    max_rounds = router_cfg.get("max_revision_rounds", 2)

    deep_cfg = config.get("deep_reader", {})
    deep_enabled = deep_cfg.get("enabled", True) and (not no_deep)
    max_deep_items = deep_cfg.get("max_deep_items", 3)

    # 实例化中枢路由编排器
    agent_router = AgentRouter(
        api_key="" if mock else gemini_api_key,
        model=gemini_model,
        pass_threshold=pass_threshold,
        max_revision_rounds=max_rounds,
        deep_reader_enabled=deep_enabled,
        max_deep_items=max_deep_items
    )

    print(f"\n🔀 启动多智能体动态路由 (DeepReader={'开启' if deep_enabled else '关闭'} -> Writer -> Critic)...")
    summary_data = agent_router.route_and_process(cleaned_items)

    # 5. 排版并导出 Markdown
    output_cfg = config.get("output", {})
    output_dir = output_cfg.get("dir", "./reports")
    save_raw_json = output_cfg.get("save_raw_json", True)

    exporter = MarkdownExporter(output_dir=output_dir)
    file_path = exporter.export(summary_data, date_str=date_str, save_json=save_raw_json)

    # 打印总结与质检卡片
    audit = summary_data.get("audit_report", {})
    score = audit.get("overall_score", "N/A")
    rounds = audit.get("rounds", 1)

    print("\n" + "=" * 65)
    print("🎉 今日 AI 情报早报生成成功！")
    print(f"📁 报告文件已归档至: {file_path}")
    print(f"🛡️ 路由质检综合评分: 【{score} / 100 分】 (经历 {rounds} 轮审稿博弈)")
    print("=" * 65)
    print(f"\n📌 今日核心大势：{summary_data.get('daily_focus', '')}\n")

    # 6. 可选自动同步至 GitHub
    should_push = git_push or output_cfg.get("git_auto_push", False)
    if should_push:
        auto_git_push(file_path, date_str)


def main():
    parser = argparse.ArgumentParser(description="AI Knowledge Agent - v1.2.0 Deep Reader 深度穿透版")
    parser.add_argument("--mock", action="store_true", help="强制使用本地 Mock 模式生成报告（不消耗 API）")
    parser.add_argument("--test-collect", action="store_true", help="仅测试数据采集，不调用多智能体")
    parser.add_argument("--git-push", action="store_true", help="生成报告后自动 commit 并 push 到 GitHub")
    parser.add_argument("--no-deep", action="store_true", help="关闭深度正文穿透（仅使用快讯模式，速度更快）")
    parser.add_argument("--date", type=str, help="自定义报告日期 (格式: YYYY-MM-DD)")
    parser.add_argument("--config", type=str, default="config.json", help="配置文件路径")

    args = parser.parse_args()
    run_pipeline(
        mock=args.mock,
        test_collect=args.test_collect,
        git_push=args.git_push,
        no_deep=args.no_deep,
        date_str=args.date,
        config_path=args.config
    )


if __name__ == "__main__":
    main()
