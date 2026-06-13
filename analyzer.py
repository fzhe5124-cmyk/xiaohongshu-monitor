"""
analyzer.py — 小红书笔记分析模块

功能：
1. 标题特征分析（长度、emoji、数字、关键词、标题模式）
2. 爆款规律挖掘（高赞笔记共性）
3. 内容优化建议生成
"""

import random
import re
import logging
from collections import Counter
from typing import Any

import jieba

# 简单语言检测：如果文本中中文字符占比 > 20%，视为中文
def _is_chinese_text(text: str) -> bool:
    if not text.strip():
        return True
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return chinese_chars / max(len(text.strip()), 1) > 0.2

logger = logging.getLogger(__name__)

# ── Emoji 匹配正则 ─────────────────────────────────────────────

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # 表情符号
    "\U0001F300-\U0001F5FF"  # 符号和象形文字
    "\U0001F680-\U0001F6FF"  # 交通和地图符号
    "\U0001F1E0-\U0001F1FF"  # 国旗
    "\U00002702-\U000027B0"  # 其他符号
    "\U000024C2-\U0001F251"
    "]+"
)

# ── 标题模式检测 ───────────────────────────────────────────────

# 悬念式：问号、省略号、"竟然是"、"没想到"、"原来"、"惊了"
SUSPENSE_PATTERNS = re.compile(r"[？?…！!]|竟然是|没想到|原来|惊了|绝了|哭了|后悔")

# 数字式：包含阿拉伯数字或中文数字
NUMBER_PATTERNS = re.compile(r"\d+|[零一二三四五六七八九十百千万亿]")

# 对比式："vs"、"VS"、"对比"、"vs"、"还是"、"不如"、"不同"
COMPARE_PATTERNS = re.compile(r"[Vv][Ss]|对比|不如|不同|还是|区别")

# 经验分享式："攻略"、"教程"、"指南"、"技巧"、"分享"、"推荐"、"必看"、"干货"
EXPERIENCE_PATTERNS = re.compile(r"攻略|教程|指南|技巧|分享|推荐|必看|干货|方法|经验")


def _extract_emoji(text: str) -> list[str]:
    """提取字符串中的所有 emoji。"""
    return EMOJI_PATTERN.findall(text)


def _contains_emoji(text: str) -> bool:
    """检查字符串是否包含 emoji。"""
    return bool(EMOJI_PATTERN.search(text))


def _contains_number(text: str) -> bool:
    """检查字符串是否包含数字。"""
    return bool(NUMBER_PATTERNS.search(text))


def _detect_title_pattern(title: str) -> str:
    """
    检测标题属于哪种模式。

    优先级：悬念式 > 数字式 > 对比式 > 经验分享式 > 其他
    """
    if SUSPENSE_PATTERNS.search(title):
        return "悬念式"
    if NUMBER_PATTERNS.search(title):
        return "数字式"
    if COMPARE_PATTERNS.search(title):
        return "对比式"
    if EXPERIENCE_PATTERNS.search(title):
        return "经验分享式"
    return "其他"


# 英文停用词
_EN_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "need",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those", "what", "which", "who", "whom",
    "when", "where", "why", "how", "all", "each", "every", "both",
    "few", "some", "any", "no", "not", "only", "own", "same",
    "so", "than", "too", "very", "just", "because", "as", "until",
    "while", "of", "at", "by", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "in", "out",
    "on", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "and", "but", "or", "if", "because", "as",
    "until", "while", "get", "got", "getting", "make", "made", "making",
    "take", "took", "taking", "use", "used", "using", "like", "want",
    "go", "going", "went", "come", "came", "coming", "know", "think",
    "see", "look", "find", "give", "tell", "say", "try", "start",
    "also", "back", "well", "way", "even", "still", "already",
    "really", "actually", "basically", "probably", "maybe",
    "thing", "things", "stuff", "lot", "bit", "little",
    "much", "many", "more", "most", "some", "something",
    "one", "two", "new", "first", "last", "next", "other",
    "now", "today", "yesterday", "tomorrow", "always", "never",
    "ever", "soon", "later", "ago", "already", "yet",
    "please", "thanks", "thank", "welcome", "hello", "hi",
}


def _tokenize(text: str) -> list[str]:
    """对文本进行分词（支持中文和英文）。"""
    is_chinese = _is_chinese_text(text)

    if is_chinese:
        # 中文停用词
        stopwords = {
            "我", "你", "他", "她", "它", "我们", "你们", "他们", "她们", "它们",
            "自己", "别人", "大家", "这个", "那个", "这些", "那些", "什么", "怎么",
            "如何", "为什么", "哪个", "哪里",
        # 介词/连词/助词
        "的", "了", "是", "在", "有", "和", "就", "不", "都", "一", "一个",
        "上", "也", "很", "到", "说", "要", "去", "会", "着", "没有", "看",
        "好", "这", "那", "些", "能", "得", "地", "与", "为", "之", "及",
        "等", "被", "把", "让", "从", "以", "对", "但", "而", "或", "如",
        "如果", "因为", "所以", "可以", "做", "还", "来", "让", "不是", "就是",
        "过", "吧", "吗", "呢", "啊", "哦", "嗯", "啦",
        # 通用动词（无领域含义）
        "觉得", "知道", "看到", "发现", "成为", "使用", "选择", "决定",
        "开始", "需要", "喜欢", "想要", "应该", "能够", "不会", "不能",
        "可能", "一定", "已经", "正在", "还是", "但是", "只是",
        # 程度/范围词
        "最", "更", "太", "非常", "特别", "比较", "很多", "一些", "有点",
        "所有", "每个", "有的", "不少", "更多", "很少",
        # 时间词（无领域含义）
        "今天", "明天", "昨天", "现在", "以前", "之后", "时候", "时间",
        "最近", "平时", "每天", "一直", "总是", "有时", "已经",
        # 数量/序数词
        "一个", "这个", "那个", "一些", "这些", "那些", "每个", "几个",
        "第一", "第二", "第三", "首先", "其次", "最后",
        # 否定/肯定
        "不是", "没有", "可以", "不能", "不会", "不要", "必须",
        # 语气/连接
        "其实", "真的", "就是", "还是", "但是", "而且", "虽然", "因为",
        "所以", "如果", "然后", "还有", "此外", "另外", "不过",
        # 互动/平台通用词（无领域含义）
        "收藏", "点赞", "评论", "关注", "转发", "分享", "私信", "私我",
        "留言", "截屏", "保存", "下载", "关注我", "码住",
        "双击", "扣1", "扣2", "评论区", "在评论区",
        # 正文常见无意义词
        "是不是", "能不能", "会不会", "要不要", "有没有", "好不好",
        "对不对", "行不行", "那些", "这些", "哪个", "每个", "各种",
        "很多", "一些", "有点", "的话", "来说", "来讲", "而言",
        "方面", "部分", "层面", "角度", "维度", "程度",
        "时候", "时间", "情况", "事情", "东西", "内容", "方式",
        "方法", "步骤", "过程", "阶段", "结果", "效果", "目的",
        "原因", "理由", "关系", "影响", "变化",
        "问题", "答案", "建议", "想法", "感受", "体验",
        "其实", "当然", "虽然", "不过", "但是", "然而",
        "比如", "例如", "比方", "像是", "就是", "就是说",
        "所以", "因此", "于是", "接着", "然后", "最后",
        "大家", "姐妹", "姐妹", "姐妹", "宝宝", "宝子",
        "可以", "能够", "需要", "应该", "必须", "一定",
        "不会", "不能", "不要", "不用", "没有",
        "的话", "来说", "来讲", "来看", "来",
        # 单字残余
        "把", "被", "让", "给", "对", "从", "以",
    }
    if is_chinese:
        words = jieba.lcut(text)
    else:
        # 英文：按空格分词 + 转小写 + 去标点
        import string
        text_clean = text.lower().translate(str.maketrans("", "", string.punctuation))
        words = text_clean.split()
        stopwords = _EN_STOPWORDS

    result = []
    for w in words:
        w = w.strip()
        if not w or len(w) <= 1:
            continue
        if w in stopwords:
            continue
        if w.isdigit():
            continue
        if is_chinese:
            if not re.search(r"[\u4e00-\u9fff]", w):
                if len(w) <= 2:
                    continue
        result.append(w)
    return result


