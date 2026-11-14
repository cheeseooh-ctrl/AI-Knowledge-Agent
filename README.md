# 🪐 AI Daily Knowledge Agent (AI 每日情报知识管家)

> 每日自动化追踪全球 AI 前沿动态，经过智能清洗与大模型深度提炼，沉淀为高质量知识库与日报。

---

## 🌟 核心特性

- **多维权威信源矩阵**：
  - 💬 **Hacker News**：挖掘全球极客对 AI/LLM 的高分深度讨论与冷静评测。
  - 📄 **Hugging Face Daily Papers**：追踪每日最新学术突破与算法论文榜单。
  - 🛠️ **GitHub Trending**：自动发现过去几天最火的开源 AI Agent、模型微调与底层工具库。
  - 📡 **权威官方博客 RSS**：第一时间跟进 OpenAI、Google AI、Hugging Face Blog 及专家技术专栏（Simon Willison 等）。
- **智能去噪与 LLM 提炼**：
  - 自动 URL 规范化、去重与质量排序。
  - 接入 **Google Gemini API**（如 `gemini-2.5-flash`），进行结构化深度提炼：总结**今日核心大势**、分析**为何重要**、提取**核心要点**与**项目亮点**。
- **零外部必装依赖设计（Zero-Dependency Core）**：
  - 核心网络通信与数据解析基于 Python 3.9+ 原生标准库实现，克隆即可运行；同时也支持 `pip install -r requirements.txt` 进行功能增强。
- **本地 Markdown 知识库自动沉淀**：
  - 每天自动将结构化日报归档至 `./reports/YYYY-MM-DD_AI_Daily_Briefing.md`。

---

## 🚀 快速上手

### 1. 配置 API Key（可选但强烈建议）

复制环境变量模板：
```bash
cp .env.example .env
```
编辑 `.env` 文件，填入你的 Google Gemini API Key：
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```
> 💡 **如何获取免费的 Gemini API Key**：
> 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)，点击 "Create API Key" 即可免费申请。

### 2. 运行生成日报

* **一键运行（完整流程：采集 → 大模型总结 → 生成归档）**：
  ```bash
  python3 run.py
  ```

* **测试数据采集（不消耗 LLM 额度，仅测试网络与源数据）**：
  ```bash
  python3 run.py --test-collect
  ```

* **本地模拟模式（无 API Key 时快速体验生成效果）**：
  ```bash
  python3 run.py --mock
  ```

* **指定历史日期重新生成**：
  ```bash
  python3 run.py --date 2026-11-14
  ```

---

## ⚙️ 自定义配置 (`config.json`)

你可以通过修改根目录下的 `config.json` 轻松自定义关注的领域与抓取规则：

```json
{
  "sources": {
    "hackernews": {
      "enabled": true,
      "min_points": 25,
      "keywords": ["AI", "LLM", "Agent", "Claude", "Gemini", "DeepSeek"]
    },
    "huggingface_papers": {
      "enabled": true,
      "max_items": 8
    },
    "github_trending": {
      "enabled": true,
      "topics": ["llm", "agent", "ai", "rag", "mcp"]
    },
    "rss_feeds": {
      "enabled": true,
      "feeds": [
        {"name": "OpenAI News", "url": "https://openai.com/news/rss.xml"},
        {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
        {"name": "Simon Willison Weblog", "url": "https://simonwillison.net/atom/everything/"},
        {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"}
      ]
    }
  }
}
```

---

## ⏰ 每日定时自动执行

你可以将该脚本配置为每天早上自动执行：

### 方式一：macOS / Linux 本地 Crontab（最简单稳定）
在终端中输入 `crontab -e`，添加一条定时任务（例如每天早晨 8:30 自动生成）：
```bash
30 8 * * * cd "/Users/cheese/Desktop/File/AI应用搭建/AI Knowledge Agent" && /usr/bin/python3 run.py >> reports/cron.log 2>&1
```

### 方式二：在 Antigravity 中使用 `/schedule`
在对话框中输入 `/schedule`，设定指令：
> “每天早上 9 点运行当前工作区的 python3 run.py，并提醒我最新出炉的 AI 日报”

---

## 📂 项目结构

```
AI Knowledge Agent/
├── config.json               # 抓取信源与模型参数配置
├── .env.example              # 环境变量配置模板
├── requirements.txt          # 可选依赖
├── run.py                    # 统一执行入口
├── src/
│   ├── utils.py              # 兼容标准库的 HTTP 网络库与环境加载器
│   ├── collectors/           # 4 大信源独立采集器
│   │   ├── base.py           # 数据模型 NewsItem 与基类
│   │   ├── hackernews.py     # Hacker News Algolia 接口
│   │   ├── huggingface.py    # Hugging Face Daily Papers 接口
│   │   ├── github.py         # GitHub 开源生态搜索
│   │   └── rss.py            # 标准 RSS/Atom 极速解析器
│   ├── processor/            # 核心处理与 LLM 提炼
│   │   ├── cleaner.py        # 去重与清洗
│   │   ├── gemini_summarizer.py # Google Gemini 结构化 Prompt
│   │   └── mock_summarizer.py   # 本地快速预览模拟器
│   └── exporters/            # 导出与分发
│       └── markdown_exporter.py # 生成精美排版的 Markdown 日报
└── reports/                  # 历史日报存储归档
    ├── 2026-11-14_AI_Daily_Briefing.md
    └── 2026-11-14_AI_Daily_Briefing.json
```
