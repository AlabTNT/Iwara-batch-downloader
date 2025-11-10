import json, re, time, os, requests
from urllib.parse import urlsplit, unquote, unquote_plus
from pathlib import Path
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

SAVE_DIR = "videos"
waitafterload = 10
REQUEST_TIMEOUT = 30

os.makedirs(SAVE_DIR, exist_ok=True)

def safe_filename(name: str, max_len=200) -> str:
    if not name:
        name = "untitled"
    name = unquote(name)
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", name).strip()
    if len(name) > max_len:
        name = name[:max_len].rstrip()
    return name or "untitled"

def download_stream_to_file(url: str, path: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT, headers=headers) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(path, "wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc=os.path.basename(path)) as bar:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))

def make_driver_headless():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--mute-audio")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_argument("--ignore-certificate-errors")
    service = Service(log_path="NUL")

    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver


def extract_videos_and_title(logs):
    video_urls = set()
    title = "untitled"
    title_urls= set()

    for entry in logs:
        try:
            message = json.loads(entry["message"])["message"]
        except Exception:
            continue
        method = message.get("method")
        params = message.get("params", {})
        if method == "Network.responseReceived":
            response = params.get("response", {})
            url = response.get("url", "")

            if "_Source.mp4" in url or "_540.mp4" in url:
                video_urls.add(unquote(url))    
                
            if url:
                if re.search(r"\.mp4(\?|$)", url, re.I):
                    title_urls.add(url)

    # 尝试从符合条件的视频 URL 提取 title
    for u in title_urls:
        if "files.iwara.tv" in u:
            t = u.split("download=")[-1]
            try:
                decoded = unquote_plus(t or "")
                decoded = decoded.split("?", 1)[0].split("#", 1)[0].strip()
                decoded = re.sub(r'\.(mp4|m3u8|webm|mov|avi|mkv)$', '', decoded, flags=re.I)
                decoded = re.sub(r'\s+', ' ', decoded)
                title = safe_filename(decoded)
            except Exception:
                title = safe_filename(unquote_plus(t)) if t else "untitled"
            break
    
    backtitle = title
    try:
        title = title.replace("Iwara - ","")
        title = re.sub(r'\[[A-Za-z0-9]+\]', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        title = safe_filename(title)
    except:
        title=backtitle

    return video_urls, title

def crawl_one(url: str, driver=None):
    print(f"\n🚩 处理页面: {url}")
    df=driver is None
    try:
        if not driver:
            driver = make_driver_headless()
        driver.get(url)
        time.sleep(waitafterload)
        logs = driver.get_log("performance")
        video_urls, title = extract_videos_and_title(logs)
        print("页面标题：", title or "(无标题)")

        if not video_urls:
            print("⚠️ 未找到符合 iwara.tv 的媒体资源。尝试播放录制抓取...")
            wait = WebDriverWait(driver, 10)
            play_button = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "button.vjs-play-control.vjs-control.vjs-button"
            )))
            play_button.click()
            time.sleep(waitafterload)
            logs = driver.get_log("performance")
            video_urls,_= extract_videos_and_title(logs)
        
        if not video_urls:
            print("❌ 未找到任何视频资源，跳过此链接。")
            return False

        chosen = None
        for v in video_urls:
            if re.search(r"\.mp4(\?|$)", v, re.I):
                chosen = v
                break
        if not chosen:
            chosen = next(iter(video_urls))

        print("🎯 选中下载：", chosen)
        path = urlsplit(chosen).path
        ext = os.path.splitext(path)[1] or ".mp4"

        derived_name = title
        if derived_name:
            _t=os.path.splitext(derived_name)
            if not _t[1] or _t[1].lower() not in [".mp4", ".m3u8", ".webm", ".mov", ".avi", ".mkv"]:
                filename = derived_name + ext
            else:
                filename = derived_name
        else:
            filename = safe_filename(title) + ext

        out_path = os.path.join(SAVE_DIR, filename)
        if os.path.exists(out_path):
            print("😮 文件已存在，跳过：", out_path)
            return True
        
        download_stream_to_file(chosen, out_path)
        print("✅ 下载完成：", out_path)
        return True

    except Exception as e:
        print("⚠️ 处理出错：", e)
    
    if df and driver:
        driver.quit()


def save_main(url):
    with open("iwara_urls.json", "r", encoding="utf-8") as f:
        urls = json.load(f)
    with open("iwara_urls.json", "w", encoding="utf-8") as f:
        json.dump([i for i in urls if i != url], f, ensure_ascii=False, indent=4)

