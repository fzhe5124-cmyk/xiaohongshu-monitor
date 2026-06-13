"""
main.py — 小红书竞品监控系统 主程序入口

功能：
1. 交互式菜单（单次分析 / 定时任务 / 历史报告）
2. 核心分析流程串联
3. 定时任务（每日9点自动分析 + 推送）
"""

import logging
import os
import re
import sys
import threading
import time
from datetime import datetime
from typing import Optional

import schedule

from scraper import search_notes
from analyzer import analyze_titles, find_viral_patterns, generate_suggestions
from reporter import generate_markdown_report, save_report
from notifier import send_to_wechat
from config import SEND_KEY, KEYWORDS, MIN_LIKES, SEARCH_DAYS

# ── GBK 终端下 emoji 降级 ──────────────────────────────────
try:
    "⚡".encode(sys.stdout.encoding or "utf-8")
    _CAN_EMOJI = True
except (UnicodeEncodeError, UnicodeDecodeError):
    _CAN_EMOJI = False


def _emoji(text: str) -> str:
    """如果终端不支持 emoji，自动移除。"""
    if _CAN_EMOJI:
        return text
    return re.sub(r"[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\w\s\.\,\!\?\-\:\;\(\)\[\]\{\}]", "", text)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

VERSION = "v1.0"


def run_analysis(keyword: str) -> Optional[str]:
    """
    执行一次完整的分析流程。

    Parameters
    ----------
    keyword : str
        搜索关键词。

    Returns
    -------
    str or None
        报告文件的绝对路径，如果失败则返回 None。
    """
    print(f"\n{'='*50}")
    print(f"  正在分析关键词：「{keyword}」")
    print(f"{'='*50}\n")

    print("[1/4] 正在获取笔记数据...")
    notes = search_notes(keyword, days=SEARCH_DAYS, min_likes=MIN_LIKES)
    if not notes:
        logger.error(f"未找到关键词「{keyword}」的笔记数据")
        print("  \u274c 未找到相关笔记，请尝试其他关键词。")
        return None
    print(f"  \u2705 获取到 {len(notes)} 条笔记")

    print("[2/4] 正在分析标题特征...")
    title_analysis = analyze_titles(notes)

    print("[2/4] 正在分析爆款规律...")
    viral_analysis = find_viral_patterns(notes)
    analysis = {**title_analysis, **viral_analysis}

    print("  \u2705 分析完成")
    print(f"     平均标题长度: {analysis['avg_length']} 字")
    print(f"     Emoji 使用率: {analysis['emoji_ratio']*100:.0f}%")
    print(f"     TOP3 平均点赞: {analysis['avg_likes_of_top3']}")

    print("[3/4] 正在生成优化建议...")
    suggestions = generate_suggestions(analysis)
    print(f"  \u2705 生成 {len(suggestions)} 条优化建议")

    print("[4/4] 正在生成报告...")
    report_content = generate_markdown_report(keyword, analysis, suggestions, notes)
    report_path = save_report(report_content, keyword)
    print(f"  \u2705 报告已保存: {report_path}")

    print(f"\n{'='*50}")
    print(f"  \U0001f4ca 报告摘要 \u2014 「{keyword}」")
    print(f"{'='*50}")
    print(f"  \u2022 热门话题: {', '.join(analysis.get('common_topics', [])[:5])}")
    print(f"  \u2022 高频关键词: {', '.join(w for w, _ in analysis.get('common_keywords', [])[:5])}")
    print(f"  \u2022 最高点赞: {max(n.get('likes', 0) for n in notes)} 赞")
    print(f"  \u2022 优化建议数: {len(suggestions)} 条")
    print(f"{'='*50}\n")

    return report_path


def menu_single_analysis():
    """菜单1: 单次分析"""
    print()
    keyword = input("请输入要分析的关键词（如：职场穿搭）: ").strip()
    if not keyword:
        print("  \u26a0\ufe0f 关键词不能为空")
        return

    report_path = run_analysis(keyword)
    if report_path is None:
        return

    print()
    choice = input("是否推送到微信？(y/n, 默认 n): ").strip().lower()
    if choice == "y" or choice == "yes":
        if not SEND_KEY:
            print("  \u26a0\ufe0f 未配置 SEND_KEY，无法推送。请先设置 config.py 或 .env 中的 SEND_KEY。")
        else:
            success = send_to_wechat(report_path, keyword)
            if success:
                print("  \u2705 微信推送成功！请查收手机通知。")
            else:
                print("  \u274c 微信推送失败，请检查 SEND_KEY 是否正确。")

    print("\n按 Enter 键返回主菜单...")
    input()