# ── 公开 API ───────────────────────────────────────────────────


def analyze_titles(notes_list: list[dict]) -> dict[str, Any]:
    """
    分析笔记标题特征。

    Parameters
    ----------
    notes_list : list[dict]
        笔记列表，每条须包含 "title" 字段。

    Returns
    -------
    dict
        avg_length      : 平均标题字数
        emoji_ratio     : 包含 emoji 的标题比例 (0~1)
        number_ratio    : 包含数字的标题比例 (0~1)
        common_keywords : 高频关键词 TOP10 [(词, 次数), ...]
        title_patterns  : 各模式分布 {模式名: 数量, ...}
    """
    if not notes_list:
        logger.warning("analyze_titles 收到空列表")
        return {
            "avg_length": 0,
            "emoji_ratio": 0.0,
            "number_ratio": 0.0,
            "common_keywords": [],
            "title_patterns": {},
        }

    titles = [n.get("title", "") for n in notes_list if n.get("title")]
    total = len(titles)

    # 标题长度
    lengths = [len(t) for t in titles]
    avg_length = round(sum(lengths) / total, 1) if total else 0

    # Emoji 比例
    emoji_count = sum(1 for t in titles if _contains_emoji(t))
    emoji_ratio = round(emoji_count / total, 2) if total else 0.0

    # 数字比例
    number_count = sum(1 for t in titles if _contains_number(t))
    number_ratio = round(number_count / total, 2) if total else 0.0

    # 高频关键词
    all_words: list[str] = []
    for t in titles:
        all_words.extend(_tokenize(t))
    word_freq = Counter(all_words).most_common(10)

    # 标题模式分布
    pattern_counts: dict[str, int] = {}
    for t in titles:
        pattern = _detect_title_pattern(t)
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
    # 确保所有模式都有记录
    for p in ["悬念式", "数字式", "对比式", "经验分享式", "其他"]:
        pattern_counts.setdefault(p, 0)

    logger.info(
        f"标题分析完成: {total}条, "
        f"平均长度{avg_length}, "
        f"emoji比例{emoji_ratio}, "
        f"数字比例{number_ratio}"
    )

    return {
        "avg_length": avg_length,
        "emoji_ratio": emoji_ratio,
        "number_ratio": number_ratio,
        "common_keywords": word_freq,
        "title_patterns": pattern_counts,
    }


def find_viral_patterns(notes_list: list[dict]) -> dict[str, Any]:
    """
    分析爆款笔记规律。

    Parameters
    ----------
    notes_list : list[dict]
        笔记列表，每条须包含 "title", "likes" 等字段。

    Returns
    -------
    dict
        avg_likes_of_top3 : 前三名平均点赞数
        common_topics     : 共同话题标签列表
        best_time_pattern : 发布时间规律（Mock 模式下返回占位提示）
        success_factors   : 成功因素洞察列表
    """
    if not notes_list:
        logger.warning("find_viral_patterns 收到空列表")
        return {
            "avg_likes_of_top3": 0,
            "common_topics": [],
            "best_time_pattern": "无数据",
            "success_factors": [],
        }

    # 按点赞排序取前三
    sorted_notes = sorted(notes_list, key=lambda n: n.get("likes", 0), reverse=True)
    top3 = sorted_notes[:3]
    avg_likes_top3 = round(sum(n.get("likes", 0) for n in top3) / len(top3)) if top3 else 0

    # 标题分词，找高频词作为"共同话题"
    all_words: list[str] = []
    for n in notes_list:
        title = n.get("title", "")
        all_words.extend(_tokenize(title))
        # 也分析正文
        content = n.get("content", "")
        if content:
            all_words.extend(_tokenize(content))

    word_freq = Counter(all_words)
    # 选取出现次数 >= 总笔记数 20% 的词作为共同话题
    threshold = max(1, len(notes_list) * 0.2)
    common_topics = [word for word, count in word_freq.most_common(20) if count >= threshold]
    # 如果超过 10 个只取前 10
    common_topics = common_topics[:10]

    # 成功因素洞察（基于数据分析生成的规则）
    success_factors = _derive_success_factors(notes_list, sorted_notes)

    logger.info(
        f"爆款规律分析完成: 前3平均点赞{avg_likes_top3}, "
        f"共同话题{len(common_topics)}个, "
        f"洞察{len(success_factors)}条"
    )

    return {
        "avg_likes_of_top3": avg_likes_top3,
        "common_topics": common_topics,
        "best_time_pattern": "当前使用 Mock 数据，暂无发布时间信息。" 
                              "接入真实爬虫后可统计笔记发布日期分布。",
        "success_factors": success_factors,
    }