def readin(readbook=True):
    if os.path.exists("iwara_urls.json"):
        with open("iwara_urls.json", "r", encoding="utf-8") as f:
            bookmarks = json.load(f)
    else:
        bookmarks = []

    if readbook is True:
        for p in Path('.').glob('*.html'):
            print("ℹ️找到可能的书签文件：",p.name)
            with open(p.name, "r", encoding="utf-8") as f:
                html_content = f.read().splitlines()
                for i in html_content:
                    m = re.search(r'<DT><A HREF="([^"]+)"\s+ADD_DATE=', i)
                    if not m:
                        continue
                    url = m.group(1)
                    if "iwara.tv/video" not in url:
                        continue
                    bookmarks.append(url)
                    print("  ➤ 添加链接：", url)
            os.remove(p.name)
            print("ℹ️已处理并删除书签文件：",p.name)
    bookmarks = list(set(bookmarks))

    with open("iwara_urls.json", "w", encoding="utf-8") as f:
        json.dump(bookmarks, f, ensure_ascii=False, indent=4)
    print(f"ℹ️ 已加载 iwara_urls.json，包含 {len(bookmarks)} 个链接。")
    return bookmarks

def get_txt():
    urls=[]
    for p in Path('.').glob('*.txt'):
        print("ℹ️找到可能的文本文件：",p.name)
        with open(p.name, "r", encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if "iwara.tv/video" in url:
                    urls.append(url)
                    print("  ➤ 添加链接：", url)
        os.remove(p.name)
        print("ℹ️已处理并删除文本文件：",p.name)
    return urls

def main(urls=[],driver=None):
    print("=== Iwara 视频下载器 by AlabTNT ===")
    failed=[]
    print(f"🌟 开始批量下载，任务共有 {len(urls)} 个链接。预计需要时长：{len(urls)*1.5:.1f} 分钟")
    for url in urls:
        try:
            success = crawl_one(url, driver=driver)
            if not success:
                failed.append(url)
            else:
                save_main(url)
        except Exception as e:
            print("整体处理异常：", e)
    
    print("\n=== 处理完成 ===")
    print("✅ 成功下载的视频：", len(urls) - len(failed),"/", len(urls))
    if failed:
        print("🚨 所有尝试失败的视频链接：\n-","\n- ".join(failed))
    print("ℹ️ 视频已存放在：", os.path.abspath(SAVE_DIR))
    print("\n\n任务完成，退出。")

    if driver:
        driver.quit()
        
def routing():
    print("=== Iwara 视频下载器 by AlabTNT ===")
    print("   1. 只批量下载 .json 中的链接")
    print("   2. 从 .html 书签文件导入并下载 .json 中的链接")
    print("   3. 从 .txt 文件导入并下载 .json 中的链接")
    print("   4(default). 同时从 .html 书签文件和 .txt 文件导入并下载 .json 中的链接")
    print("   5. 手动输入单个链接下载")
    print("   e/q/6. 退出程序")
    driver=make_driver_headless()

    while True:
        print("ℹ️ 请选择运行模式(1/2/3/4/5/6/e/q)：", end="")
        choice = input().strip()
        if choice == "1":
            print("✨ 模式：1（仅.json）")
            urls = readin(False)
            main(urls, driver=driver)
        elif choice == "2":
            print("📝 模式：2（.html）")
            urls = readin(True)
            main(urls, driver=driver)
        elif choice == "3":
            print("🕶️ 模式：3（.txt）")
            urls = get_txt()
            main(urls, driver=driver)
        elif choice == "4":
            print("🎯 模式：4（.txt+.html）")
            urls = readin(True)
            urls += get_txt()
            urls = list(set(urls))
            main(urls, driver=driver)
        elif choice == "5":
            print("😀 模式：5（手动）")
            while True:
                print("ℹ️ 请输入 iwara.tv 视频链接，输入 exit 退出：", end="")
                url = input().strip()
                if "iwara.tv" in url:
                    crawl_one(url, driver=driver)
                elif url=="exit":
                    print("👋 退出手动输入模式。")
                    break
                else:
                    print("⚠️ 输入的链接无效。")
        elif choice in ["e", "q", "6"]:
            print("👋 退出程序。")
            if driver:
                driver.quit()
            return
        else:
            print("❌ 无效选择，请重试。")
            
if __name__ == "__main__":
    routing()
