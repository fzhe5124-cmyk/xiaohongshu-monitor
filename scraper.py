"""
scraper.py — 小红书笔记爬虫模块

数据来源（按优先级）：
1. Playwright 真实爬虫 — 使用 Edge 浏览器自动化，数据真实有效
2. Mock 数据 — 当真实爬虫不可用时自动降级
"""

import asyncio
import json
import os
import pickle
import random
import re
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# Playwright 按需导入，未安装时不会阻塞
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)

# ── Mock 示例数据 ──────────────────────────────────────────────

# ── 通用 Mock 数据生成器 ──────────────────────────────────────

MOCK_TITLE_TEMPLATES = [
    "{keyword}天花板｜{keyword}推荐",
    "绝了｜{keyword}这样做效果翻倍",
    "后悔没早知道！{keyword}必备攻略",
    "新手必看｜{keyword}入门指南",
    "{keyword}干货分享｜亲测有效",
    "揭秘｜{keyword}背后的真相",
    "{keyword}合集｜建议收藏",
    "终于有人把{keyword}说清楚了",
    "{keyword}避坑指南｜血泪教训",
    "3个{keyword}技巧，立省时间",
    "{keyword}这样做，后悔没早点看到",
    "小白也能懂的{keyword}攻略",
    "{keyword}天花板｜绝绝子",
    "别再这样{keyword}了！正确做法是",
    "看完这篇{keyword}，我悟了",
    # 额外 15 个模板，支撑 100 条数据
    "{keyword}真实测评｜不吹不黑",
    "{keyword}翻车现场｜这些坑你别踩",
    "2026最新{keyword}趋势分析",
    "{keyword}神器推荐｜相见恨晚",
    "{keyword}入门到精通｜一篇就够了",
    "谁再说{keyword}没用？我第一个不服",
    "{keyword}对比评测｜选对不选贵",
    "零基础{keyword}｜30天逆袭计划",
    "私藏{keyword}清单｜舍不得分享",
    "{keyword}冷知识｜99%的人都不知道",
    "懒人版{keyword}｜躺着也能做好",
    "{keyword}天花板｜这才是正确姿势",
    "{keyword}翻包记｜我的装备大公开",
    "{keyword}血泪史｜花了3万买来的教训",
    "{keyword}日常｜沉浸式体验vlog",
]