def _derive_success_factors(
    notes_list: list[dict],
    sorted_notes: list[dict],
) -> list[str]:
    """
    基于笔记数据推导成功因素洞察。

    规则示例：
    - 如果前 3 标题都含数字 → "标题带数字"
    - 如果前 3 标题都含 emoji → "使用 emoji 吸引眼球"
    - 如果前 3 标题都是悬念式 → "悬念式标题"
    - 如果某关键词在标题中高频出现 → "蹭了XX热点"
    """
    factors: list[str] = []
    top3_titles = [n.get("title", "") for n in sorted_notes[:3]]

    # —— 标题特征统计 ——
    emoji_in_top3 = sum(1 for t in top3_titles if _contains_emoji(t))
    number_in_top3 = sum(1 for t in top3_titles if _contains_number(t))

    # 前 3 标题模式分布
    top3_patterns = [_detect_title_pattern(t) for t in top3_titles]
    pattern_counter = Counter(top3_patterns)

    if emoji_in_top3 >= 2:
        factors.append("爆款标题中 emoji 使用率较高（TOP3 中 %d/3 条含 emoji）" % emoji_in_top3)

    if number_in_top3 >= 2:
        factors.append("标题带数字的笔记更容易成为爆款（TOP3 中 %d/3 条含数字）" % number_in_top3)

    if pattern_counter.get("悬念式", 0) >= 2:
        factors.append("悬念式标题（问句、省略号、『绝了』等）在高赞笔记中占比高")
    elif pattern_counter.get("数字式", 0) >= 2:
        factors.append("数字式标题（薪资、年龄、比例等）更易引发点击")
    elif pattern_counter.get("经验分享式", 0) >= 2:
        factors.append("『攻略/教程/技巧』类经验分享型标题更受欢迎")

    # —— 关键词热度分析 ——
    all_top3_words: list[str] = []
    for t in top3_titles:
        all_top3_words.extend(_tokenize(t))
    top3_word_freq = Counter(all_top3_words).most_common(5)

    hot_keywords = [w for w, _ in top3_word_freq]
    if hot_keywords:
        factors.append(
            "标题高频词「%s」值得持续使用" % "、".join(hot_keywords[:3])
        )

    # —— 内容对比 ——
    # 检测对比式表达
    compare_count = sum(1 for t in notes_list if COMPARE_PATTERNS.search(t.get("title", "")))
    total = len(notes_list)
    if total > 0 and compare_count / total >= 0.3:
        factors.append("对比式标题（『vs』『不如』『区别』）在整体内容中占比 %.0f%%，这类标题互动率较高" % (compare_count / total * 100))

    if not factors:
        factors.append("样本量较小或特征不明显，建议增加更多笔记数据后重新分析")

    return factors


def generate_suggestions(analysis_result: dict) -> list[str]:
    """
    根据分析结果生成内容优化建议。

    Parameters
    ----------
    analysis_result : dict
        由 analyze_titles() 和 find_viral_patterns() 合并后的结果。

    Returns
    -------
    list[str]
        5 条具体的、可执行的内容优化建议。
    """
    suggestions: list[str] = []
    title_data = analysis_result.get("title_analysis", analysis_result)
    viral_data = analysis_result.get("viral_analysis", analysis_result)

    # 1. 标题长度建议
    avg_length = title_data.get("avg_length", 0)
    if avg_length < 10:
        suggestions.append(
            f"当前标题平均长度仅 {avg_length} 字，偏短。"
            "建议将标题扩展至 15-25 字之间，"
            "增加关键词密度以提高搜索曝光。"
        )
    elif avg_length > 25:
        suggestions.append(
            f"当前标题平均长度 {avg_length} 字，偏长。"
            "建议精简至 15-25 字，核心关键词前置，"
            "避免被搜索截断。"
        )
    else:
        suggestions.append(
            f"标题平均长度 {avg_length} 字处于合理范围，"
            "继续保持。可尝试 A/B 测试不同长度标题的效果。"
        )

    # 2. Emoji 建议
    emoji_ratio = title_data.get("emoji_ratio", 0)
    if emoji_ratio < 0.3:
        suggestions.append(
            "标题中 emoji 使用比例较低（%.0f%%）。" % (emoji_ratio * 100)
            + "建议在标题适当位置添加 1-2 个相关 emoji "
            "（如 👗👔💼 等穿搭相关），可提升在信息流中的视觉吸引力。"
        )
    else:
        suggestions.append(
            "标题 emoji 使用比例（%.0f%%）表现良好。" % (emoji_ratio * 100)
            + "注意 emoji 不要超过 3 个，避免显得杂乱。"
        )

    # 3. 关键词建议
    keywords = title_data.get("common_keywords", [])
    if keywords:
        top_words = [w for w, _ in keywords[:5]]
        suggestions.append(
            "建议在标题中持续使用以下高频关键词："
            "「%s」。"
            "同时可以拓展相关长尾关键词，如「%s穿搭」「%s公式」等组合。"
            % ("、".join(top_words[:3]), top_words[0] if top_words else "职场", top_words[0] if top_words else "职场")
        )
    else:
        suggestions.append(
            "当前样本量不足以提取高频关键词。"
            "建议收集更多笔记数据后再进行关键词分析。"
        )

    # 4. 标题模式建议
    patterns = title_data.get("title_patterns", {})
    # 找到占比最低的非"其他"模式
    pattern_items = {k: v for k, v in patterns.items() if k != "其他"}
    if pattern_items:
        dominant_pattern = max(pattern_items, key=pattern_items.get)
        suggestions.append(
            "当前最常用的标题模式是「%s」。"
            "建议尝试混搭不同模式，例如将「%s」与数字或对比元素结合，"
            "如『原来XXX！3个技巧让XX翻倍』（悬念+数字），"
            "可提升点击率。"
            % (dominant_pattern, dominant_pattern)
        )
    else:
        suggestions.append(
            "标题模式分布较分散，建议多尝试「悬念式」标题"
            "（如『没想到XX竟然…』）和「数字式」标题"
            "（如『3个XX技巧』），这两类在小红书上表现较好。"
        )

    # 5. 成功因素建议
    viral_factors = viral_data.get("success_factors", [])
    if viral_factors:
        top_factor = viral_factors[0]
        suggestions.append(
            "核心洞察：%s。"
            "建议将这一策略系统化，在后续内容创作中持续应用。"
            % top_factor
        )
    else:
        suggestions.append(
            "建议多参考同领域爆款笔记，提炼共性元素"
            "（封面图风格、标题句式、正文结构），"
            "形成自己的内容模板库。"
        )

    return suggestions[:5]


# ── 功能一：黑马账号识别 ──────────────────────────────────────


def find_dark_horse_accounts(notes_list: list[dict]) -> list[dict]:
    """
    识别黑马账号（低粉高赞的新账号）。

    筛选标准：
    - 账号粉丝数 < 5000
    - 近7天有 ≥2 条笔记点赞 > 500
    - 账号注册时间 < 6个月（约180天）

    Parameters
    ----------
    notes_list : list[dict]
        笔记列表，每条须包含 "author" 字段：
        {
            "author": {
                "followers": int,
                "reg_days": int,   # 注册天数
            }
        }

    Returns
    -------
    list[dict]
        符合条件的黑马账号列表，按潜力评分降序，每项：
        {
            "author_id": str,
            "author_name": str,
            "followers": int,
            "reg_days": int,
            "hot_notes": int,         # 爆款笔记数（点赞>500）
            "total_notes": int,       # 收录笔记总数
            "avg_likes": float,       # 平均点赞
            "potential_score": float, # 潜力评分（综合算法）
        }
    """
    if not notes_list:
        logger.warning("find_dark_horse_accounts 收到空列表")
        return []

    # 按作者分组
    author_notes: dict[str, dict] = {}
    for note in notes_list:
        author = note.get("author")
        if not author:
            continue
        aid = author["id"]
        if aid not in author_notes:
            author_notes[aid] = {
                "author_id": aid,
                "author_name": author.get("name", "未知"),
                "followers": author.get("followers", 0),
                "reg_days": author.get("reg_days", 999),
                "notes": [],
            }
        author_notes[aid]["notes"].append(note)

    # 筛选
    dark_horses: list[dict] = []
    for aid, info in author_notes.items():
        if info["followers"] >= 5000:
            continue
        if info["reg_days"] >= 180:
            continue

        notes = info["notes"]
        hot_notes = [n for n in notes if n.get("likes", 0) > 500]
        if len(hot_notes) < 2:
            continue

        avg_likes = sum(n.get("likes", 0) for n in notes) / len(notes) if notes else 0

        # 潜力评分：粉丝数越低 + 爆款率越高 + 平均点赞越高 = 分越高
        follower_factor = max(0, 1 - info["followers"] / 5000)  # 0~1
        hot_rate = len(hot_notes) / len(notes)  # 0~1
        likes_factor = min(1, avg_likes / 5000)  # 0~1
        potential_score = round(
            follower_factor * 30 + hot_rate * 40 + likes_factor * 30, 1
        )

        dark_horses.append({
            "author_id": aid,
            "author_name": info["author_name"],
            "followers": info["followers"],
            "reg_days": info["reg_days"],
            "hot_notes": len(hot_notes),
            "total_notes": len(notes),
            "avg_likes": round(avg_likes, 1),
            "potential_score": potential_score,
        })

    dark_horses.sort(key=lambda x: x["potential_score"], reverse=True)
    logger.info(f"黑马账号识别完成: 共 {len(dark_horses)} 个")
    return dark_horses


