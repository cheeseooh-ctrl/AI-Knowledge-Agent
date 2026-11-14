# -*- coding: utf-8 -*-

# ==============================================================================
# 🛠️ src/utils.py - 通用底层工具库（水电工）
#
# 【小白通俗理解】：
# 这个文件是全项目的“后勤保障部”。
# 里面放着最基础的通用功能：怎么读文件？怎么连网发 HTTP 请求？怎么处理超时和报错？
# 特点：采用了“双模兼容设计”——无论你的电脑有没有通过 pip 安装 requests 库，
# 它都能自动使用 Python 3 原生内置的标准网络库工作，保证代码在任何环境“开箱即用”。
# ==============================================================================

import os             # 负责跟操作系统打交道（检查文件是否存在、读取环境变量）
import json           # 负责把 JSON 字符串和 Python 字典互相转换
import logging        # 负责在控制台输出带时间、带严重程度的日志
import ssl            # 负责处理 HTTPS 加密证书通道（防止网络抓取时因证书问题断连）
from typing import Optional, Dict, Any # 类型注解（帮助编辑器做语法提示，不影响实际运行）

# ------------------------------------------------------------------------------
# 📝 配置全局标准日志格式
# ------------------------------------------------------------------------------
# 规定打印在终端的每一行长成什么样：[时间] [日志等级] 模块名: 具体内容
logging.basicConfig(
    level=logging.INFO, # 默认只显示 INFO（普通信息）及以上级别的日志，忽略 DEBUG 琐碎日志
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AIAgent") # 创建一个名为 "AIAgent" 的专用日志员


def load_env(env_path: str = ".env") -> Dict[str, str]:
    """
    【读取 .env 环境变量文件】：
    .env 文件通常存放敏感数据（如 API Key），这个函数负责把里面的配置读入内存。
    特点：即使用户没有安装 python-dotenv 库，它自己用纯 Python 逐行解析也能读出来。
    """
    env_vars: Dict[str, str] = {}
    # 如果电脑里根本没有这个 .env 文件，直接礼貌返回空字典，绝不崩溃报错
    if not os.path.exists(env_path):
        return env_vars

    try:
        # 打开 .env 文件并按 utf-8 编码一行行读取
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip() # 去掉行首行尾的空格和换行符
                # 如果这一行是空的，或者是用 # 开头的注释，就直接跳过不看
                if not line or line.startswith("#"):
                    continue
                # 如果这一行包含等号，说明是 KEY=VALUE 格式
                if "=" in line:
                    key, val = line.split("=", 1) # 只按第一个等号切开成左右两块
                    key = key.strip()             # 提取左边的名字（比如 GEMINI_API_KEY）
                    val = val.strip().strip("'\"")# 提取右边的值，并剥除外层的单引号或双引号
                    env_vars[key] = val
                    # 同时顺便把它写入 Python 系统的当前环境变量中，方便随时读取
                    if key not in os.environ:
                        os.environ[key] = val
    except Exception as e:
        logger.warning(f"读取环境文件 {env_path} 时发生小异常: {e}")

    return env_vars


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    【读取 config.json 配置文件】：
    把我们写好的抓取规则、关键词和模型名字，以字典形式加载出来。
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件找不到了，请检查路径: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f) # json.load 能把文件里的文本直接解析为 Python 字典


def http_get(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> Optional[str]:
    """
    【发起 HTTP GET 请求（通用的网页与数据下载器）】：
    输入一个网址，它负责把那个网页或接口返回的文本带回来。
    特点：优先尝试使用好用的 requests 库；如果没有安装，自动使用 Python 自带的 urllib。
    """
    # 伪装一个合法的浏览器“用户代理（User-Agent）”，防止对方服务器以为是恶意脚本直接拦截
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 AIDailyAgent/1.0",
        "Accept": "application/json, text/html, application/xml, */*"
    }
    # 如果调用方传了额外的请求头，就合并进去
    if headers:
        default_headers.update(headers)

    # 方案 1：优先尝试第三方的 requests 库（如果电脑里已经装了）
    try:
        import requests
        resp = requests.get(url, headers=default_headers, timeout=timeout)
        if resp.status_code == 200: # 200 代表网络请求大获成功
            return resp.text
        logger.warning(f"访问 {url} 失败，对方服务器返回状态码: {resp.status_code}")
        return None
    except ImportError:
        # 如果电脑没装 requests，不要慌，什么都不做，直接自动滑入方案 2
        pass
    except Exception as e:
        logger.warning(f"requests GET 网络连接失败 {url}: {e}")
        return None

    # 方案 2：Python 标准库 urllib 兜底（任何装了 Python 的电脑都有，零依赖！）
    import urllib.request
    import urllib.error

    # 创建一个网络请求任务
    req = urllib.request.Request(url, headers=default_headers)
    ctx = ssl.create_default_context() # 创建标准 SSL 加密上下文，保障 HTTPS 安全

    try:
        # 真正发起网络通信连接
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            # 读取网络传回的二进制字节，并用 utf-8 解码成人类可读的文字
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        logger.warning(f"HTTP 错误 (状态码 {e.code})：访问 {url} 失败")
        return None
    except Exception as e:
        logger.warning(f"urllib 抓取失败 {url}: {e}")
        return None


def http_post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """
    【发起 HTTP POST 请求（专门用来向大模型发送 Prompt 并接收回答）】：
    与 GET 只是“索取”不同，POST 是“带上我们自己的数据（Prompt）送给对方服务器”。
    发送的是 JSON 格式，收回来的也自动解析成 Python 字典。
    """
    default_headers = {
        "Content-Type": "application/json", # 告诉对方服务器：我发给你的是一段合法的 JSON
        "User-Agent": "AIDailyAgent/1.0"
    }
    if headers:
        default_headers.update(headers)

    # 方案 1：优先使用 requests 库
    try:
        import requests
        resp = requests.post(url, json=payload, headers=default_headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.json() # 把大模型返回的 JSON 文本直接变成字典
        logger.error(f"POST {url} 失败，状态码 {resp.status_code}，错误原因: {resp.text[:300]}")
        return None
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"requests POST 连线失败 {url}: {e}")
        return None

    # 方案 2：标准库 urllib 原生兜底
    import urllib.request
    import urllib.error

    # 把要发送的 Python 字典转成 JSON 字符串，再编码成网络传输的二进制字节 (bytes)
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, headers=default_headers, method="POST")
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            resp_text = response.read().decode("utf-8", errors="replace")
            return json.loads(resp_text) # 解析大模型返回的 JSON 数据
    except urllib.error.HTTPError as e:
        # 如果大模型接口返回 400（参数错误）或 403（密钥不对），把错误原因打印出来
        err_msg = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
        logger.error(f"HTTPError {e.code} POST 失败: {err_msg[:300]}")
        return None
    except Exception as e:
        logger.error(f"urllib POST 通信异常 {url}: {e}")
        return None