MOCK_CONTENT_TEMPLATES = [
    # 模板0: 颠覆认知式开头 + 数据干货 + 互动钩子
    "你是不是也觉得{keyword}很难？其实90%的人都搞错了顺序。\n\n"
    "我花了3个月时间，试了20多种方法，终于总结出这套{keyword}的核心打法。\n\n"
    "先说说最常见的3个误区：第一，盲目跟风；第二，忽视基础；第三，急于求成。"
    "这3个坑我全都踩过，每一个都让我多花了至少2周时间。\n\n"
    "正确做法是：先做好A，再考虑B，最后才是C。"
    "具体来说分三步走——第一步明确目标，第二步搭建框架，第三步迭代优化。\n\n"
    "很多姐妹问我具体怎么操作，其实核心就一句话：方向对了，努力才有意义。\n\n"
    "觉得有用的话双击收藏，下次找不到了～还有什么问题评论区留言，我看到都会回！",

    # 模板1: 提问式开头 + 清单体结构 + 收藏引导
    "姐妹们！为什么你做的{keyword}总是不如别人？答案全在这篇了。\n\n"
    "我整理了5个{keyword}的黄金法则，每一个都是用真金白银换来的经验。\n\n"
    "1️⃣ 第一条：选对方向比努力更重要。不要什么火做什么，要找适合自己的赛道。\n"
    "2️⃣ 第二条：内容要有「用户思维」，站在对方的角度想ta需要什么。\n"
    "3️⃣ 第三条：坚持更新比完美更重要，完成比完美强100倍。\n"
    "4️⃣ 第四条：学会复盘数据，点赞收藏评论背后都有信号。\n"
    "5️⃣ 第五条：建立自己的素材库，好内容不是靠灵感的。\n\n"
    "这5条建议是我做了半年{keyword}最深的感悟，每一条都是血泪教训。\n\n"
    "建议先收藏🌟，以后迷茫了翻出来看看。你们觉得哪一条最难做到？",

    # 模板2: 故事开头 + 情绪共鸣 + 讨论引导
    "还记得我第一次接触{keyword}的时候，完全是一头雾水。\n\n"
    "看别人的教程觉得好简单，自己一上手就各种翻车。"
    "那时候真的很沮丧，觉得自己是不是不适合做这个。\n\n"
    "但坚持下来之后发现，其实所有人都是一样走过来的。"
    "那些看起来轻松做到的人，背后不知道练了多少次。\n\n"
    "我总结了3个对我帮助最大的方法：\n"
    "一是找到对标的榜样，拆解ta的每一步；\n"
    "二是记录自己的每一次尝试，对比找差距；\n"
    "三是加入同好的圈子，有人一起走会轻松很多。\n\n"
    "到现在我也不敢说自己多厉害，但至少走了这么远。\n\n"
    "你们是从什么时候开始接触{keyword}的？评论区聊聊吧👇",

    # 模板3: 数据冲击式开头 + 步骤教程 + 点赞引导
    "做了30天{keyword}，数据翻了5倍，我把方法论全部拆解给你。\n\n"
    "先看数据对比：优化前日均50，优化后日均250+。"
    "没有买量，没有刷单，纯靠内容策略调整。\n\n"
    "核心就3个改动：\n"
    "第一步：重新定位目标人群。以前我觉得越多人看到越好，"
    "后来发现精准用户比数量重要100倍。\n"
    "第二步：优化内容结构。开头3秒决定用户是否留下，"
    "我测试了10种开头方式，最后找到最高效的那种。\n"
    "第三步：建立互动机制。每篇笔记我都会设计一个互动环节，"
    "评论区活跃度直接影响了系统推荐量。\n\n"
    "详细的操作步骤我都整理成表格了，需要的评论区扣1，我私发给你～\n\n"
    "码字不易，觉得有用的话点个赞再走呀❤️",

    # 模板4: 悬念式开头 + 反常识观点 + 结尾转化
    "我发现了{keyword}领域一个惊人的秘密：绝大多数人都做反了。\n\n"
    "你可能会问：大家都在这么做，难道都错了吗？\n"
    "答案是：是的。\n\n"
    "我研究了100个成功案例，发现那些做得好的，"
    "做的事情和我们恰恰相反。\n\n"
    "举个例子：当大家都说要多更新的时候，"
    "他们却在花80%的时间做选题和内容打磨。\n"
    "当大家在追热点的时候，他们在深耕一个垂直方向。\n"
    "当大家在比价格的时候，他们在建立品牌信任。\n\n"
    "这就是所谓的「反直觉策略」——"
    "做别人不做的事，才有别人没有的回报。\n\n"
    "如果你也想系统学习这套方法，关注我，"
    "后续我会出更详细的视频版教程📺",

    # 模板5: 对比式开头 + 踩坑经历 + 收藏/关注引导
    "以前我做{keyword}都是自己瞎琢磨，走了太多弯路。"
    "后来跟着大佬学了一个月，效率直接翻倍。\n\n"
    "对比一下就知道差距在哪了：\n\n"
    "❌ 以前的做法：\n"
    "  - 想到什么做什么，没有规划\n"
    "  - 只看表面技巧，不懂底层逻辑\n"
    "  - 三天打鱼两天晒网\n\n"
    "✅ 现在的做法：\n"
    "  - 每月初制定详细计划\n"
    "  - 先理解为什么做，再想怎么做\n"
    "  - 每天固定时间执行，雷打不动\n\n"
    "变化最大的不是技巧，而是心态和习惯。\n\n"
    "如果你也想做出改变，可以先从一个小目标开始，"
    "比如连续7天每天花30分钟在这件事上。\n\n"
    "收藏这篇笔记，等你坚持了一周回来告诉我感受！",
]

MOCK_NOTES: dict[str, list[dict]] = {}