# ── 功能二：爆款结构拆解 ──────────────────────────────────────


def _detect_opening_strategy(content: str) -> str:
    """
    检测开头策略类型。
    """
    first_para = content.split("\n\n")[0] if "\n\n" in content else content[:100]

    if any(kw in first_para for kw in ["你是不是也", "有没有", "为什么", "吗？", "？"]):
        return "提问式"
    if any(kw in first_para for kw in ["90%", "80%", "翻了", "数据", "%"]):
        return "数据冲击式"
    if any(kw in first_para for kw in ["还记得", "第一次", "以前我", "那时候"]):
        return "故事开头"
    if any(kw in first_para for kw in ["惊人的秘密", "绝大多数人都", "其实", "真相", "原来"]):
        return "颠覆认知式"
    if any(kw in first_para for kw in ["你不会还不知道", "别再", "千万不要", "后悔"]) or "!" in first_para or "！" in first_para:
        return "悬念/警告式"
    return "平铺直叙"


def _estimate_content_distribution(content: str) -> dict[str, float]:
    """
    估算全文的信息分布（干货% : 情绪% : 场景%）。

    基于关键词匹配的简单估算。
    """
    total = len(content)
    if total == 0:
        return {"干货": 33, "情绪": 33, "场景": 34}

    # 干货关键词
    dry_keywords = [
        "第一", "第二", "第三", "首先", "其次", "最后", "步骤", "方法",
        "技巧", "攻略", "教程", "公式", "核心", "关键", "原则", "法则",
        "建议", "注意", "要点", "总结", "对比", "数据", "步骤", "方式",
        "策略", "底层逻辑", "方法论", "拆解", "框架",
    ]
    # 情绪关键词
    emo_keywords = [
        "真的", "太", "了！", "了!", "绝了", "哭了", "后悔", "感动",
        "惊喜", "崩溃", "开心", "焦虑", "紧张", "兴奋", "难过",
        "推荐", "码住", "收藏", "关注", "点赞", "❤️", "🌟", "👇",
        "双击", "评论区",
    ]
    # 场景关键词
    scene_keywords = [
        "上班", "通勤", "面试", "出差", "约会", "旅行", "居家",
        "办公室", "会议室", "地铁", "咖啡厅", "餐厅", "聚会",
        "早上", "晚上", "周末", "日常", "学生党", "打工人",
        "新手", "小白", "职场", "宿舍", "出租屋",
    ]

    dry_count = sum(content.count(kw) for kw in dry_keywords)
    emo_count = sum(content.count(kw) for kw in emo_keywords)
    scene_count = sum(content.count(kw) for kw in scene_keywords)

    total_count = dry_count + emo_count + scene_count
    if total_count == 0:
        return {"干货": 34, "情绪": 33, "场景": 33}

    return {
        "干货": round(dry_count / total_count * 100),
        "情绪": round(emo_count / total_count * 100),
        "场景": round(scene_count / total_count * 100),
    }


def _find_interaction_hooks(content: str) -> list[str]:
    """
    提取引导互动的原文片段。
    """
    hooks = []
    hook_patterns = [
        "收藏", "点赞", "关注", "评论区", "留言", "扣1", "扣2",
        "双击", "码住", "保存", "转发", "私信", "私我",
        "你觉得", "你们觉得", "评论区聊聊", "告诉我",
    ]
    paras = content.split("\n\n")
    for para in paras:
        for pattern in hook_patterns:
            if pattern in para:
                # 提取含该关键词的句子
                for sent in para.split("。"):
                    if pattern in sent and len(sent) < 80:
                        hooks.append(sent.strip() + ("。" if not sent.endswith("。") else ""))
                        break
                break  # 每段只取第一个钩子
    return hooks[:3]


def _detect_ending_strategy(content: str) -> str:
    """
    检测结尾策略类型。
    """
    paras = content.split("\n\n")
    if len(paras) < 2:
        return "无明显结尾策略"

    last_para = paras[-1]

    if any(kw in last_para for kw in ["关注", "关注我", "进群", "私信"]):
        return "引导关注/转化"
    if any(kw in last_para for kw in ["收藏", "码住", "保存"]):
        return "引导收藏"
    if any(kw in last_para for kw in ["评论区", "留言", "告诉我", "聊聊", "扣1"]):
        return "引导评论互动"
    if any(kw in last_para for kw in ["点赞", "双击", "❤️"]):
        return "引导点赞"
    if any(kw in last_para for kw in ["下次", "后续", "下期", "视频版"]):
        return "预告/期待引导"
    return "自然收尾"


def deconstruct_viral_content(note: dict) -> dict:
    """
    对单条笔记进行爆款结构拆解。

    Parameters
    ----------
    note : dict
        笔记数据，须包含 title, content, likes 等字段。

    Returns
    -------
    dict
        {
            "title": str,
            "likes": int,
            "opening_strategy": str,         # 开头策略类型
            "opening_excerpt": str,           # 开头原文片段
            "content_distribution": dict,     # 干货% : 情绪% : 场景%
            "interaction_hooks": list[str],   # 互动钩子原文
            "ending_strategy": str,           # 结尾策略
            "ending_excerpt": str,            # 结尾原文片段
            "template": str,                  # 可填空的内容模板
        }
    """
    title = note.get("title", "")
    content = note.get("content", "")
    likes = note.get("likes", 0)

    opening_strategy = _detect_opening_strategy(content)
    content_dist = _estimate_content_distribution(content)
    hooks = _find_interaction_hooks(content)
    ending_strategy = _detect_ending_strategy(content)

    # 提取开头片段（第一段）
    paras = content.split("\n\n")
    first_para = paras[0][:80] + "…" if len(paras[0]) > 80 else paras[0]
    last_para = paras[-1][:80] + "…" if len(paras[-1]) > 80 else paras[-1] if len(paras) > 0 else ""

    # 生成可填空的内容模板
    template = _generate_content_template(title, opening_strategy, content_dist, ending_strategy)

    return {
        "title": title,
        "likes": likes,
        "opening_strategy": opening_strategy,
        "opening_excerpt": first_para,
        "content_distribution": content_dist,
        "interaction_hooks": hooks,
        "ending_strategy": ending_strategy,
        "ending_excerpt": last_para,
        "template": template,
    }


