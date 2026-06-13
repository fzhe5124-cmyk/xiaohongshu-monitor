"""
notifier.py — 推送模块（Server酱 → 微信）

使用 Server酱 免费服务将报告推送到微信。
注册地址：https://sct.ftqq.com/
"""

import logging
from typing import Optional

import requests

from config import SEND_KEY, REPORT_BASE_URL

logger = logging.getLogger(__name__)

# Server酱 API 地址
SERVERCHAN_API = "https://sctapi.ftqq.com/{send_key}.send"

# 推送内容最大长度（Server酱限制 text 最长 1000 字，我们截取 500）
MAX_TEXT_LENGTH = 500


def send_to_wechat(report_path: str, keyword: str) -> bool:
    """
    通过 Server酱 将报告推送到微信。

    Parameters
    ----------
    report_path : str
        报告文件的本地路径。
    keyword : str
        搜索关键词。

    Returns
    -------
    bool
        推送是否成功。
    """
    if not SEND_KEY:
        logger.warning("未配置 SEND_KEY，跳过微信推送。请在 config.py 或 .env 中设置。")
        return False

    # ── 读取报告内容 ──
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
    except FileNotFoundError:
        logger.error(f"报告文件不存在: {report_path}")
        return False
    except Exception as e:
        logger.error(f"读取报告文件失败: {e}")
        return False

    # ── 构建推送标题 ──
    title = f"小红书监控「{keyword}」领域周报"

    # ── 构建推送正文 ──
    # 取报告前 MAX_TEXT_LENGTH 字
    text_body = report_content[:MAX_TEXT_LENGTH]

    # 如果报告有公网地址，附加链接
    if REPORT_BASE_URL:
        import os as _os
        filename = _os.path.basename(report_path)
        report_url = f"{REPORT_BASE_URL.rstrip('/')}/{filename}"
        text_body += f"\n\n📎 完整报告：{report_url}"
    else:
        text_body += "\n\n📎 完整报告已保存在 output 目录"

    # ── 发送请求 ──
    url = SERVERCHAN_API.format(send_key=SEND_KEY)
    payload = {
        "title": title,
        "desp": text_body,
    }

    logger.info(f"正在推送报告到微信: {title}")
    try:
        resp = requests.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        result = resp.json()

        if result.get("code") == 0:
            logger.info(f"微信推送成功: {result.get('data', {}).get('pushid', '')}")
            return True
        else:
            logger.error(f"微信推送失败: {result.get('message', '未知错误')}")
            return False

    except requests.RequestException as e:
        logger.error(f"微信推送请求失败: {e}")
        return False
    except ValueError as e:
        logger.error(f"解析推送响应失败: {e}")
        return False


def send_summary_to_wechat(
    keyword: str,
    analysis_summary: str,
    file_path: Optional[str] = None,
) -> bool:
    """
    发送简短分析摘要到微信（不用读取完整报告文件）。

    Parameters
    ----------
    keyword : str
        搜索关键词。
    analysis_summary : str
        简短的分析摘要文本（推荐 300-500 字）。
    file_path : str, optional
        报告文件路径，如果提供会附加链接。

    Returns
    -------
    bool
        推送是否成功。
    """
    if not SEND_KEY:
        logger.warning("未配置 SEND_KEY，跳过微信推送。")
        return False

    title = f"小红书监控「{keyword}」分析快讯"
    text_body = analysis_summary[:MAX_TEXT_LENGTH]

    if file_path and REPORT_BASE_URL:
        import os as _os
        filename = _os.path.basename(file_path)
        report_url = f"{REPORT_BASE_URL.rstrip('/')}/{filename}"
        text_body += f"\n\n📎 完整报告：{report_url}"

    url = SERVERCHAN_API.format(send_key=SEND_KEY)
    payload = {"title": title, "desp": text_body}

    try:
        resp = requests.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        return result.get("code") == 0
    except Exception as e:
        logger.error(f"推送摘要失败: {e}")
        return False
