"""登录小红书 + 测试真实数据"""
import sys, os, time, pickle
sys.stdout.reconfigure(encoding='utf-8')

from scraper import COOKIE_DIR, COOKIE_FILE, USER_DATA_DIR
from playwright.sync_api import sync_playwright

print("正在启动 Edge 浏览器...")

play = sync_playwright().start()

context = play.chromium.launch_persistent_context(
    user_data_dir=USER_DATA_DIR,
    channel="msedge",
    headless=False,
    viewport={"width": 1280, "height": 800},
    locale="zh-CN",
)

page = context.pages[0] if context.pages else context.new_page()
page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")

print()
print("=" * 60)
print("  1. 在弹出的浏览器中登录小红书")
print("  2. 登录完成后关闭浏览器窗口")
print("  3. 脚本会自动继续")
print("=" * 60)
print()
print("等待浏览器关闭...")

while True:
    try:
        if page.is_closed():
            break
        time.sleep(1)
    except:
        break

try:
    cookies = context.cookies()
    COOKIE_DIR.mkdir(parents=True, exist_ok=True)
    with open(COOKIE_FILE, "wb") as f:
        pickle.dump(cookies, f)
    print(f"已保存 {len(cookies)} 条 cookie")
except Exception as e:
    print(f"保存 cookie 失败: {e}")

context.close()
play.stop()

print("\n测试搜索真实数据...")

try:
    from scraper import XiaohongshuScraper
    scraper = XiaohongshuScraper(headless=True)
    notes = scraper.search("职场穿搭")
    scraper.close()

    if notes:
        print(f"\n成功获取 {len(notes)} 条真实数据！\n")
        for n in notes[:5]:
            author = n.get("author", {})
            print(f"[{n['likes']}赞] {n['title']}")
            print(f"  作者: {author.get('name', '未知')}")
            print()
    else:
        print("未获取到数据，Cookie 可能无效")
except Exception as e:
    print(f"搜索失败: {e}")
