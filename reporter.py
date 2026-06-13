"""
reporter.py — 报告生成模块

功能：
1. 生成结构化 Markdown 报告
2. 保存到 output/ 目录
"""

import os
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def generate_markdown_report(
    keyword: str,
    analysis: dict[str, Any],
    suggestions: list[str],
    notes_list: list[dict],
) -> str:
    """
    生成 Markdown 格式的竞品监控报告。

    Parameters
    ----------
    keyword : str
        搜索关键词。
    analysis : dict
        由 analyze_titles() + find_viral_patterns() 合并的分析结果。
    suggestions : list[str]
        由 generate_suggestions() 生成的优化建议。
    notes_list : list[dict]
        原始笔记列表。

    Returns
    -------
    str
        完整 Markdown 报告内容。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sample_count = len(notes_list)

    # ── 标题分析数据 ──
    avg_length = analysis.get("avg_length", 0)
    emoji_ratio = analysis.get("emoji_ratio", 0)
    keywords = analysis.get("common_keywords", [])
    title_patterns = analysis.get("title_patterns", {})

    # ── 爆款分析数据 ──
    avg_likes_top3 = analysis.get("avg_likes_of_top3", 0)
    common_topics = analysis.get("common_topics", [])
    success_factors = analysis.get("success_factors", [])

    # ── 最佳笔记 ──
    best_note = max(notes_list, key=lambda n: n.get("likes", 0)) if notes_list else {}

    # ── 标题建议长度区间 ──
    length_advice = "15-20字"
    if avg_length < 12:
        length_advice = "15-20字"
    elif avg_length > 25:
        length_advice = "15-20字"
    else:
        length_advice = f"当前{avg_length}字左右"

    # ── 标题模式分布排序 ──
    sorted_patterns = sorted(
        title_patterns.items(), key=lambda x: x[1], reverse=True
    )

    lines: list[str] = []

    # === 标题 ===
    lines.append(f"# 📊 小红书「{keyword}」领域竞品监控报告")
    lines.append("")
    lines.append(
        f"> 生成时间：{now} "
        f"| 分析范围：最近7天 "
        f"| 样本量：{sample_count}条爆款笔记"
    )
    lines.append("")

    # === 本周热门话题 ===
    lines.append("## 🔥 本周热门话题 TOP5")
    if common_topics:
        for i, topic in enumerate(common_topics[:5], 1):
            lines.append(f"{i}. {topic}")
    else:
        lines.append("暂无数据")
    lines.append("")

    # === 爆款标题规律 ===
    lines.append("## 📝 爆款标题规律")
    lines.append("")
    lines.append(f"- **平均字数**：{avg_length}字（建议控制在{length_advice}左右）")
    lines.append(f"- **Emoji使用率**：{emoji_ratio * 100:.0f}%")
    lines.append(f"- **数字使用率**：{analysis.get('number_ratio', 0) * 100:.0f}%")

    kw_str = "、".join([w for w, _ in keywords[:5]]) if keywords else "暂无数据"
    lines.append(f"- **高频关键词**：{kw_str}")
    lines.append("")

    # 标题模式分布
    if sorted_patterns:
        dist = " | ".join(f"{p}: {c}条" for p, c in sorted_patterns if c > 0)
        lines.append(f"- **标题模式分布**：{dist}")
    lines.append("")

    # 典型标题示例
    lines.append("- **典型标题示例**：")
    top_titles = sorted(
        notes_list, key=lambda n: n.get("likes", 0), reverse=True
    )[:3]
    for n in top_titles:
        title = n.get("title", "无标题")
        likes = n.get("likes", 0)
        lines.append(f"  - 《{title}》（{likes}赞）")
    lines.append("")

    # === 内容优化建议 ===
    lines.append("## 💡 内容优化建议")
    lines.append("")
    for i, s in enumerate(suggestions, 1):
        lines.append(f"{i}. {s}")
    lines.append("")

    # === 数据亮点 ===
    lines.append("## 📈 数据亮点")
    lines.append("")
    if best_note:
        best_title = best_note.get("title", "无")
        best_likes = best_note.get("likes", 0)
        lines.append(f"- **最高点赞笔记**：《{best_title}》（{best_likes}赞）")
    lines.append(f"- **TOP3平均点赞**：{avg_likes_top3}")
    lines.append(f"- **词云关键词TOP3**：{kw_str}")
    if success_factors:
        lines.append(f"- **爆款共性**：{success_factors[0]}")
    lines.append("")

    # === 行动建议 ===
    lines.append("## 🎯 你的下周行动建议")
    lines.append("")
    lines.append("- **建议发布时间**：")
    lines.append("  - 周三/周四 上午10-12点（职场类内容互动高峰）")
    lines.append("  - 周六/周日 晚上8-10点（用户浏览高峰）")
    lines.append("")
    lines.append("- **建议内容方向**：")
    if common_topics:
        topics_str = "、".join(common_topics[:3])
        lines.append(f"  - 围绕「{topics_str}」等热点话题创作")
    lines.append("  - 制作对比类内容（如『面试穿什么vs不要穿什么』）")
    lines.append("  - 标题加入数字和 emoji 提升信息流点击率")
    lines.append("")
    lines.append("- **建议蹭的热点**：")
    lines.append("  - 关注小红书官方近期活动和话题挑战")
    lines.append("  - 结合当季热点（换季穿搭、节假日出行穿搭）")
    lines.append("  - 参考同领域头部博主的最新内容方向")
    lines.append("")

    lines.append("---")
    lines.append(f"*报告由小红书监控系统自动生成 | {now}*")
    lines.append("")

    return "\n".join(lines)


def save_report(report_content: str, keyword: str) -> str:
    """
    将 Markdown 报告保存到 output/ 目录。

    Parameters
    ----------
    report_content : str
        Markdown 格式的报告内容。
    keyword : str
        关键词，用于文件名。

    Returns
    -------
    str
        保存的文件绝对路径。
    """
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    safe_keyword = keyword.replace(" ", "_").replace("/", "_")
    filename = f"{safe_keyword}_{date_str}.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_content)

    logger.info(f"报告已保存: {filepath}")
    return os.path.abspath(filepath)
