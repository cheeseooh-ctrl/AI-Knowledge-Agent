#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# 🎯 run.py - 项目的主入口脚本（总指挥部）
#
# 【小白通俗理解】：
# 这个文件就像是一家餐厅的“店长”或“总调度员”。
# 它本身不直接去洗菜（不直接写清洗规则），也不直接做菜（不直接实现模型接口），
# 它的工作是：按顺序指挥各个部门（采集部门、清洗部门、大模型提炼部门、导出部门）协同工作。
# ==============================================================================

# 导入 Python 自带的基础工具包
import os          # 【操作系统工具】：用来处理电脑上的文件路径、读取环境变量等
import sys         # 【系统解释器工具】：用来和 Python 运行时环境打交道
import argparse    # 【命令行参数解析器】：让你在终端输入类似 --mock 或 --test-collect 时，程序能看懂你的指令
import logging     # 【日志记录器】：在终端打印带时间戳、带等级的运行日志
from datetime import datetime  # 【日期时间工具】：用来获取今天的年月日（如 2026-11-14）

# ------------------------------------------------------------------------------
# 🛠️ 路径环境初始化
# ------------------------------------------------------------------------------
# 下面这行代码的意思是：把当前项目所在的文件夹根目录，加入到 Python 的“寻路名单”最前列。
# 为什么要加？因为这样 Python 才能顺利找到同级 src 目录下的各个工具包，避免提示“找不到模块 (ModuleNotFoundError)”。
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# ------------------------------------------------------------------------------
# 📦 从 src 业务模块中把我们写好的“专业工具”请出来
# ------------------------------------------------------------------------------
from src.utils import load_env, load_config, logger
from src.collectors import (
    HackerNewsCollector,         # 专门负责抓取 Hacker News 极客讨论的采集员
    HuggingFacePapersCollector,  # 专门负责抓取 Hugging Face 学术论文的采集员
    GitHubTrendingCollector,     # 专门负责抓取 GitHub 热门开源项目的采集员
    RSSFeedCollector,            # 专门负责读取 OpenAI 等官方博客 RSS 的采集员
)
from src.processor import (
    clean_and_deduplicate,       # 负责数据去重和清洗的“保洁员”
    GeminiSummarizer,            # 负责呼叫 Google Gemini 大模型写总结的“分析师”
    MockSummarizer,              # 没配 API Key 时的本地备用“模拟替身”
)
from src.exporters import MarkdownExporter  # 负责把提炼好的数据排版并保存为 .md 文件的“排版编辑”


