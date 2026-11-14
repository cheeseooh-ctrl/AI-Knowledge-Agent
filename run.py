#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# 🎯 run.py - 项目的主入口脚本（v1.1.0 虚拟多智能体编辑部版）
#
# 【小白通俗理解】：
# 这个文件是总调度指挥中心。
# 在 v1.1.0 中，它不再只是简单地调用一次大模型，而是召集了：
# 1. 采集部门（HN, HF, GitHub, RSS）
# 2. 清洗部门（Cleaner 去重归一化）
# 3. 虚拟编辑部（Editorial Board：主笔记者撰稿 + 恶魔总编苛刻质检博弈）
# 4. 美编排版厂（Markdown 导出）
# 5. Git 云端同步员（可选自动把早报 push 到 GitHub）
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
from src.processor import clean_and_deduplicate, MultiAgentEditorialBoard
from src.exporters import MarkdownExporter


def auto_git_push(report_file: str, date_str: str):
    """
    【可选自动化功能】：将刚生成的日报自动 commit 并 push 到 GitHub。
    """
    print("\n📦 正在将今日早报自动同步推送至 GitHub 远端知识库...")
    try:
        # 执行 git add
        subprocess.run(["git", "add", "reports/"], check=True, capture_output=True)
        # 执行 git commit
        commit_msg = f"docs: 自动同步 {date_str} AI 每日情报早报 [v1.1.0]"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)
        # 执行 git push
        push_res = subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True, text=True)
        print("🚀 GitHub 云端知识库同步成功！可在网页端即时查看。")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Git 自动同步跳过或出错 (可能没有新变动或网络波动): {e}")


def run_pipeline(
    mock: bool = False,
    test_collect: bool = False,
    git_push: bool = False,
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
    print(f"🏛️ AI Knowledge Agent [v1.1.0 虚拟编辑部对抗版] 启动 | {date_str}")
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

    # 4. 虚拟多智能体编辑部：主笔撰稿 + 恶魔质检员博弈循环
    board_cfg = config.get("editorial_board", {})
    pass_threshold = board_cfg.get("pass_threshold", 80)
    max_rounds = board_cfg.get("max_revision_rounds", 2)

    # 实例化虚拟编辑部
    editorial_board = MultiAgentEditorialBoard(
        api_key="" if mock else gemini_api_key,
        model=gemini_model,
        pass_threshold=pass_threshold,
        max_revision_rounds=max_rounds
    )

    print("\n🏛️ 启动多智能体对抗审稿会议 (Writer vs Critic)...")
    summary_data = editorial_board.process(cleaned_items)

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
    print(f"🛡️ 虚拟编辑部质检评分: 【{score} / 100 分】 (经历 {rounds} 轮审稿博弈)")
    print("=" * 65)
    print(f"\n📌 今日核心大势：{summary_data.get('daily_focus', '')}\n")

    # 6. 可选自动同步至 GitHub
    should_push = git_push or output_cfg.get("git_auto_push", False)
    if should_push:
        auto_git_push(file_path, date_str)


def main():
    parser = argparse.ArgumentParser(description="AI Knowledge Agent - v1.1.0 虚拟编辑部对抗版")
    parser.add_argument("--mock", action="store_true", help="强制使用本地 Mock 模式生成报告（不消耗 API）")
    parser.add_argument("--test-collect", action="store_true", help="仅测试数据采集，不调用多智能体")
    parser.add_argument("--git-push", action="store_true", help="生成报告后自动 commit 并 push 到 GitHub")
    parser.add_argument("--date", type=str, help="自定义报告日期 (格式: YYYY-MM-DD)")
    parser.add_argument("--config", type=str, default="config.json", help="配置文件路径")

    args = parser.parse_args()
    run_pipeline(
        mock=args.mock,
        test_collect=args.test_collect,
        git_push=args.git_push,
        date_str=args.date,
        config_path=args.config
    )


if __name__ == "__main__":
    main()
