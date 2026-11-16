# -*- coding: utf-8 -*-

# ==============================================================================
# 📱 feishu_pusher.py - 飞书自定义机器人交互式卡片推送器 (v2.0.0)
#
# 【架构定位】：
# 1. 负责将 Writer/Critic 最终定稿的早报数据转换为高颜值的飞书 Interactive Card (消息卡片)；
# 2. 纯 Python 原生零依赖，通过 urllib.request POST 到飞书 Webhook 接口；
# 3. 具备网络熔断容错、长文本截断防超载、以及离线 Dry-Run 校验功能。
# ==============================================================================

import os
import json
import ssl
import logging
from typing import Dict, Any, List, Optional, Tuple
import urllib.request
import urllib.error

logger = logging.getLogger("AIKnowledgeAgent.FeishuPusher")


class FeishuPusher:
    """飞书自定义机器人交互式卡片推送器"""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        card_theme: str = "blue",
        github_repo_url: str = "https://github.com/cheeseooh-ctrl/AI-Knowledge-Agent"
    ):
        """
        :param webhook_url: 飞书自定义机器人的 Webhook 地址 (形如 https://open.feishu.cn/open-apis/bot/v2/hook/xxxx)
        :param card_theme: 卡片 Header 主题色 (blue, wathet, turquoise, green, yellow, orange, red, carmine, violet, purple, indigo)
        :param github_repo_url: GitHub 仓库链接，供卡片底部的跳转按钮使用
        """
        # 优先级：显式入参 > 环境变量 FEISHU_WEBHOOK_URL
        self.webhook_url = webhook_url or os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
        self.card_theme = card_theme
        self.github_repo_url = github_repo_url

    def build_interactive_card(
        self,
        summary_data: Dict[str, Any],
        date_str: str,
        max_items_per_section: int = 3
    ) -> Dict[str, Any]:
        """
        将聚合提炼后的 summary_data 结构化组装为飞书 Interactive Card JSON。
        """
        audit = summary_data.get("audit_report", {})
        score = audit.get("overall_score", 85)
        rounds = audit.get("rounds", 1)
        suppressed = audit.get("suppressed_repeats", 0)
        profile_matched = audit.get("profile_matched", False)

        daily_focus = summary_data.get("daily_focus", "暂无核心大势")
        focus_areas = summary_data.get("focus_areas", [])

        # 1. 组装审稿档案描述
        profile_badge = "✅ 已匹配用户专属画像提权" if profile_matched else "🌐 通用全局视角"
        audit_text = (
            f"🎯 严谨度质检分：**{score} / 100**   |   🔄 审稿博弈：**{rounds} 轮**\n"
            f"🧠 个性化画像：{profile_badge}   |   🛡️ 跨天防炒冷饭：**压制 {suppressed} 条老线索**"
        )

        elements: List[Dict[str, Any]] = [
            # 审稿徽章区块
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**【虚拟编辑部审稿档案】**\n{audit_text}"
                }
            },
            {"tag": "hr"},
            # 今日核心大势
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📌 **今日核心大势**\n{daily_focus}"
                }
            },
            {"tag": "hr"}
        ]

        # 2. 遍历各分类区块提取高价值内容
        deep_items_content = []
        regular_items_content = []

        for area in focus_areas:
            area_title = area.get("title", "")
            items = area.get("items", [])

            for item in items:
                title = item.get("title", "").strip()
                url = item.get("url", "").strip()
                analysis = item.get("analysis", "").strip()
                deep = item.get("deep_research")

                # 如果有深度穿透事实
                if deep and isinstance(deep, dict):
                    arch = deep.get("architecture_details", "")
                    bench = deep.get("benchmarks_and_metrics", "")
                    takeaway = deep.get("actionable_takeaway", "")

                    deep_md = f"🔬 **[{title}]({url})**\n"
                    if arch:
                        deep_md += f"• **架构核心**: {arch}\n"
                    if bench:
                        deep_md += f"• **实测跑分**: {bench}\n"
                    if takeaway:
                        deep_md += f"• **落地价值**: {takeaway}\n"
                    deep_items_content.append(deep_md)
                else:
                    reg_md = f"• **[{title}]({url})**\n  > {analysis[:120]}..." if len(analysis) > 120 else f"• **[{title}]({url})**\n  > {analysis}"
                    regular_items_content.append(reg_md)

        # 3. 填入深度穿透特辑 (最多展示前 3 个)
        if deep_items_content:
            selected_deep = deep_items_content[:3]
            deep_block = "### 🔬 深度技术穿透 (一手事实与跑分)\n" + "\n".join(selected_deep)
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": deep_block
                }
            })
            elements.append({"tag": "hr"})

        # 4. 填入精选快讯脉冲 (最多展示前 5 个)
        if regular_items_content:
            selected_regular = regular_items_content[:5]
            reg_block = "### ⚡ 今日精选前沿脉冲\n" + "\n".join(selected_regular)
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": reg_block
                }
            })
            elements.append({"tag": "hr"})

        # 5. 底部操作按钮：直达 GitHub 完整知识库
        report_url = f"{self.github_repo_url}/blob/main/reports/{date_str}_AI_Daily_Briefing.md"
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "📖 在 GitHub 查阅完整今日知识库"
                    },
                    "type": "primary",
                    "url": report_url
                },
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "📂 访问知识库主页"
                    },
                    "type": "default",
                    "url": self.github_repo_url
                }
            ]
        })

        # 组装完整卡片结构
        card_payload = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"🪐 AI Daily Briefing | {date_str} 每日情报内参"
                    },
                    "template": self.card_theme
                },
                "elements": elements
            }
        }

        return card_payload

    def push(
        self,
        summary_data: Dict[str, Any],
        date_str: str,
        dry_run: bool = False
    ) -> Tuple[bool, str]:
        """
        向飞书机器人发送卡片消息。
        :param summary_data: 早报核心数据
        :param date_str: 报告日期
        :param dry_run: 若为 True，仅打印组装后的 JSON Payload，不发起实际网络请求
        :return: (是否成功, 详细结果/错误信息)
        """
        card_payload = self.build_interactive_card(summary_data, date_str)

        if dry_run:
            preview_str = json.dumps(card_payload, ensure_ascii=False, indent=2)
            print("\n" + "=" * 60)
            print("📱 [Dry-Run 模式] 飞书 Interactive Card 报文预览：")
            print("=" * 60)
            print(preview_str)
            print("=" * 60 + "\n")
            return True, "Dry-run preview generated successfully."

        if not self.webhook_url:
            warning_msg = (
                "⚠️ 未检测到飞书 Webhook 地址 (FEISHU_WEBHOOK_URL)！\n"
                "  【快速配置指引】：\n"
                "  1. 在飞书群组中添加【自定义机器人】；\n"
                "  2. 复制 Webhook 地址；\n"
                "  3. 在终端中配置 export FEISHU_WEBHOOK_URL=\"https://open.feishu.cn/open-apis/bot/v2/hook/...\"；\n"
                "  4. 或在 config.json 的 notification.feishu.webhook_url 中填入。"
            )
            logger.warning(warning_msg)
            print(f"\n{warning_msg}\n")
            return False, "Missing FEISHU_WEBHOOK_URL."

        # 原生网络请求发送
        data_bytes = json.dumps(card_payload).encode("utf-8")
        req = urllib.request.Request(
            url=self.webhook_url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "AIKnowledgeAgent/2.0"
            },
            method="POST"
        )

        ctx = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                resp_body = resp.read().decode("utf-8")
                resp_json = json.loads(resp_body)
                code = resp_json.get("code", 0)
                msg = resp_json.get("msg", "")

                if code == 0:
                    success_msg = "🎉 飞书早报卡片推送成功！已直达手机与桌面端。"
                    print(f"\n{success_msg}")
                    return True, success_msg
                else:
                    err_msg = f"❌ 飞书接口返回错误 (code: {code}): {msg}"
                    logger.error(err_msg)
                    print(f"\n{err_msg}")
                    return False, err_msg

        except urllib.error.HTTPError as e:
            err_msg = f"❌ HTTP Error connecting to Feishu: {e.code} - {e.reason}"
            logger.error(err_msg)
            return False, err_msg
        except urllib.error.URLError as e:
            err_msg = f"❌ URL Error connecting to Feishu: {e.reason}"
            logger.error(err_msg)
            return False, err_msg
        except Exception as e:
            err_msg = f"❌ Unexpected error pushing to Feishu: {e}"
            logger.error(err_msg)
            return False, err_msg
