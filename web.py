"""
web.py — Flask Web 服务

功能：
1. 首页：输入密钥 → 进入主界面
2. 内容分析：输入关键词 → 生成报告
3. Pro 专业版 API：五大竞品分析工具
"""

import hashlib
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Optional

import markdown as md_lib
import requests
from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, session, url_for

from analyzer import (
    analyze_titles,
    find_viral_patterns,
    generate_suggestions,
    find_dark_horse_accounts,
    deconstruct_top_viral_notes,
    hot_trend_alert,
    find_content_gap,
    analyze_business_model,
)
from config import ACCESS_KEY, SEARCH_DAYS, WEB_PORT
from reporter import generate_markdown_report, save_report
from scraper import search_notes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("web")

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# ── 订单存储（内存） ─────────────────────────────────────────
ORDERS: dict[str, dict] = {}


def _generate_order_id() -> str:
    return "XS" + datetime.now().strftime("%y%m%d%H%M%S") + uuid.uuid4().hex[:6].upper()


# ── 密钥验证装饰器 ───────────────────────────────────────────


def login_required(f):
    """需要密钥才能访问的页面装饰器。"""
    def wrapper(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


# ── 路由: 登录页 ─────────────────────────────────────────────


@app.route("/login", methods=["GET", "POST"])
def login():
    """登录页：输入密钥。"""
    error = None
    if request.method == "POST":
        key = request.form.get("key", "").strip()
        if key == ACCESS_KEY:
            session["authenticated"] = True
            session.permanent = True
            return redirect(url_for("index"))
        else:
            error = "密钥错误，请重试"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── 路由: 首页 ───────────────────────────────────────────────


@app.route("/")
@login_required
def index():
    """主界面。"""
    return render_template("index.html")


# ── 路由: 创建订单 → 分析 → 报告 ─────────────────────────


@app.route("/create-order", methods=["POST"])
@login_required
def create_order():
    """创建分析订单并直接执行。"""
    keyword = request.form.get("keyword", "").strip()
    if not keyword:
        return render_template("index.html", error="请输入关键词")

    order_id = _generate_order_id()
    ORDERS[order_id] = {
        "keyword": keyword,
        "status": "paid",
        "report_path": None,
        "created_at": datetime.now(),
    }
    return redirect(url_for("run_report", order_id=order_id))


# ── 路由: 执行分析 + 报告展示 ────────────────────────────────


@app.route("/report/<order_id>")
@login_required
def run_report(order_id: str):
    """执行分析并展示报告。"""
    order = ORDERS.get(order_id)
    if not order:
        abort(404)

    if order.get("report_path") and os.path.exists(order["report_path"]):
        return _show_report(order["report_path"], order["keyword"])

    keyword = order["keyword"]
    logger.info(f"开始分析: {keyword} (订单 {order_id})")

    try:
        notes = search_notes(keyword, days=SEARCH_DAYS, min_likes=0)
        if not notes:
            return render_template("report.html", error=f"未找到关键词「{keyword}」的相关笔记",
                                   keyword=keyword)

        title_analysis = analyze_titles(notes)
        viral_analysis = find_viral_patterns(notes)
        analysis = {**title_analysis, **viral_analysis}
        suggestions = generate_suggestions(analysis)

        report_content = generate_markdown_report(keyword, analysis, suggestions, notes)
        report_path = save_report(report_content, keyword)
        order["report_path"] = report_path

        return _show_report(report_path, keyword)

    except Exception as e:
        logger.error(f"分析失败: {e}", exc_info=True)
        return render_template("report.html", error=f"分析出错: {str(e)}", keyword=keyword)


def _show_report(report_path: str, keyword: str):
    """渲染报告 HTML。"""
    with open(report_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    html_content = md_lib.markdown(md_content, extensions=["fenced_code", "tables", "nl2br"])
    return render_template("report.html", keyword=keyword, report_html=html_content)


@app.route("/report-raw/<order_id>")
@login_required
def report_raw(order_id: str):
    """返回原始 Markdown 文件。"""
    order = ORDERS.get(order_id)
    if not order or not order.get("report_path"):
        abort(404)
    return send_file(order["report_path"], as_attachment=True)


# ── Pro 专业版 API ────────────────────────────────────────────


@app.route("/api/pro/<func>", methods=["POST"])
@login_required
def api_pro(func: str):
    """Pro 专业版五大功能 API。"""
    keyword = request.form.get("keyword", "").strip()
    if not keyword:
        return jsonify({"error": "请输入关键词"})

    try:
        notes = search_notes(keyword, days=SEARCH_DAYS, min_likes=0, use_mock=True)
        if not notes:
            return jsonify({"error": f"未找到关键词「{keyword}」的相关笔记"})

        if func == "dark_horse":
            accounts = find_dark_horse_accounts(notes)
            return jsonify({"keyword": keyword, "total_notes": len(notes), "accounts": accounts})
        elif func == "deconstruct":
            results = deconstruct_top_viral_notes(notes, top_n=3)
            return jsonify({"keyword": keyword, "results": results})
        elif func == "trend":
            return jsonify(hot_trend_alert(keyword, notes))
        elif func == "gap":
            return jsonify(find_content_gap(keyword, notes))
        elif func == "biz":
            return jsonify(analyze_business_model(keyword, notes))
        else:
            return jsonify({"error": f"未知功能: {func}"})

    except Exception as e:
        logger.error(f"Pro API 错误: {e}", exc_info=True)
        return jsonify({"error": f"分析出错: {str(e)}"})


# ── 启动 ──────────────────────────────────────────────────────


def main():
    print()
    print("=" * 50)
    print("  小红书竞品监控系统 - Web 服务")
    print("=" * 50)
    print()
    print(f"  本地地址: http://localhost:{WEB_PORT}")
    print(f"  访问密钥: {ACCESS_KEY}")
    print()
    print(f"  按 Ctrl+C 停止服务")
    print()

    app.run(host="0.0.0.0", port=WEB_PORT, debug=False)


if __name__ == "__main__":
    main()