def menu_scheduled_task():
    """菜单2: 设置定时任务"""
    print()
    print("\U0001f4c5 设置定时任务")
    print("-" * 30)
    print("定时任务将每天上午 9:00 自动执行分析并推送微信。")
    print()

    task_keywords = input("请输入要监控的关键词（多个用逗号分隔）: ").strip()
    if not task_keywords:
        print("  \u26a0\ufe0f 关键词不能为空")
        return

    kw_list = [kw.strip() for kw in task_keywords.split(",") if kw.strip()]

    print(f"\n已设置监控关键词: {', '.join(kw_list)}")
    print("定时任务将在每天 09:00 自动运行。")
    print("注意：保持此终端窗口打开，或使用系统定时任务（如 Windows 任务计划程序）。")
    print()

    if not SEND_KEY:
        print("  \u26a0\ufe0f 未配置 SEND_KEY，定时任务推送将失败。请先设置 config.py 或 .env 中的 SEND_KEY。")
        print()

    print("按 Enter 键返回主菜单（定时任务仍在后台运行）...")
    input()

    def _job_wrapper(kw: str):
        logger.info(f"\u23f0 定时任务触发: 分析「{kw}」")
        print(f"\n{'='*50}")
        print(f"  \u23f0 定时任务 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"  正在分析关键词：「{kw}」")
        print(f"{'='*50}\n")
        report_path = run_analysis(kw)
        if report_path:
            success = send_to_wechat(report_path, kw)
            status = "\u2705 推送成功" if success else "\u274c 推送失败"
            logger.info(f"定时任务「{kw}」完成, {status}")

    def _scheduler_loop():
        logger.info("定时任务线程已启动")
        for kw in kw_list:
            schedule.every().day.at("09:00").do(_job_wrapper, kw)
        while True:
            schedule.run_pending()
            time.sleep(30)

    thread = threading.Thread(target=_scheduler_loop, daemon=True)
    thread.start()
    logger.info(f"定时任务已设置: {', '.join(kw_list)} 每天 09:00")


def menu_list_reports():
    """菜单3: 查看历史报告"""
    output_dir = os.path.join(os.path.dirname(__file__), "output")

    if not os.path.isdir(output_dir):
        print("\n  \U0001f4c2 output/ 目录不存在，暂无报告。\n")
        input("按 Enter 键返回主菜单...")
        return

    md_files = [f for f in os.listdir(output_dir) if f.endswith(".md")]
    if not md_files:
        print("\n  \U0001f4c2 output/ 目录下暂无报告。\n")
        input("按 Enter 键返回主菜单...")
        return

    md_files.sort(
        key=lambda f: os.path.getmtime(os.path.join(output_dir, f)),
        reverse=True,
    )

    print(f"\n\U0001f4c2 历史报告（共 {len(md_files)} 份）")
    print("-" * 60)
    for i, fname in enumerate(md_files, 1):
        fpath = os.path.join(output_dir, fname)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M")
        size = os.path.getsize(fpath)
        print(f"  {i:2d}. {fname}  ({mtime}, {size} \u5b57\u8282)")
    print("-" * 60)

    print()
    choice = input("输入编号查看报告内容（Enter 返回）: ").strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(md_files):
            fpath = os.path.join(output_dir, md_files[idx])
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                print(f"\n{'='*60}")
                print(content)
                print(f"{'='*60}")
            except Exception as e:
                print(f"  \u274c 读取文件失败: {e}")
            print("\n按 Enter 键返回主菜单...")
            input()


def _start_default_scheduled_tasks():
    """启动默认的定时任务（如果 KEYWORDS 已自定义）"""
    kw_list = [kw.strip() for kw in KEYWORDS if kw.strip()]
    if len(kw_list) > 0 and kw_list != ["职场穿搭"]:
        logger.info(f"检测到自定义关键词，自动启用定时任务: {kw_list}")

        def _job_wrapper(kw: str):
            logger.info(f"\u23f0 定时任务触发: 分析「{kw}」")
            report_path = run_analysis(kw)
            if report_path:
                send_to_wechat(report_path, kw)

        def _scheduler_loop():
            for kw in kw_list:
                schedule.every().day.at("09:00").do(_job_wrapper, kw)
            while True:
                schedule.run_pending()
                time.sleep(30)

        thread = threading.Thread(target=_scheduler_loop, daemon=True)
        thread.start()
        logger.info(f"后台定时任务已启动: {', '.join(kw_list)} 每天 09:00")


# 打猴子补丁：让 print 自动过滤 emoji
_original_print = print
import builtins as _builtins


def _safe_print(*args, sep=" ", end="\n", file=None, flush=False):
    filtered = []
    for a in args:
        if isinstance(a, str):
            filtered.append(_emoji(a))
        else:
            filtered.append(str(a))
    _original_print(*filtered, sep=sep, end=end, file=file, flush=flush)


_builtins.print = _safe_print


def show_menu():
    """显示主菜单并等待用户选择。"""
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print()
        print("=" * 45)
        print("   小红书竞品监控系统 {}".format(VERSION))
        print("=" * 45)
        print()
        print("   1. \U0001f50d 单次分析（输入关键词，立即生成报告）")
        print("   2. \u23f0 设置定时任务（每天 9:00 自动分析）")
        print("   3. \U0001f4c2 查看历史报告")
        print("   0. \U0001f6aa 退出")
        print()
        print("=" * 45)
        print()

        choice = input("请选择操作 (0-3): ").strip()

        if choice == "1":
            menu_single_analysis()
        elif choice == "2":
            menu_scheduled_task()
        elif choice == "3":
            menu_list_reports()
        elif choice == "0":
            print("\n  \U0001f44b 感谢使用，再见！\n")
            sys.exit(0)
        else:
            print("  \u26a0\ufe0f 无效选择，请输入 0-3")
            time.sleep(1)


def main():
    """程序入口。"""
    print()
    print("  \u26a1 小红书竞品监控系统 {} 启动中...".format(VERSION))

    if not SEND_KEY:
        print("  \u26a0\ufe0f 未检测到 SEND_KEY 配置，微信推送功能不可用。")
        print("    如需推送，请注册 Server酱 (https://sct.ftqq.com/)")
        print("    并将 SendKey 写入 .env 文件: SEND_KEY=你的Key")
    else:
        print("  \u2705 微信推送已配置")

    _start_default_scheduled_tasks()
    show_menu()


if __name__ == "__main__":
    main()