def run_pipeline(
    mock: bool = False,            # 是否启用单机模拟模式（True: 不调大模型；False: 正常调用）
    test_collect: bool = False,    # 是否仅测试抓取（True: 抓完打印几条就退出，不写文件）
    date_str: str = None,          # 报告的日期（若为空，默认取今天）
    config_path: str = "config.json" # 配置文件存放的位置
):
    """
    【核心业务流水线流水线函数】：
    按顺序执行：1.读取配置 -> 2.启动采集 -> 3.数据清洗 -> 4.大模型思考 -> 5.生成日报文件
    """
    
    # 步骤 1：读取环境配置与 API 密钥
    env_vars = load_env(".env")      # 读取 .env 文件中的私密配置（如 GEMINI_API_KEY）
    config = load_config(config_path)# 读取 config.json 中的公开配置（如关键词、开关）

    # 优先从电脑系统的环境变量拿密钥，如果没有，就从刚刚读取的 .env 文件里拿
    gemini_api_key = os.environ.get("GEMINI_API_KEY") or env_vars.get("GEMINI_API_KEY", "")
    # 获取要调用的模型名称（默认使用 gemini-2.5-flash）
    gemini_model = os.environ.get("GEMINI_MODEL") or config.get("summarizer", {}).get("default_model", "gemini-2.5-flash")

    # 如果用户没手动指定日期，就自动获取电脑当天的本地日期（格式：2026-11-14）
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 打印一个漂亮的启动横幅
    print("\n" + "=" * 60)
    print(f"🤖 AI Knowledge Agent 每日情报生成器启动 | {date_str}")
    print("=" * 60 + "\n")

    # 步骤 2：组建“采集员队伍”
    # 我们去检查 config.json 里的配置，看用户开启了哪些数据源，开启哪个就实例化哪个采集器
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

    # 步骤 3：指挥所有采集员出发，到网上去拉取数据
    raw_items = []  # 用来存放全网捞回来的原始数据列表
    print(f"📡 正在从 {len(collectors)} 个多维信源拉取最新 AI 动态...")
    for collector in collectors:
        try:
            items = collector.collect() # 真正发起网络请求爬取数据
            print(f"  ✓ [{collector.name}] 成功获取 {len(items)} 条")
            raw_items.extend(items)     # 把抓到的条目合并存入总列表
        except Exception as e:
            logger.error(f"采集器 {collector.name} 运行出错: {e}")

    # 步骤 4：数据清洗与去重（保洁环节）
    # 把不同渠道重复报道的新闻合并，把乱七八糟的 URL 跟踪参数剁掉
    cleaned_items = clean_and_deduplicate(raw_items)
    print(f"\n✨ 数据预处理完成：原始数据 {len(raw_items)} 条，清洗去重后精选 {len(cleaned_items)} 条。")

    # 如果用户在终端输入了 --test-collect，说明他只是想测测网络通不通，这里打印完就提前收工退出
    if test_collect:
        print("\n[--test-collect 模式] 前 5 条采集样例：")
        for i, item in enumerate(cleaned_items[:5], 1):
            print(f"  {i}. [{item.source}] {item.title} ({item.url})")
        print("\n测试采集结束。")
        return

    # 步骤 5：呼叫大模型进行智能深度提炼（大脑思考环节）
    summary_data = None
    # 只有当用户配置了 API Key，且没有主动加 --mock 参数时，才真正发起网络请求连线 Gemini
    if gemini_api_key and not mock:
        print(f"\n🧠 正在通过 Google Gemini API ({gemini_model}) 进行深度理解与智能提炼...")
        summarizer = GeminiSummarizer(gemini_api_key, model=gemini_model)
        summary_data = summarizer.summarize(cleaned_items)
        if not summary_data:
            print("⚠️  Gemini API 调用未能返回预期结果，自动回退到模拟整理模式...")

    # 如果没配 API Key，或者大模型连不上，系统绝不闪退，而是自动启动 Mock 模拟器来保底排版
    if not summary_data:
        if not gemini_api_key:
            print("\n💡 提示：未检测到 GEMINI_API_KEY，当前以【模拟结构化模式】生成报告。")
            print("   （如需开启 Gemini 大模型智能提炼，请在 .env 文件中填入 GEMINI_API_KEY）")
        summarizer = MockSummarizer()
        summary_data = summarizer.summarize(cleaned_items)

    # 步骤 6：把提炼好的数据导出并存入 Markdown 文件（出报纸环节）
    output_cfg = config.get("output", {})
    output_dir = output_cfg.get("dir", "./reports")         # 报告存到哪个文件夹
    save_raw_json = output_cfg.get("save_raw_json", True)   # 是否同时备份一份 JSON 原始数据

    exporter = MarkdownExporter(output_dir=output_dir)
    file_path = exporter.export(summary_data, date_str=date_str, save_json=save_raw_json)

    # 步骤 7：在控制台打印大功告成的庆祝信息
    print("\n" + "=" * 60)
    print("🎉 今日 AI 情报早报生成成功！")
    print(f"📁 报告文件已归档至: {file_path}")
    print("=" * 60)
    print(f"\n📌 今日核心大势：{summary_data.get('daily_focus', '')}\n")


def main():
    """
    【终端命令行参数接收器】：
    当你在终端里输入 python3 run.py --mock 时，Python 会首先跳到这里，
    解析你输入的每个单词，然后转交给上面的 run_pipeline 函数。
    """
    parser = argparse.ArgumentParser(description="AI Knowledge Agent - 每日 AI 世界情报生成器")
    parser.add_argument("--mock", action="store_true", help="强制使用本地 Mock 模式生成报告（不消耗 API 额度）")
    parser.add_argument("--test-collect", action="store_true", help="仅测试数据采集功能，不调用大模型也不写报告")
    parser.add_argument("--date", type=str, help="自定义报告日期 (格式: YYYY-MM-DD)")
    parser.add_argument("--config", type=str, default="config.json", help="配置文件路径（默认是 config.json）")

    args = parser.parse_args() # 开始解析命令
    # 把解析出来的选项传给主流程
    run_pipeline(
        mock=args.mock,
        test_collect=args.test_collect,
        date_str=args.date,
        config_path=args.config
    )


# ------------------------------------------------------------------------------
# 这一行是 Python 的惯用语法：
# 意思是：只有当你直接在命令行里跑 `python3 run.py` 时，才执行 main() 函数；
# 如果别人只是从其他文件里引用（import）它，就不会自动胡乱执行。
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
