"""
config.py — 配置文件

使用方式：
1. 复制本文件为 .env 文件，填入真实值
2. 或直接在这里修改配置（不推荐将敏感信息提交到 Git）
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Server酱推送配置 ─────────────────────────────────────────
# 注册地址：https://sct.ftqq.com/
# 获取 SendKey 后填入下方，或写入 .env 文件：
#   SEND_KEY=你的SendKey
SEND_KEY = os.getenv("SEND_KEY", "")

# ── 可选：报告公网地址（用于推送时提供下载链接） ──────────
# 如果你将 output 目录部署到了公网服务器，可以设置此地址
# 例如：https://your-server.com/reports/
REPORT_BASE_URL = os.getenv("REPORT_BASE_URL", "")

# ── 爬虫配置 ─────────────────────────────────────────────────
# 搜索关键词列表（用逗号分隔）
KEYWORDS = os.getenv("KEYWORDS", "职场穿搭").split(",")

# 每次搜索的最低点赞数
MIN_LIKES = int(os.getenv("MIN_LIKES", "100"))

# 搜索时间范围（天）
SEARCH_DAYS = int(os.getenv("SEARCH_DAYS", "7"))

# ── 访问密钥配置 ─────────────────────────────────────────────
# 用户需要输入此密钥才能使用系统功能
# 你可以改成自己的密钥，例如：ACCESS_KEY=xiaohongshu2024
ACCESS_KEY = os.getenv("ACCESS_KEY", "xiaohongshu2024")

# ── Web 服务配置 ─────────────────────────────────────────────
# 本地运行端口
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