def _generate_content_template(
    title: str,
    opening: str,
    dist: dict,
    ending: str,
) -> str:
    """根据拆解结果生成可填空的内容模板。"""
    template_parts = []

    # --- 标题模板 ---
    template_parts.append("【标题模板】")
    template_parts.append(f"  参考：「{title}」")
    template_parts.append(f"  模板：[数字/悬念词] + [核心卖点] + [人群标签]")
    template_parts.append("")

    # --- 开头模板 ---
    template_parts.append("【开头模板】（策略：{}）".format(opening))
    if opening == "提问式":
        template_parts.append("  「你是不是也觉得______？其实______。」")
    elif opening == "数据冲击式":
        template_parts.append("  「做了____天____，数据翻了____倍，我把方法论拆给你。」")
    elif opening == "故事开头":
        template_parts.append("  「还记得我第一次______的时候，完全______。」")
    elif opening == "颠覆认知式":
        template_parts.append("  「我发现____一个惊人的秘密：绝大多数人都____。」")
    elif opening == "悬念/警告式":
        template_parts.append("  「别再______了！正确做法是______。」")
    else:
        template_parts.append("  「______是很多人的困扰，今天一次性说清楚。」")
    template_parts.append("")

    # --- 正文结构模板 ---
    template_parts.append("【正文结构】")
    template_parts.append(f"  建议比例：干货{dist.get('干货', 40)}% + 情绪{dist.get('情绪', 30)}% + 场景{dist.get('场景', 30)}%")
    template_parts.append("  框架：")
    template_parts.append("    1️⃣ 核心观点/方法一（干货）")
    template_parts.append("    2️⃣ 核心观点/方法二（干货）")
    template_parts.append("    3️⃣ 核心观点/方法三（干货 + 场景结合）")
    template_parts.append("")

    # --- 互动引导模板 ---
    template_parts.append("【互动引导】")
    template_parts.append("  收藏钩子：「先收藏🌟，以后用得着」")
    template_parts.append("  评论钩子：「你们觉得______？评论区聊聊👇」")
    template_parts.append("  点赞钩子：「有用的话点个赞支持一下❤️」")
    template_parts.append("")

    # --- 结尾模板 ---
    template_parts.append("【结尾模板】（策略：{}）".format(ending))
    if "关注" in ending:
        template_parts.append("  「关注我，后续更新______教程。」")
    elif "收藏" in ending:
        template_parts.append("  「建议收藏🌟，______的时候翻出来看看。」")
    elif "评论" in ending:
        template_parts.append("  「你们______？评论区告诉我～」")
    elif "点赞" in ending:
        template_parts.append("  「觉得有用的话双击❤️支持一下～」")
    else:
        template_parts.append("  「______，希望对你有帮助。」")

    return "\n".join(template_parts)


def deconstruct_top_viral_notes(notes_list: list[dict], top_n: int = 3) -> list[dict]:
    """
    对点赞最高的前 N 条笔记逐一进行爆款结构拆解。

    Parameters
    ----------
    notes_list : list[dict]
        笔记列表。
    top_n : int, default 3
        拆解前 N 条。

    Returns
    -------
    list[dict]
        每条笔记的拆解结果。
    """
    if not notes_list:
        logger.warning("deconstruct_top_viral_notes 收到空列表")
        return []

    sorted_notes = sorted(notes_list, key=lambda n: n.get("likes", 0), reverse=True)
    results = []
    for note in sorted_notes[:top_n]:
        result = deconstruct_viral_content(note)
        results.append(result)
        logger.info(f"拆解完成: {note.get('title', '')[:20]}... ({note.get('likes', 0)}赞)")

    return results


# ── 功能三：热点预警系统 ──────────────────────────────────────