# "职场穿搭"使用精心设计的 Mock 数据
MOCK_NOTES["职场穿搭"] = [
        {
            "title": "月薪3000穿出高级感｜打工人OOTD",
            "url": "https://www.xiaohongshu.com/explore/1",
            "likes": 3245,
            "cover_desc": "黑白简约通勤穿搭，西装外套搭配直筒裤",
            "content": (
                "入职三年总结的打工人穿搭公式，花最少的钱穿出最贵的质感。"
                "首选黑、白、灰、米色系，搭配西装外套和直筒裤，"
                "鞋子选尖头低跟鞋，显高又专业。"
            ),
        },
        {
            "title": "被HR夸爆的面试穿搭｜应届生必看",
            "url": "https://www.xiaohongshu.com/explore/2",
            "likes": 4872,
            "cover_desc": "米色衬衫搭配深蓝半身裙，温柔知性",
            "content": (
                "面试穿搭不需要太贵，但一定要干净利落。"
                "推荐浅色衬衫+深色下装，避免花哨图案，"
                "配饰简洁大方，第一印象很重要。"
            ),
        },
        {
            "title": "职场小白怎么穿才不像实习生",
            "url": "https://www.xiaohongshu.com/explore/3",
            "likes": 2156,
            "cover_desc": "藏青色西装三件套，干练有气场",
            "content": (
                "刚入职场最怕穿得稚气未脱。"
                "三招摆脱学生气：1. 合身剪裁优于宽松 2. 质感面料优于款式"
                "3. 腰带和腕表是提升精致度的利器。"
            ),
        },
        {
            "title": "周一例会这样穿｜气场全开又不over",
            "url": "https://www.xiaohongshu.com/explore/4",
            "likes": 1589,
            "cover_desc": "雾霾蓝针织衫+白色阔腿裤，知性优雅",
            "content": (
                "周一例会穿搭的关键词是'专业但不刻板'。"
                "雾霾蓝、燕麦色、奶茶色系都是不错的选择，"
                "搭配一条丝巾或简约项链，细节处见品味。"
            ),
        },
        {
            "title": "35岁+职场姐姐的日常穿搭哲学",
            "url": "https://www.xiaohongshu.com/explore/5",
            "likes": 3891,
            "cover_desc": "驼色大衣内搭黑色高领，简约高级",
            "content": (
                "到了一定年龄，穿搭做减法比加法更重要。"
                "注重面料和剪裁，选择经典款而非流行款，"
                "一身不超过三个颜色，配饰选金色系。"
            ),
        },
        {
            "title": "夏季通勤穿搭｜清凉又得体",
            "url": "https://www.xiaohongshu.com/explore/6",
            "likes": 1247,
            "cover_desc": "真丝衬衫+九分西裤，清爽利落",
            "content": (
                "夏天通勤怕热又怕不正式？真丝/天丝衬衫是答案。"
                "搭配九分西裤露出脚踝，配一双乐福鞋，"
                "清凉感和专业度都能兼顾。"
            ),
        },
        {
            "title": "出差开会怎么穿｜商务休闲风穿搭模板",
            "url": "https://www.xiaohongshu.com/explore/7",
            "likes": 2763,
            "cover_desc": "黑色针织Polo搭配卡其色休闲西裤",
            "content": (
                "出差穿搭核心：可正式可休闲，一件单品多场景切换。"
                "推荐blazer+针织衫+西裤的组合，"
                "见客户时穿blazer，回酒店脱掉就是休闲look。"
            ),
        },
        {
            "title": "小个子职场穿搭｜显高10cm的搭配技巧",
            "url": "https://www.xiaohongshu.com/explore/8",
            "likes": 4321,
            "cover_desc": "高腰阔腿裤+短款西装，拉长比例",
            "content": (
                "158cm小个子的职场穿搭秘诀：高腰线+同色系延伸。"
                "短款上衣/塞衣角+高腰下装=黄金比例，"
                "尖头鞋和V领上衣也能在视觉上拉长身形。"
            ),
        },
        {
            "title": "体制内穿搭｜低调又不失质感的通勤look",
            "url": "https://www.xiaohongshu.com/explore/9",
            "likes": 2789,
            "cover_desc": "藏蓝色衬衫搭配卡其色西裤，沉稳高级",
            "content": (
                "体制内穿搭的核心是『得体』而非『出挑』。"
                "藏蓝、深灰、米白是安全色，衬衫选有暗纹的款式，"
                "搭配一块简约腕表和乐福鞋，低调中透露品位。"
            ),
        },
        {
            "title": "互联网大厂上班穿什么｜舒适与体面我都要",
            "url": "https://www.xiaohongshu.com/explore/10",
            "likes": 3456,
            "cover_desc": "宽松针织衫搭配直筒牛仔裤，休闲不失礼貌",
            "content": (
                "大厂穿搭不需要正装，但也不能太随意。"
                "上衣选有质感的针织或棉麻衬衫，下装配直筒裤或A字裙，"
                "一双帆布鞋或板鞋搞定，舒适又有精神。"
            ),
        },
        {
            "title": "职场秋冬穿搭｜叠穿公式直接抄作业",
            "url": "https://www.xiaohongshu.com/explore/11",
            "likes": 4123,
            "cover_desc": "风衣+西装马甲+高领打底三层叠穿",
            "content": (
                "秋冬职场穿搭就靠叠穿了。"
                "万能公式：打底+衬衫/针织+外套，颜色由浅到深，"
                "围巾是点睛之笔，保暖又提升层次感。"
            ),
        },
        {
            "title": "实习生转正穿搭｜第一印象加分的5套look",
            "url": "https://www.xiaohongshu.com/explore/12",
            "likes": 3678,
            "cover_desc": "白色衬衫搭配灰色百褶裙，青春有活力",
            "content": (
                "实习期穿搭的关键是『让人觉得靠谱』。"
                "避免全黑（过于老气），也不要太花哨。"
                "推荐白色/浅蓝衬衫+半身裙/西裤+低跟单鞋，干净清爽最加分。"
            ),
        },
        {
            "title": "微胖女生职场穿搭｜显瘦20斤的搭配秘诀",
            "url": "https://www.xiaohongshu.com/explore/13",
            "likes": 5210,
            "cover_desc": "V领衬衫搭配高腰A字裙，遮肉显高",
            "content": (
                "微胖身材穿职场装最怕显壮。"
                "记住三个关键字：V领、高腰、垂感面料。"
                "V领拉长颈部线条，高腰遮小腹，垂感面料显瘦不贴身。"
            ),
        },
    ]

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
]


def _random_delay(min_sec: float = 1.0, max_sec: float = 3.0) -> None:
    """随机延迟，模拟人类操作间隔。"""
    delay = random.uniform(min_sec, max_sec)
    logger.debug(f"随机延迟 {delay:.1f} 秒")
    time.sleep(delay)