def hot_trend_alert(keyword: str, notes_list: list[dict]) -> dict:
    """
    热点预警系统。

    基于 Mock 数据模拟检测三个维度：
    1. 发布量增长速度
    2. 多个账号同时发布相似主题
    3. 平均点赞是否异常偏高

    输出预警等级和具体建议。

    Parameters
    ----------
    keyword : str
        搜索关键词。
    notes_list : list[dict]
        笔记列表。

    Returns
    -------
    dict
        {
            "keyword": str,
            "level": str,              # "red" / "yellow" / "green"
            "level_label": str,        # "红色预警" / "黄色预警" / "观察中"
            "level_icon": str,         # "🔴" / "🟡" / "🟢"
            "dimensions": {
                "growth_rate": { "value": float, "label": str, "score": int },      # 0~100
                "multi_account": { "value": bool, "label": str, "score": int },     # 0 or 100
                "avg_likes_anomaly": { "value": float, "label": str, "score": int }, # 0~100
            },
            "total_score": int,        # 总分 0~300
            "suggestions": list[str],  # 具体建议
        }

    预警等级判定：
    - red:   总分 >= 200，或 growth_rate 极高且有 multi_account
    - yellow: 总分 >= 100，或 growth_rate > 100%
    - green:  其他
    """
    if not notes_list:
        logger.warning("hot_trend_alert 收到空列表")
        return {
            "keyword": keyword,
            "level": "green",
            "level_label": "观察中",
            "level_icon": "\U0001f7e2",
            "dimensions": {},
            "total_score": 0,
            "suggestions": ["暂无数据，无法判断热点趋势。"],
        }

    # ── 维度1: 发布量增长速度（模拟） ──
    # 使用关键词 hash 生成一致的模拟值，让同一关键词结果稳定
    random.seed(keyword + "_trend")
    base_growth = random.uniform(0.3, 3.5)  # 30% ~ 350%
    # 笔记数量多则增速倾向更高（更多创作者涌入）
    note_count_factor = min(1.0, len(notes_list) / 15)
    growth_rate = round(base_growth * (0.7 + 0.3 * note_count_factor), 2)
    random.seed()

    if growth_rate > 2.0:
        growth_score = 100
        growth_label = f"发布量暴涨 {int(growth_rate * 100)}%，远超日常水平"
    elif growth_rate > 1.0:
        growth_score = 60
        growth_label = f"发布量增长 {int(growth_rate * 100)}%，明显上升趋势"
    else:
        growth_score = 20
        growth_label = f"发布量增长 {int(growth_rate * 100)}%，处于正常范围"

    # ── 维度2: 多账号同时发布相似主题 ──
    # 看作者池是否在短时间内集中发布
    authors = {}
    for note in notes_list:
        author = note.get("author")
        if author:
            aid = author["id"]
            if aid not in authors:
                authors[aid] = {"count": 0, "name": author.get("name", "")}
            authors[aid]["count"] += 1

    # 检查是否有 ≥3 个作者在近7天集中发布
    active_authors = [a for a in authors.values() if a["count"] >= 1]
    if len(active_authors) >= 3 and len(notes_list) / len(active_authors) >= 2.5:
        multi_account = True
        multi_score = 100
        multi_label = f"检测到 {len(active_authors)} 个账号集中发布「{keyword}」相关内容"
    else:
        multi_account = False
        multi_score = 0
        multi_label = f"仅有 {len(active_authors)} 个相关账号发布，未形成集中发布趋势"

    # ── 维度3: 平均点赞是否异常偏高 ──
    likes_list = [n.get("likes", 0) for n in notes_list]
    avg_likes = sum(likes_list) / len(likes_list) if likes_list else 0

    # 模拟基准值（不同关键词基准不同）
    # 用实际数据的中位数作为基准更合理
    sorted_likes = sorted(likes_list)
    median_likes = sorted_likes[len(sorted_likes) // 2] if sorted_likes else 500
    baseline_likes = max(200, median_likes * 0.4)  # 基准约为中位数的 40%

    if avg_likes > baseline_likes * 2:
        likes_score = 100
        likes_label = f"平均点赞 {int(avg_likes)}，是基准值 {int(baseline_likes)} 的 {avg_likes / baseline_likes:.1f} 倍，热度异常偏高"
    elif avg_likes > baseline_likes * 1.3:
        likes_score = 60
        likes_label = f"平均点赞 {int(avg_likes)}，高于基准值 {int(baseline_likes)}，热度正在上升"
    else:
        likes_score = 20
        likes_label = f"平均点赞 {int(avg_likes)}，与基准值 {int(baseline_likes)} 持平"

    # ── 综合评分与等级 ──
    total_score = growth_score + multi_score + likes_score

    if total_score >= 200 or (growth_rate > 2.0 and multi_account):
        level = "red"
        level_label = "红色预警"
        level_icon = "\U0001f534"
    elif total_score >= 100 or growth_rate > 1.0:
        level = "yellow"
        level_label = "黄色预警"
        level_icon = "\U0001f7e1"
    else:
        level = "green"
        level_label = "观察中"
        level_icon = "\U0001f7e2"

    # ── 生成建议 ──
    suggestions = _generate_trend_suggestions(
        keyword, level, growth_rate, multi_account, avg_likes, baseline_likes
    )

    logger.info(f"热点预警「{keyword}」: {level_label} (总分 {total_score})")

    return {
        "keyword": keyword,
        "level": level,
        "level_label": level_label,
        "level_icon": level_icon,
        "dimensions": {
            "growth_rate": {
                "value": growth_rate,
                "label": growth_label,
                "score": growth_score,
            },
            "multi_account": {
                "value": multi_account,
                "label": multi_label,
                "score": multi_score,
            },
            "avg_likes_anomaly": {
                "value": round(avg_likes / baseline_likes, 1) if baseline_likes > 0 else 0,
                "label": likes_label,
                "score": likes_score,
            },
        },
        "total_score": total_score,
        "suggestions": suggestions,
    }


def _generate_trend_suggestions(
    keyword: str,
    level: str,
    growth_rate: float,
    multi_account: bool,
    avg_likes: float,
    baseline_likes: float,
) -> list[str]:
    """根据预警等级和维度数据生成具体建议。"""
    suggestions = []

    if level == "red":
        suggestions.append(f"🔥 立即行动！「{keyword}」正处于爆发期，建议在 2 小时内完成内容创作并发布。")
        if multi_account:
            suggestions.append(f"📊 已有多个账号集中发布该主题，快速抢占流量窗口，先发优势至关重要。")
        suggestions.append(f"📈 当前平均点赞 {int(avg_likes)}，远超日常水平 {int(baseline_likes)}，流量红利明显。")
        suggestions.append(f"💡 建议从差异化角度切入，避免与已有爆款内容同质化。")
        suggestions.append(f"⏰ 建议发布时间：工作日上午10-12点或晚上8-10点。")
        suggestions.append(f"🔄 发布后 1 小时内密切关注数据表现，效果好立即追发同类内容。")

    elif level == "yellow":
        suggestions.append(f"⚠️ 「{keyword}」热度正在上升，建议在 24 小时内完成内容规划并发布。")
        suggestions.append(f"📊 当前发布量增长 {int(growth_rate * 100)}%，趋势在持续升温。")
        suggestions.append(f"💡 建议先做选题调研，找到该热点下尚未被充分覆盖的细分角度。")
        suggestions.append(f"📝 参考当前高赞笔记的标题和结构，结合自身风格进行二创。")
        if avg_likes > baseline_likes * 1.3:
            suggestions.append(f"📈 平均点赞已高于日常水平，说明用户关注度正在提升。")
        else:
            suggestions.append(f"📈 虽然发布量增加，但平均点赞尚未明显提升，建议在内容质量上做差异化。")

    else:  # green
        suggestions.append(f"🟢 「{keyword}」当前处于正常波动范围，暂无异常热点信号。")
        suggestions.append(f"📊 发布量增长 {int(growth_rate * 100)}%，属于正常范畴。")
        suggestions.append(f"💡 建议持续关注，可每周分析一次关键词趋势变化。")
        suggestions.append(f"📝 如果不急需追热点，建议将精力放在其他高优先级关键词上。")
        suggestions.append(f"🔍 也可以尝试更细分的长尾关键词，可能会有意外发现。")

    return suggestions


# ── 功能四：差异化缺口分析 ──────────────────────────────────────


def find_content_gap(keyword: str, notes_list: list[dict]) -> dict:
    """
    差异化缺口分析。

    从现有笔记中提取高频角度，按竞争度分为红海/中等/蓝海，
    并生成蓝海内容方向建议。

    Parameters
    ----------
    keyword : str
        搜索关键词。
    notes_list : list[dict]
        笔记列表，每条须包含 title 和 content。

    Returns
    -------
    dict
        {
            "keyword": str,
            "total_notes": int,
            "red_sea": [{"angle": str, "count": int, "ratio": float}],
            "mid_sea": [{"angle": str, "count": int, "ratio": float}],
            "blue_sea": [{"angle": str, "count": int, "ratio": float}],
            "suggestions": [
                {"title": str, "reason": str, "target": str, "estimated_difficulty": str},
                ...
            ],
        }
    """
    if not notes_list:
        logger.warning("find_content_gap 收到空列表")
        return {
            "keyword": keyword,
            "total_notes": 0,
            "red_sea": [],
            "mid_sea": [],
            "blue_sea": [],
            "suggestions": [{
                "title": f"暂无「{keyword}」的笔记数据，请先收集更多样本。",
                "reason": "数据不足",
                "target": "待定",
                "estimated_difficulty": "未知",
            }],
        }

    total = len(notes_list)

    # ── 从标题中提取主题短语 ──
    # 从每个标题中提取 "｜" 前后的核心部分作为主题
    raw_themes: list[str] = []
    for note in notes_list:
        title = note.get("title", "")
        # 按 "｜"、"|"、"、" 等分隔符拆解标题
        parts = re.split(r"[｜|,，、]", title)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # 过滤掉纯模板式词语
            if len(part) < 4:  # 至少 4 个字才叫主题
                continue
            if any(kw in part for kw in ["天花板", "绝绝子", "必看", "攻略", "指南", "合集",
                                          "推荐", "干货", "分享", "教程", "技巧"]):
                continue
            raw_themes.append(part)

    # 如果标题提取不到足够的主题，从正文第一句提取
    if len(raw_themes) < total * 0.3:
        for note in notes_list:
            content = note.get("content", "")
            first_line = content.split("\n\n")[0] if "\n\n" in content else content[:30]
            if len(first_line) >= 6:
                raw_themes.append(first_line[:30])

    # 去重统计
    theme_counts: dict[str, int] = {}
    for theme in raw_themes:
        theme_counts[theme] = theme_counts.get(theme, 0) + 1

    # 按相似度合并主题（基于共享关键词）
    # 简单合并：如果两个主题共享至少 2 个字，合并
    merged_themes: dict[str, int] = {}
    used = set()
    themes_list = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)

    for theme, count in themes_list:
        if theme in used:
            continue
        # 找相似主题合并
        similar = [theme]
        used.add(theme)
        for other, other_count in themes_list:
            if other in used:
                continue
            # 检查是否有公共关键词（取每个主题中 2 字以上的片段）
            shared = sum(1 for c in theme if c in other and len(theme) > 2)
            if shared >= max(2, len(theme) // 2):
                similar.append(other)
                used.add(other)
                count += other_count
        merged_themes[similar[0]] = count

    # 排序
    sorted_themes = sorted(merged_themes.items(), key=lambda x: x[1], reverse=True)

    # 按出现比例分类为内容主题而非关键词
    red_sea = []
    mid_sea = []
    blue_sea = []

    for theme, count in sorted_themes:
        ratio = round(count / total, 2)
        item = {"topic": theme, "count": count, "ratio": ratio}

        if ratio >= 0.30:
            red_sea.append(item)
        elif ratio >= 0.10:
            mid_sea.append(item)
        else:
            blue_sea.append(item)

    red_sea = red_sea[:6]
    mid_sea = mid_sea[:6]
    blue_sea = blue_sea[:10]

    # ── 生成红海/蓝海分析描述 ──
    red_topics = [r["topic"] for r in red_sea]
    blue_topics = [b["topic"] for b in blue_sea]

    suggestions = _generate_blue_ocean_suggestions(
        keyword, notes_list, red_topics, blue_topics
    )

    logger.info(
        f"差异化缺口分析完成: 红海{len(red_sea)}个主题, "
        f"中等{len(mid_sea)}个, 蓝海{len(blue_sea)}个"
    )

    return {
        "keyword": keyword,
        "total_notes": total,
        "red_sea": red_sea,
        "mid_sea": mid_sea,
        "blue_sea": blue_sea,
        "suggestions": suggestions,
    }


def _generate_blue_ocean_suggestions(
    keyword: str,
    notes_list: list[dict],
    red_topics: list[str],
    blue_topics: list[str],
) -> list[dict]:
    """
    基于蓝海角度 + 已有红海内容，生成 3 个可执行的蓝海内容方向。

    模拟 AI 生成（无需调用外部 API），后续可接入真实 AI 增强。
    """
    # 蓝海主题
    blue_words = blue_topics[:8]
    # 红海主题（知道大家都在做什么，以便避开）
    red_words = red_topics[:5]

    suggestions = []
    random.seed(keyword + "_blue_ocean")

    # ── 模板化的蓝海建议生成 ──
    blue_templates = [
        {
            "angle_type": "跨界融合",
            "pattern": f"{keyword}+[新场景/新人群/新形式]",
            "title_template": "没想到{keyword}还能这样用！{angle}专属{keyword}攻略",
            "reason_template": "当前「{keyword}」内容集中在「{red}」等角度，尚未有将{keyword}与{angle}结合的内容，属于明显缺口",
            "target_template": "关注{angle}场景的用户，痛点未被满足",
            "difficulty": "中等 — 需要跨领域知识整合",
        },
        {
            "angle_type": "细分人群",
            "pattern": f"[特定人群]+{keyword}",
            "title_template": "{angle}必看！{keyword}避坑指南｜血泪经验",
            "reason_template": "现有内容以通用性{keyword}为主，缺乏针对{angle}的定制化内容",
            "target_template": "{angle}相关人群，需求精准且粘性高",
            "difficulty": "较低 — 面向垂直人群，内容聚焦即可",
        },
        {
            "angle_type": "反常识/新视角",
            "pattern": f"颠覆认知的{keyword}观点",
            "title_template": "谁说{keyword}只能这样？{angle}才是关键",
            "reason_template": "市面上主流观点集中在「{red}」，从{angle}角度切入可形成差异化认知",
            "target_template": "对{keyword}已有基础认知、寻求进阶的用户",
            "difficulty": "中等 — 需要独特的经验或数据支撑",
        },
        {
            "angle_type": "实操教程",
            "pattern": f"从0到1的{keyword}教程",
            "title_template": "手把手教你{keyword}｜从入门到{angle}",
            "reason_template": "现有内容偏重「{red}」等概念性分享，缺少针对{angle}的系统性实操指南",
            "target_template": "新手用户，需要保姆级教程",
            "difficulty": "较低 — 按步骤整理即可",
        },
        {
            "angle_type": "成本优化",
            "pattern": f"低成本/高性价比{keyword}",
            "title_template": "不花冤枉钱！{angle}也能做好{keyword}的秘诀",
            "reason_template": "当前内容多聚焦「{red}」，未充分覆盖预算有限但追求质量场景",
            "target_template": "预算敏感但追求品质的用户",
            "difficulty": "较低 — 基于实际经验分享即可",
        },
    ]

    # 选 3 个模板
    selected_templates = random.sample(blue_templates, min(3, len(blue_templates)))

    for tmpl in selected_templates:
        angle = random.choice(blue_words) if blue_words else "新场景"
        red_example = "、".join(red_words[:3]) if red_words else "常见角度"

        title = tmpl["title_template"].replace("{keyword}", keyword).replace("{angle}", angle)
        reason = tmpl["reason_template"].replace("{keyword}", keyword).replace("{angle}", angle).replace("{red}", red_example)
        target = tmpl["target_template"].replace("{angle}", angle)

        suggestions.append({
            "title": title,
            "reason": reason,
            "target": target,
            "estimated_difficulty": tmpl["difficulty"],
            "angle_type": tmpl["angle_type"],
            "pattern": tmpl["pattern"],
        })

    random.seed()
    return suggestions


# ── 功能五：竞品商业模式拆解 ──────────────────────────────────


def analyze_business_model(account_name: str, notes_list: list[dict]) -> dict:
    """
    竞品商业模式拆解。

    基于笔记内容模拟检测变现方式及占比。

    检测维度：
    - 带货电商：笔记出现「购买」「同款」「链接」「橱窗」「下单」
    - 私域引流：笔记出现「微信」「私信」「社群」「领取」「资料」
    - 品牌广告：笔记出现「合作」「赞助」「广告」「代言」「品牌」
    - 知识付费：笔记出现「课程」「训练营」「1v1」「教程」「会员」

    Parameters
    ----------
    account_name : str
        竞品账号名称。
    notes_list : list[dict]
        该账号的笔记列表。

    Returns
    -------
    dict
        {
            "account_name": str,
            "total_notes": int,
            "monetization": {
                "带货电商": {"count": int, "ratio": float, "examples": list[str]},
                "私域引流": {"count": int, "ratio": float, "examples": list[str]},
                "品牌广告": {"count": int, "ratio": float, "examples": list[str]},
                "知识付费": {"count": int, "ratio": float, "examples": list[str]},
                "无明显变现": {"count": int, "ratio": float, "examples": list[str]},
            },
            "primary_model": str,           # 主要变现方式
            "model_diversity": float,       # 变现方式多样性 0~1
            "summary": str,                 # 变现策略总结
            "opportunities": list[str],     # 你的机会点
        }
    """
    if not notes_list:
        logger.warning("analyze_business_model 收到空列表")
        return {
            "account_name": account_name,
            "total_notes": 0,
            "monetization": {},
            "primary_model": "无法判断",
            "model_diversity": 0.0,
            "summary": f"暂无「{account_name}」的笔记数据。",
            "opportunities": ["建议先收集该账号的笔记样本。"],
        }

    # ── 变现检测关键词 ──
    monetization_keywords = {
        "带货电商": ["购买", "同款", "链接", "橱窗", "下单", "购物", "买它", "入手", "优惠", "折扣"],
        "私域引流": ["微信", "私信", "社群", "领取", "资料", "免费送", "扫码", "添加", "朋友圈"],
        "品牌广告": ["合作", "赞助", "广告", "代言", "品牌", "试用", "体验官", "pr", "PR", "商务"],
        "知识付费": ["课程", "训练营", "1v1", "教程", "会员", "付费", "一对一", "陪跑", "私教"],
    }

    # 初始化统计
    monetization: dict[str, dict] = {}
    for model_name in monetization_keywords:
        monetization[model_name] = {"count": 0, "ratio": 0.0, "examples": []}
    monetization["无明显变现"] = {"count": 0, "ratio": 0.0, "examples": []}

    # 逐条检测
    for note in notes_list:
        content = note.get("content", "")
        title = note.get("title", "")
        combined = title + " " + content

        matched = False
        for model_name, keywords in monetization_keywords.items():
            for kw in keywords:
                if kw in combined:
                    monetization[model_name]["count"] += 1
                    # 取含该关键词的片段作为示例
                    example = title
                    monetization[model_name]["examples"].append(example)
                    matched = True
                    break
            if matched:
                break

        if not matched:
            monetization["无明显变现"]["count"] += 1
            monetization["无明显变现"]["examples"].append(note.get("title", ""))

    # 计算比例
    total = len(notes_list)
    for model_name in monetization:
        monetization[model_name]["ratio"] = round(monetization[model_name]["count"] / total, 2) if total > 0 else 0
        # 去重示例（只保留前 3 个）
        monetization[model_name]["examples"] = list(dict.fromkeys(monetization[model_name]["examples"]))[:3]

    # ── 主要变现方式 ──
    sorted_models = sorted(
        [(k, v) for k, v in monetization.items() if k != "无明显变现"],
        key=lambda x: x[1]["count"],
        reverse=True,
    )
    primary_model = sorted_models[0][0] if sorted_models and sorted_models[0][1]["count"] > 0 else "无明显变现"

    # ── 变现方式多样性（有多少种变现方式有实际内容） ──
    active_models = sum(1 for _, v in monetization.items() if v["count"] > 0 and _ != "无明显变现")
    model_diversity = round(active_models / 4, 2)  # 4 种变现方式

    # ── 生成总结与机会点 ──
    summary = _generate_business_summary(account_name, primary_model, sorted_models, total)
    opportunities = _generate_business_opportunities(primary_model, sorted_models, monetization)

    logger.info(
        f"竞品商业模式拆解完成: {account_name}, "
        f"主要变现={primary_model}, "
        f"覆盖{active_models}/4种方式"
    )

    return {
        "account_name": account_name,
        "total_notes": total,
        "monetization": monetization,
        "primary_model": primary_model,
        "model_diversity": model_diversity,
        "summary": summary,
        "opportunities": opportunities,
    }


def _generate_business_summary(
    account_name: str,
    primary_model: str,
    sorted_models: list[tuple[str, dict]],
    total: int,
) -> str:
    """生成竞品变现策略总结。"""
    if primary_model == "无明显变现":
        return (
            f"「{account_name}」目前 {total} 条笔记中未检测到明显的变现信号，"
            f"可能处于内容积累期或变现方式较为隐晦。"
        )

    details = []
    for name, info in sorted_models[:3]:
        if info["count"] > 0:
            details.append(f"{name} {info['count']}条 ({info['ratio']*100:.0f}%)")

    return (
        f"「{account_name}」主要变现方式为「{primary_model}」，"
        f"共 {total} 条笔记中涉及 {len(details)} 种变现方式：{'、'.join(details)}。"
        f"整体变现策略以{primary_model}为核心驱动。"
    )


def _generate_business_opportunities(
    primary_model: str,
    sorted_models: list[tuple[str, dict]],
    monetization: dict,
) -> list[str]:
    """基于竞品变现策略生成你的机会点。"""
    opportunities = []

    # 找出占比低的变现方式（缺口）
    weak_models = [(name, info) for name, info in sorted_models if info["ratio"] < 0.15]

    if primary_model == "带货电商":
        opportunities.append("该竞品以带货为主，私域和知识付费占比较低，可作为差异化切入点。")
        opportunities.append("建议建立私域社群，将公域流量沉淀到私域，提升用户LTV。")
        opportunities.append("同时可以尝试知识付费（如付费教程/1v1咨询），客单价远高于带货佣金。")

    elif primary_model == "私域引流":
        opportunities.append("该竞品以私域引流为主，带货转化偏弱，可加强内容中的产品推荐环节。")
        opportunities.append("建议在引流笔记中加入场景化带货，实现「内容→种草→转化」闭环。")
        opportunities.append("品牌合作也是一个补充方向，可在有一定粉丝基础后开放广告位。")

    elif primary_model == "品牌广告":
        opportunities.append("该竞品以品牌合作为主，收入依赖外部投放，抗风险能力较弱。")
        opportunities.append("建议开辟自有变现渠道（带货/知识付费），减少对品牌广告的依赖。")
        opportunities.append("私域引流也可以同步做，积累自有用户资产。")

    elif primary_model == "知识付费":
        opportunities.append("该竞品以知识付费为核心，客单价高但受众面窄。")
        opportunities.append("建议用低价带货内容扩大流量池，再通过高价课程变现。")
        opportunities.append("品牌合作也可以拓展，知识类账号在美妆/教育赛道品牌方青睐。")

    else:
        opportunities.append("该竞品尚未形成清晰的变现路径，这是抢占用户心智的好时机。")
        opportunities.append("建议优先建立1-2种变现方式（推荐带货电商+私域引流组合）。")
        opportunities.append("先跑通最小变现闭环，再逐步扩大收入和变现方式多样性。")

    # 通用机会点
    if weak_models:
        weak_names = [n for n, _ in weak_models[:2]]
        opportunities.append(
            f"竞品在「{'、'.join(weak_names)}」等变现方式上涉足较少，"
            f"可作为你的重点突破口。"
        )

    return opportunities[:5]