def _build_session() -> requests.Session:
    """创建带有反爬规避头的 requests Session。"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(DEFAULT_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.xiaohongshu.com/",
    })
    return session


def search_notes(
    keyword: str,
    days: int = 7,
    min_likes: int = 100,
    use_mock: bool = True,
    use_realtime: bool = False,
) -> list[dict]:
    """
    搜索小红书笔记。

    Parameters
    ----------
    keyword : str
        搜索关键词，如 "职场穿搭"。
    days : int, default 7
        搜索最近多少天内的笔记。
    min_likes : int, default 100
        最小点赞数过滤。
    use_mock : bool, default True
        是否使用 Mock 数据。
    use_realtime : bool, default False
        是否使用 Playwright 实时爬取真实数据。
        为 True 时优先实时爬取，失败后降级到 Mock。

    Returns
    -------
    list[dict]
        笔记列表，每项包含 title, url, likes, cover_desc, content, author。
    """
    # 实时模式：优先真实数据
    if use_realtime and not use_mock:
        logger.info(f"[实时] 搜索关键词「{keyword}」...")
        try:
            results = search_realtime(keyword, max_notes=100)
            if results:
                logger.info(f"[实时] 成功获取 {len(results)} 条真实笔记")
                # 按最低点赞过滤
                results = [n for n in results if n["likes"] >= min_likes]
                return results
            else:
                logger.warning("[实时] 未获取到数据，降级到 Mock")
        except Exception as e:
            logger.warning(f"[实时] 请求失败 ({e})，降级到 Mock")

    if use_mock or use_realtime is False:
        logger.info(f"[Mock] 搜索关键词「{keyword}」, 最近 {days} 天, 最小点赞 {min_likes}")
        _random_delay(0.5, 1.0)  # 模拟网络延迟

        # 所有关键词统一走动态生成（100条），包括"职场穿搭"
        if keyword in MOCK_NOTES:
            # 清除预设缓存，确保下次重新生成
            del MOCK_NOTES[keyword]

        if keyword not in MOCK_NOTES:
            # 动态生成 Mock 数据
            logger.info(f"[Mock] 关键词「{keyword}」无预设数据，动态生成中...")
            _random_delay(0.5, 1.0)
            results = _generate_mock_notes(keyword)
            # 缓存，避免重复生成
            MOCK_NOTES[keyword] = results

        results = [n for n in results if n["likes"] >= min_likes]
        logger.info(f"[Mock] 找到 {len(results)} 条笔记")
        return results

    # ── 真实爬取逻辑（占位，待后续实现） ──────────────────
    logger.warning("真实爬取模式尚未完整实现，尝试使用 requests 直接请求...")
    session = _build_session()
    url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}"

    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"请求失败: {e}")
        return []

    # TODO: 解析 HTML / 调用小红书内部 API
    return []


def get_note_detail(url: str, use_mock: bool = True) -> Optional[dict]:
    """
    获取单条笔记的详细内容。

    Parameters
    ----------
    url : str
        笔记链接。
    use_mock : bool, default True
        是否使用 Mock 数据。

    Returns
    -------
    dict or None
        笔记详情，如果找不到则返回 None。
    """
    if use_mock:
        logger.info(f"[Mock] 获取笔记详情: {url}")
        _random_delay(0.3, 0.8)
        for notes in MOCK_NOTES.values():
            for note in notes:
                if note["url"] == url:
                    return note
        return None

    logger.warning("真实详情爬取模式尚未实现")
    return None


def _generate_mock_notes(keyword: str, count: int = 100) -> list[dict]:
    """
    为未预设 Mock 数据的关键词动态生成示例笔记。

    Parameters
    ----------
    keyword : str
        搜索关键词。
    count : int, default 6
        生成的笔记数量。

    Returns
    -------
    list[dict]
        笔记列表。
    """
    random.seed(keyword)
    notes = []

    # ── 语言检测 ──
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", keyword))
    is_chinese = chinese_chars / max(len(keyword.strip()), 1) > 0.2

    if is_chinese:
        title_templates = MOCK_TITLE_TEMPLATES
        content_templates = MOCK_CONTENT_TEMPLATES
        cover_prefix = f"{keyword}相关封面图"
        nicknames = [
            "小鹿爱穿搭", "普通打工人小李", "西西的衣橱日记", "老张说职场",
            "艾米丽在巴黎", "小王今天穿什么", "白领穿搭日记", "时尚买手老李",
            "林同学的OOTD", "Rita的日常", "小陈的变美笔记", "七七的衣帽间",
            "大厂女孩日常", "魔都打工妹", "莉莉安的职场美学", "阿杰的搭配经",
            "丸子要努力", "菜菜不踩雷", "二狗的生活笔记", "Una的生活美学",
            "皮皮的小红书", "MOMO穿搭记", "小野的成长日记", "番茄不是西红柿",
            "周末不上班", "茉莉的日常分享", "阿星随便写写", "肥肥的精致生活",
            "小云朵在大厂", "阿拉蕾的备忘录", "大白鹅的日常",
            "一颗柠檬精", "葡萄成熟时", "小透明的逆袭",
            "加菲猫的衣橱", "咸鱼翻身记", "小太阳的自习室",
            "王子的穿搭笔记", "CC的成长日记",
        ]
    else:
        # 英文模板
        EN_TITLE_TEMPLATES = [
            "Ultimate Guide to {keyword}",
            "10 {keyword} Tips You Need to Know",
            "Stop Doing {keyword} Wrong!",
            "Best {keyword} Hacks for Beginners",
            "I Tried {keyword} for 30 Days",
            "{keyword} Review: Honest Thoughts",
            "How to Master {keyword} in 2026",
            "{keyword} vs {keyword}: Which is Better?",
            "Why Everyone is Talking About {keyword}",
            "Complete {keyword} Tutorial for Beginners",
            "5 {keyword} Mistakes That Cost Me Money",
            "My {keyword} Journey: From Zero to Hero",
            "What Nobody Tells You About {keyword}",
            "{keyword} Transformations That Will Shock You",
            "The Truth About {keyword} Nobody Talks About",
            "I Wish I Knew This About {keyword} Sooner",
            "Game-Changing {keyword} Secrets Revealed",
            "Simple {keyword} Routine That Actually Works",
            "{keyword} for Busy People: Shortcut Edition",
            "Everything You Need to Know About {keyword}",
            "Beginner's Luck? No, {keyword} Strategy Works",
            "Behind the Scenes of My {keyword} Setup",
            "This {keyword} Hack Saved Me Hours",
            "Honest {keyword} Review: Worth It or Not?",
            "Breaking Down {keyword} Step by Step",
            "Is {keyword} Overrated? My Experience",
            "2026 {keyword} Trends You Can't Ignore",
            "My Favorite {keyword} Tools & Resources",
            "Common {keyword} Myths Debunked",
            "How I Made {keyword} Work for Me",
        ]
        EN_CONTENT_TEMPLATES = [
            "I've been exploring {keyword} for a while now, and here's what I've found.\n\n"
            "Most people get it wrong from the start. They focus on the wrong things and wonder why results don't come.\n\n"
            "Let me break down the 3 biggest mistakes I see:\n"
            "1. Jumping in without a clear plan\n"
            "2. Following trends instead of understanding the fundamentals\n"
            "3. Giving up too early\n\n"
            "The right approach is simpler than you think. Start with the basics, build a solid foundation, then iterate.\n\n"
            "Hope this helps! Drop a comment if you have questions 👇",

            "Here's a complete guide to getting started with {keyword}.\n\n"
            "I spent months researching and testing different approaches. Here's what actually works:\n\n"
            "Step 1: Define your goals clearly\n"
            "Step 2: Build your toolkit\n"
            "Step 3: Start with a small, manageable routine\n"
            "Step 4: Track your progress and adjust\n"
            "Step 5: Scale up gradually\n\n"
            "Each step builds on the previous one. Skip any and you'll struggle.\n\n"
            "Save this for later and share with someone who needs it! 🌟",

            "You won't believe what happened when I tried {keyword}.\n\n"
            "Honestly, I was skeptical at first. Everyone claims their method is the best. But I decided to test it myself.\n\n"
            "After 30 days of consistent effort, here's what changed:\n"
            "→ My workflow improved by 50%\n"
            "→ I saved roughly 10 hours per week\n"
            "→ The results exceeded my expectations\n\n"
            "The key insight? Consistency beats intensity every single time.\n\n"
            "Have you tried {keyword}? Share your experience in the comments!",
        ]
        title_templates = EN_TITLE_TEMPLATES
        content_templates = EN_CONTENT_TEMPLATES
        cover_prefix = f"{keyword} cover"
        nicknames = [
            "Sarah in NY", "TechTom", "Alice W.", "Daily Vibe",
            "Mike R.", "Luna M.", "Chris P.", "Emma J.",
            "Jay C.", "Sophia L.", "Pete G.", "Olivia K.",
            "Nina S.", "Leo Z.", "Mia B.", "Alex D.",
            "Riley T.", "Jordan W.", "Casey N.", "Sam H.",
            "Taylor R.", "Morgan F.", "Avery L.", "Quinn C.",
            "Reese P.", "Skyler G.", "Blake M.", "Cameron J.",
            "Drew S.", "Phoebe X.",
        ]

    random.shuffle(nicknames)
    selected_titles = [random.choice(title_templates) for _ in range(count)]

    REAL_NICKNAMES = nicknames
    author_pool = []
    for a in range(30):  # 30 个作者覆盖 100 条笔记
        aid = f"user_{hash(keyword + 'author' + str(a)) % 100000}"
        author_pool.append({
            "id": aid,
            "name": REAL_NICKNAMES[a % len(REAL_NICKNAMES)],
            "followers": random.choice([300, 800, 1200, 3000, 6000, 15000]),
            "reg_days": random.choice([45, 60, 90, 150, 200, 400, 600]),
        })

    for i, template in enumerate(selected_titles):
        title = template.replace("{keyword}", keyword)
        likes = random.randint(100, 5000)
        cover_desc = f"{cover_prefix} {i+1}"
        content_template = random.choice(content_templates)
        content = content_template.replace("{keyword}", keyword)

        # 模拟变现信号：按笔记索引分配不同的变现关键词
        monetization_snippets = [
            "",  # 无明显变现
            "购买同款的话可以私信我发链接～",  # 带货电商
            "",  # 无明显变现
            "需要完整资料包的姐妹私信我领取！",  # 私域引流
            "",  # 无明显变现
            "这是XX品牌的合作体验，感谢赞助～",  # 品牌广告
            "",  # 无明显变现
            "1v1课程持续招生中，需要的私我",  # 知识付费
            "",  # 无明显变现
            "同款链接放在橱窗了，自取～",  # 带货电商
            "",  # 无明显变现
            "想进社群一起交流的加我微信～",  # 私域引流
            "限时课程优惠，私信我了解详情",  # 知识付费
        ]
        snippet = monetization_snippets[i % len(monetization_snippets)]
        if snippet:
            content += "\n\n" + snippet

        author = author_pool[i % len(author_pool)]
        notes.append({
            "title": title,
            "url": f"https://www.xiaohongshu.com/explore/mock_{hash(keyword) % 100000}_{i}",
            "likes": likes,
            "cover_desc": cover_desc,
            "content": content,
            "author": dict(author),  # 浅拷贝，避免引用问题
        })

    random.seed()
    return notes


# ═══════════════════════════════════════════════════════════════
# Playwright 真实爬虫（数据来源：小红书搜索页）
# ═══════════════════════════════════════════════════════════════

# Cookie 持久化路径
COOKIE_DIR = Path(__file__).parent / ".cookies"
COOKIE_FILE = COOKIE_DIR / "xiaohongshu.pkl"

# 小红书搜索 API（从网页请求中提取的真实接口）
XHS_SEARCH_URL = "https://www.xiaohongshu.com/search_result"
XHS_API_SEARCH = "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"

# 用户数据目录（用于持久化登录态）
USER_DATA_DIR = str(Path(__file__).parent / ".browser_data")


class XiaohongshuScraper:
    """
    小红书 Playwright 爬虫。

    用法：
        scraper = XiaohongshuScraper()
        notes = scraper.search("职场穿搭")
        scraper.close()

    首次运行会自动打开浏览器窗口，请扫码登录。
    登录成功后 cookie 会保存，后续自动复用。
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self._playwright = None
        self._cookie_loaded = False

    def _ensure_browser(self):
        """确保浏览器已启动。"""
        if self.browser:
            return

        if not HAS_PLAYWRIGHT:
            raise RuntimeError(
                "Playwright 未安装。请执行: pip install playwright && python -m playwright install chromium"
            )

        self._playwright = sync_playwright().start()

        # 使用系统 Edge 浏览器（通过 channel 方式）
        cookie_exists = COOKIE_FILE.exists()

        launch_kwargs = {
            "user_data_dir": USER_DATA_DIR,
            "channel": "msedge",
            "headless": self.headless,
            "viewport": {"width": 1280, "height": 800},
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
            ),
        }

        if cookie_exists:
            self.context = self._playwright.chromium.launch_persistent_context(**launch_kwargs)
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            # 加载 cookie
            try:
                with open(COOKIE_FILE, "rb") as f:
                    cookies = pickle.load(f)
                self.context.add_cookies(cookies)
                self._cookie_loaded = True
                logger.info(f"已加载持久化 cookie，共 {len(cookies)} 条")
            except Exception as e:
                logger.warning(f"加载 cookie 失败: {e}，需要重新登录")
                self._cookie_loaded = False
        else:
            launch_kwargs["headless"] = False  # 首次必须有界面
            self.context = self._playwright.chromium.launch_persistent_context(**launch_kwargs)
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            self._prompt_login()

        self.page.set_default_timeout(30000)

    def _prompt_login(self):
        """打开小红书首页，引导用户登录。"""
        print("\n" + "=" * 60)
        print("  需要登录小红书账号")
        print("=" * 60)
        print("  浏览器窗口已打开，请:")
        print("  1. 点击右上角「登录」")
        print("  2. 使用微信/手机号扫码登录")
        print("  3. 登录完成后，在此终端按 Enter 继续")
        print("=" * 60 + "\n")

        self.page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
        input("按 Enter 键继续...")

        # 保存 cookie
        self._save_cookies()

    def _save_cookies(self):
        """保存当前 cookie 到文件。"""
        try:
            COOKIE_DIR.mkdir(parents=True, exist_ok=True)
            cookies = self.context.cookies()
            with open(COOKIE_FILE, "wb") as f:
                pickle.dump(cookies, f)
            self._cookie_loaded = True
            logger.info(f"已保存 cookie，共 {len(cookies)} 条")
        except Exception as e:
            logger.error(f"保存 cookie 失败: {e}")

    def _is_logged_in(self) -> bool:
        """检查当前是否已登录。"""
        try:
            # 通过检查 cookie 中是否有登录态标识
            cookies = self.context.cookies()
            for c in cookies:
                if "session" in c.get("name", "").lower() or "token" in c.get("name", "").lower():
                    return True
            return False
        except Exception:
            return False

    def search(self, keyword: str, max_notes: int = 100) -> list[dict]:
        """
        搜索小红书笔记（真实数据）。

        Parameters
        ----------
        keyword : str
            搜索关键词。
        max_notes : int, default 100
            最多获取的笔记数。

        Returns
        -------
        list[dict]
            笔记列表，格式与 Mock 版本一致。
        """
        self._ensure_browser()

        notes = []

        try:
            # 打开搜索页
            search_url = f"{XHS_SEARCH_URL}?keyword={keyword}"
            logger.info(f"正在搜索: {keyword}")
            self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

            # 等待搜索结果加载
            time.sleep(3)

            # 尝试多种选择器找到笔记卡片
            note_elements = []
            selectors = [
                "section.note-item",
                "div.note-item",
                ".feeds-page .note-item",
                "[class*='note'] a[href*='explore']",
                "a[href*='/explore/']",
            ]

            for selector in selectors:
                note_elements = self.page.query_selector_all(selector)
                if note_elements:
                    logger.info(f"选择器 '{selector}' 找到 {len(note_elements)} 个元素")
                    break

            if not note_elements:
                # 尝试从页面 HTML 中提取
                logger.warning("未找到笔记卡片，尝试从页面数据中提取...")
                notes = self._extract_from_page(keyword)
                if notes:
                    return notes
                # 尝试调用 API
                notes = self._search_via_api(keyword, max_notes)
                if notes:
                    return notes
                # 全部失败
                logger.error("无法从页面提取笔记数据")
                return []

            # 从卡片中提取信息
            for i, el in enumerate(note_elements[:max_notes]):
                try:
                    note = self._extract_note_from_element(el, keyword)
                    if note:
                        notes.append(note)
                except Exception as e:
                    logger.debug(f"提取第 {i} 条笔记失败: {e}")
                    continue

            if notes:
                logger.info(f"成功获取 {len(notes)} 条真实笔记")
                return notes

            # 卡片解析失败，尝试 API
            notes = self._search_via_api(keyword, max_notes)
            if notes:
                return notes

        except Exception as e:
            logger.error(f"Playwright 搜索失败: {e}")
            # 尝试 API 作为备选
            try:
                notes = self._search_via_api(keyword, max_notes)
                if notes:
                    return notes
            except Exception:
                pass

        return notes

    def _extract_from_page(self, keyword: str) -> list[dict]:
        """从页面 HTML 中提取笔记数据（window.__INITIAL_STATE__）。"""
        try:
            # 尝试从 __NEXT_DATA__ 或 __INITIAL_STATE__ 提取
            script = self.page.query_selector("script#__NEXT_DATA__")
            if script:
                data = json.loads(script.inner_text())
                if "props" in data:
                    return self._parse_next_data(data, keyword)

            # 尝试从 window.__INITIAL_STATE__ 提取
            state = self.page.evaluate("() => window.__INITIAL_STATE__")
            if state:
                return self._parse_initial_state(state, keyword)

        except Exception as e:
            logger.debug(f"从页面数据提取失败: {e}")
        return []

    def _parse_next_data(self, data: dict, keyword: str) -> list[dict]:
        """解析 __NEXT_DATA__ 格式。"""
        notes = []
        try:
            notes_data = data.get("props", {}).get("pageProps", {}).get("notes", [])
            for item in notes_data:
                note = self._format_note(item, keyword)
                if note:
                    notes.append(note)
        except Exception:
            pass
        return notes

    def _parse_initial_state(self, state: dict, keyword: str) -> list[dict]:
        """解析 __INITIAL_STATE__ 格式。"""
        notes = []
        try:
            note_map = state.get("note", {}).get("noteDetailMap", {})
            for nid, item in note_map.items():
                note = self._format_note(item.get("note", item), keyword)
                if note:
                    notes.append(note)
        except Exception:
            pass
        return notes

    def _search_via_api(self, keyword: str, max_notes: int = 20) -> list[dict]:
        """通过小红书内部 API 搜索（从页面提取 cookie/token 后调用）。"""
        try:
            # 从当前页面获取 cookie 和 token
            cookies = self.context.cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

            # 获取 X-S / X-T 签名（从页面提取）
            xt = str(int(time.time() * 1000))
            xs = self._generate_xs(xt)

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
                ),
                "Cookie": cookie_str,
                "Content-Type": "application/json;charset=UTF-8",
                "Origin": "https://www.xiaohongshu.com",
                "Referer": f"https://www.xiaohongshu.com/search_result?keyword={keyword}",
                "X-S": xs,
                "X-T": xt,
            }

            payload = {
                "keyword": keyword,
                "page": 1,
                "page_size": min(max_notes, 100),
                "sort": "general",
                "note_type": 0,
            }

            resp = requests.post(
                XHS_API_SEARCH,
                headers=headers,
                json=payload,
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", {}).get("items", [])
                notes = []
                for item in items:
                    note_data = item.get("note_card", item)
                    note = self._format_note(note_data, keyword)
                    if note:
                        notes.append(note)
                return notes

        except Exception as e:
            logger.debug(f"API 搜索失败: {e}")
        return []

    def _generate_xs(self, xt: str) -> str:
        """生成 X-S 签名（简化版本，实际签名算法更复杂）。"""
        # 这是一个简化实现，真实签名需要逆向小红书前端 JS
        # 这里使用页面中已有的签名
        try:
            xs = self.page.evaluate(f"""
                () => {{
                    try {{
                        // 尝试调用页面中的签名函数
                        if (window._sign) {{
                            return window._sign({xt});
                        }}
                    }} catch(e) {{}}
                    return "";
                }}
            """)
            if xs:
                return xs
        except Exception:
            pass
        # 如果拿不到签名，返回空字符串
        return ""

    def _extract_note_from_element(self, el, keyword: str) -> Optional[dict]:
        """从 DOM 元素中提取笔记信息。"""
        try:
            # 标题
            title_el = el.query_selector("title, .title, h3, [class*='title']")
            title = title_el.inner_text().strip() if title_el else ""

            # 链接
            link_el = el.query_selector("a[href]")
            href = link_el.get_attribute("href") if link_el else ""
            url = f"https://www.xiaohongshu.com{href}" if href.startswith("/") else href

            # 点赞数
            likes_el = el.query_selector("[class*='like'], [class*='likes'], .like-wrapper")
            likes_text = likes_el.inner_text().strip() if likes_el else "0"
            likes = self._parse_count(likes_text)

            # 作者
            author_el = el.query_selector("[class*='author'], [class*='name'], .username")
            author_name = author_el.inner_text().strip() if author_el else "未知用户"

            # 封面描述
            img_el = el.query_selector("img[alt]")
            cover_desc = img_el.get_attribute("alt") or "" if img_el else ""

            # 提取作者 ID
            author_link = el.query_selector("a[href*='user']")
            author_id = ""
            if author_link:
                author_href = author_link.get_attribute("href") or ""
                author_id = author_href.split("/")[-1]

            return {
                "title": title or keyword + "相关笔记",
                "url": url or f"https://www.xiaohongshu.com/explore",
                "likes": likes,
                "cover_desc": cover_desc,
                "content": title,  # 正文需要点进详情才拿到
                "source": "realtime",
                "author": {
                    "id": author_id or f"user_{hash(title) % 100000}",
                    "name": author_name,
                    "followers": 0,  # 列表页不显示粉丝数
                    "reg_days": 0,
                },
            }
        except Exception as e:
            logger.debug(f"提取笔记元素失败: {e}")
            return None

    def _format_note(self, item: dict, keyword: str) -> Optional[dict]:
        """将 API/页面数据格式化为统一结构。"""
        try:
            title = item.get("title", "") or item.get("display_title", "")
            if isinstance(title, dict):
                title = title.get("text", "")

            note_id = item.get("id") or item.get("note_id", "")
            url = f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else ""

            likes = item.get("likes") or item.get("liked_count", 0)
            if isinstance(likes, str):
                likes = self._parse_count(likes)

            author_data = item.get("user", {}) or item.get("author", {})
            if isinstance(author_data, dict):
                author_name = author_data.get("nickname", "") or author_data.get("name", "未知用户")
                author_id = author_data.get("user_id", "") or author_data.get("id", "")
                followers = author_data.get("fans_count", 0) or author_data.get("followers", 0)
            else:
                author_name = "未知用户"
                author_id = ""
                followers = 0

            # 封面 / 描述
            cover = item.get("cover", {}) or {}
            cover_desc = cover.get("description", "") if isinstance(cover, dict) else ""

            # 正文（列表页不一定有）
            content = item.get("desc", "") or item.get("content", "") or title

            return {
                "title": title,
                "url": url,
                "likes": int(likes) if likes else 0,
                "cover_desc": cover_desc,
                "content": content,
                "source": "realtime",
                "author": {
                    "id": author_id,
                    "name": author_name,
                    "followers": int(followers) if followers else 0,
                    "reg_days": 0,
                },
            }
        except Exception as e:
            logger.debug(f"格式化笔记数据失败: {e}")
            return None

    def _parse_count(self, text: str) -> int:
        """解析点赞数字（支持 '1.2万' 格式）。"""
        text = text.strip()
        if "万" in text:
            try:
                return int(float(text.replace("万", "")) * 10000)
            except ValueError:
                return 0
        try:
            return int(re.sub(r"[^\d]", "", text))
        except ValueError:
            return 0

    def close(self):
        """关闭浏览器。"""
        try:
            self._save_cookies()
        except Exception:
            pass
        try:
            if self.context:
                self.context.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self.browser = None
        self.context = None
        self.page = None
        self._playwright = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ── 全局单例，供 search_notes 使用 ──
_scraper_instance: Optional[XiaohongshuScraper] = None


def _get_scraper() -> XiaohongshuScraper:
    """获取或创建爬虫实例。"""
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = XiaohongshuScraper(headless=True)
    return _scraper_instance


def search_realtime(keyword: str, max_notes: int = 100) -> list[dict]:
    """
    使用 Playwright 搜索真实小红书数据。

    首次使用需要登录，后续自动复用 cookie。

    Parameters
    ----------
    keyword : str
        搜索关键词。
    max_notes : int, default 20
        最多获取多少条笔记。

    Returns
    -------
    list[dict]
        笔记列表，失败时返回空列表。
    """
    if not HAS_PLAYWRIGHT:
        logger.error("Playwright 未安装，无法使用实时搜索。请执行: pip install playwright && python -m playwright install chromium")
        return []

    try:
        scraper = _get_scraper()
        return scraper.search(keyword, max_notes=max_notes)
    except Exception as e:
        logger.error(f"实时搜索失败: {e}")
        return []
