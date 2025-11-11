from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
import json
from datetime import datetime
import os
import re
import csv

import google.generativeai as genai
import requests
from requests.exceptions import RequestException

# Konfigurasi Gemini AI (opsional)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
USE_AI_SELECTOR = GEMINI_API_KEY != ""

if USE_AI_SELECTOR:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('models/gemini-2.5-flash-preview-05-20')

def analyze_selectors_with_ai(html_content):
    """Menggunakan Gemini AI untuk menganalisis HTML dan menemukan selector yang tepat"""
    if not USE_AI_SELECTOR:
        return None
    
    prompt = f"""
Analisis HTML YouTube berikut dan berikan selector CSS yang tepat untuk mengekstrak komentar.
Berikan response dalam format JSON dengan struktur:
{{
    "comment_thread": "selector untuk thread komentar",
    "author": "selector untuk nama author",
    "comment_text": "selector untuk text komentar",
    "published_time": "selector untuk waktu publish",
    "likes": "selector untuk jumlah likes",
    "replies": "selector untuk jumlah replies",
    "video_title": "selector untuk judul video",
    "channel_name": "selector untuk nama channel"
}}

HTML (first 5000 chars):
{html_content[:5000]}
"""
    
    try:
        response = model.generate_content(prompt)
        json_text = response.text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]
        
        selectors = json.loads(json_text.strip())
        print("🤖 AI berhasil menganalisis selector!")
        return selectors
    except Exception as e:
        print(f"⚠️  AI gagal menganalisis: {e}")
        return None


def extract_text(item):
    """Helper untuk mengambil teks dari struktur YouTube (runs/simpleText)"""
    if not item:
        return ""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        if "simpleText" in item:
            return item["simpleText"]
        if "runs" in item:
            return "".join(part.get("text", "") for part in item["runs"] if isinstance(part, dict))
    if isinstance(item, list):
        return "".join(extract_text(part) for part in item)
    return ""


def normalize_count_value(value):
    """Mengubah teks jumlah (mis. '1.2K likes') menjadi angka string"""
    if value is None:
        return "0"
    text = str(value).strip()
    if not text:
        return "0"
    text = text.replace("\u202f", "").replace(",", "")
    suffix = text[-1].upper()
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    if suffix in multipliers and text[:-1]:
        try:
            return str(int(float(text[:-1]) * multipliers[suffix]))
        except ValueError:
            pass
    match = re.search(r"\d+", text)
    if match:
        return match.group(0)
    return text


def extract_comment_entities(framework_updates):
    """Mengambil mapping commentKey -> payload (dipakai untuk commentViewModel)"""
    entities = {}
    if not framework_updates:
        return entities
    batch = framework_updates.get("entityBatchUpdate", {})
    for mutation in batch.get("mutations", []):
        payload = mutation.get("payload", {})
        entity = payload.get("commentEntityPayload")
        if entity and entity.get("key"):
            entities[entity["key"]] = entity
    return entities


def _find_token_in_structure(node):
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            command = current.get("continuationCommand")
            if command and command.get("token"):
                return command["token"]
            for key in ("nextContinuationData", "reloadContinuationData"):
                cont = current.get(key)
                if isinstance(cont, dict) and cont.get("continuation"):
                    return cont["continuation"]
            if "continuationEndpoint" in current:
                endpoint = current["continuationEndpoint"]
                if isinstance(endpoint, dict):
                    command = endpoint.get("continuationCommand")
                    if command and command.get("token"):
                        return command["token"]
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return None


def extract_comment_continuation(initial_data):
    """Cari continuation token pertama untuk panel komentar"""
    if not isinstance(initial_data, (dict, list)):
        return None
    stack = [initial_data]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            panel = node.get("engagementPanelSectionListRenderer")
            if panel:
                identifier = panel.get("panelIdentifier") or panel.get("targetId")
                if identifier == "engagement-panel-comments-section":
                    token = _find_token_in_structure(panel)
                    if token:
                        return token
            target_id = node.get("targetId") or node.get("panelIdentifier")
            if target_id == "engagement-panel-comments-section":
                token = _find_token_in_structure(node)
                if token:
                    return token
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return None


def extract_next_continuation(data):
    """Ambil continuation token selanjutnya dari response API"""
    if not isinstance(data, dict):
        return None
    endpoints = data.get("onResponseReceivedEndpoints", [])
    for endpoint in endpoints:
        for key in ("reloadContinuationItemsCommand", "appendContinuationItemsAction"):
            if key in endpoint:
                token = _find_token_in_structure(endpoint[key])
                if token:
                    return token
    return _find_token_in_structure(data)


def parse_legacy_comment(thread_renderer, index):
    comment_renderer = thread_renderer.get("comment", {}).get("commentRenderer")
    if not comment_renderer:
        return None
    text = extract_text(comment_renderer.get("contentText"))
    if not text:
        return None
    author = extract_text(comment_renderer.get("authorText")) or "Unknown"
    published = extract_text(comment_renderer.get("publishedTimeText")) or "Unknown"
    like_text = (
        extract_text(comment_renderer.get("voteCount")) or comment_renderer.get("likeCount")
    )
    replies_renderer = thread_renderer.get("replies", {}).get("commentRepliesRenderer")
    replies_text = None
    if replies_renderer:
        replies_text = (
            extract_text(replies_renderer.get("moreText"))
            or extract_text(replies_renderer.get("viewReplies"))
            or replies_renderer.get("replyCount")
        )
    comment_id = comment_renderer.get("commentId")
    return {
        "index": index,
        "comment_id": comment_id,
        "author": author,
        "text": text.strip(),
        "published": published,
        "likes": normalize_count_value(like_text),
        "replies_count": normalize_count_value(replies_text),
    }


def parse_view_model_comment(thread_renderer, entities, index):
    view_model = thread_renderer.get("commentViewModel", {}).get("commentViewModel", {})
    comment_key = view_model.get("commentKey")
    if not comment_key:
        return None
    entity = entities.get(comment_key)
    if not entity:
        return None
    props = entity.get("properties", {})
    text = props.get("content", {}).get("content")
    if not text:
        return None
    author = props.get("authorButtonA11y") or entity.get("author", {}).get("displayName") or "Unknown"
    published = props.get("publishedTime") or "Unknown"
    toolbar = entity.get("toolbar", {})
    like_hint = toolbar.get("likeCountA11y") or toolbar.get("likeCountNotliked") or toolbar.get("likeCountLiked")
    replies_hint = toolbar.get("replyCount")
    comment_id = props.get("commentId")
    return {
        "index": index,
        "comment_id": comment_id,
        "author": author,
        "text": text.strip(),
        "published": published,
        "likes": normalize_count_value(like_hint),
        "replies_count": normalize_count_value(replies_hint),
    }


def parse_comment_from_thread(thread_renderer, entities, index):
    legacy = parse_legacy_comment(thread_renderer, index)
    if legacy:
        return legacy
    return parse_view_model_comment(thread_renderer, entities, index)


def parse_comment_response(data, entities, existing_total, seen_ids):
    items = []
    for endpoint in data.get("onResponseReceivedEndpoints", []):
        if "reloadContinuationItemsCommand" in endpoint:
            items.extend(endpoint["reloadContinuationItemsCommand"].get("continuationItems", []))
        if "appendContinuationItemsAction" in endpoint:
            items.extend(endpoint["appendContinuationItemsAction"].get("continuationItems", []))
    parsed = []
    for item in items:
        renderer = item.get("commentThreadRenderer")
        if not renderer:
            continue
        comment = parse_comment_from_thread(renderer, entities, existing_total + len(parsed) + 1)
        if not comment:
            continue
        dedupe_key = comment.get("comment_id") or f"{comment['author']}::{comment['text']}"
        if dedupe_key in seen_ids:
            continue
        seen_ids.add(dedupe_key)
        parsed.append(comment)
    return parsed


def fetch_comments_via_api(driver, url, target_count=None):
    """
    Gunakan endpoint internal YouTube untuk mengambil komentar.
    target_count: None untuk semua komentar, atau integer untuk jumlah spesifik
    """
    try:
        api_key = driver.run_js(
            "return (window.ytcfg && window.ytcfg.get) ? window.ytcfg.get('INNERTUBE_API_KEY') : null;"
        )
        context = driver.run_js(
            "return (window.ytcfg && window.ytcfg.get) ? window.ytcfg.get('INNERTUBE_CONTEXT') : null;"
        )
        initial_data = driver.run_js("return window.ytInitialData || null;")
        user_agent = driver.run_js("return navigator.userAgent;")
    except Exception as exc:
        print(f"⚠️  Gagal membaca konfigurasi YouTube: {exc}")
        return None

    if not api_key or not context or not initial_data:
        return None

    continuation = extract_comment_continuation(initial_data)
    if not continuation:
        return None

    api_endpoint = f"https://www.youtube.com/youtubei/v1/next?key={api_key}"
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://www.youtube.com",
        "Referer": url,
        "User-Agent": user_agent or "Mozilla/5.0",
        "X-YouTube-Client-Name": str(context.get("client", {}).get("clientName", "WEB")),
        "X-YouTube-Client-Version": context.get("client", {}).get("clientVersion", "2.20251109.10.00"),
    }

    comments = []
    seen_ids = set()
    entities_cache = {}

    with requests.Session() as session:
        token = continuation
        page = 0
        consecutive_empty = 0
        max_consecutive_empty = 5  # Tingkatkan toleransi
        
        while token:
            page += 1
            payload = {
                "context": context,
                "continuation": token,
            }
            try:
                response = session.post(api_endpoint, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
            except RequestException as req_err:
                print(f"⚠️  Permintaan komentar batch {page} gagal: {req_err}")
                # Jangan langsung break, coba lanjut dengan token berikutnya
                consecutive_empty += 1
                if consecutive_empty >= max_consecutive_empty:
                    break
                continue
            
            try:
                data = response.json()
            except ValueError as parse_err:
                print(f"⚠️  Response komentar tidak valid: {parse_err}")
                consecutive_empty += 1
                if consecutive_empty >= max_consecutive_empty:
                    break
                continue

            # Update entities cache
            entities_cache.update(extract_comment_entities(data.get("frameworkUpdates")))
            
            # Parse comments dari response
            new_comments = parse_comment_response(data, entities_cache, len(comments), seen_ids)
            
            if new_comments:
                comments.extend(new_comments)
                print(f"  📥 API batch {page}: +{len(new_comments)} komentar (total {len(comments)})")
                consecutive_empty = 0  # Reset counter
                
                # Jika ada target count dan sudah tercapai, stop
                if target_count and len(comments) >= target_count:
                    print(f"  ✅ Target {target_count:,} komentar tercapai!")
                    break
            else:
                consecutive_empty += 1
                if consecutive_empty <= 2:
                    print(f"  ⏭️  API batch {page}: tidak ada komentar baru, mencoba lanjut...")
                else:
                    print(f"  ⚠️  API batch {page}: tidak ada komentar baru ({consecutive_empty}x)")
                
                # Jika sudah beberapa kali berturut-turut tidak ada komentar baru, stop
                if consecutive_empty >= max_consecutive_empty:
                    print(f"  ⚠️  Tidak ada komentar baru setelah {max_consecutive_empty}x percobaan, berhenti.")
                    break

            # Ambil continuation token untuk batch selanjutnya
            next_token = extract_next_continuation(data)
            
            if not next_token:
                print("  ✅ Semua komentar telah diambil (tidak ada continuation token)")
                break
            
            # Pastikan token berbeda dari sebelumnya (cegah infinite loop)
            if next_token == token:
                print("  ⚠️  Token sama, kemungkinan sudah tidak ada komentar lagi")
                break
                
            token = next_token

    if comments:
        print(f"\n📊 Total berhasil mengambil {len(comments):,} komentar")
    
    return comments


def save_outputs(result, output_folder):
    """Simpan ke JSON, TXT, dan Excel dengan format yang menarik"""
    
    # Sanitize filename
    def sanitize(s):
        if not s:
            return "unknown"
        safe = re.sub(r'[\\/*?:"<>|]', '', s)
        safe = re.sub(r"\s+", '_', safe).strip('_')
        return safe[:100]
    
    video_id = result.get('video_id', 'unknown')
    title_safe = sanitize(result.get('video_title', 'unknown'))
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Buat folder berdasarkan judul video
    video_folder = os.path.join(output_folder, f"{title_safe}_{video_id}")
    os.makedirs(video_folder, exist_ok=True)
    
    base_name = f"comments_{ts}"
    
    # 1. JSON File (pretty formatted)
    json_path = os.path.join(video_folder, f"{base_name}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 2. TXT File (formatted untuk readability)
    txt_path = os.path.join(video_folder, f"{base_name}.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("═" * 80 + "\n")
        f.write("🎥 YOUTUBE COMMENT EXPORT\n")
        f.write("═" * 80 + "\n\n")
        
        f.write(f"📹 Video Title: {result.get('video_title', 'N/A')}\n")
        f.write(f"👤 Channel: {result.get('channel_name', 'N/A')}\n")
        f.write(f"🔗 URL: {result.get('video_url', 'N/A')}\n")
        f.write(f"💬 Total Comments: {result.get('total_comments', 0):,}\n")
        f.write(f"📅 Scraped At: {result.get('scraped_at', 'N/A')}\n")
        f.write(f"🔧 Source: {result.get('comments_source', 'N/A').upper()}\n")
        
        f.write("\n" + "═" * 80 + "\n")
        f.write("💬 COMMENTS\n")
        f.write("═" * 80 + "\n\n")
        
        for i, comment in enumerate(result.get('comments', []), start=1):
            author = comment.get('author', 'Unknown')
            published = comment.get('published', 'N/A')
            likes = comment.get('likes', '0')
            replies = comment.get('replies_count', '0')
            text = comment.get('text', '')
            text = ' '.join(text.split())
            
            f.write(f"[{i}] " + "─" * 73 + "\n")
            f.write(f"👤 {author}\n")
            f.write(f"📅 {published} | 👍 {likes} likes | 💬 {replies} replies\n")
            f.write(f"💭 {text}\n\n")
    
    # 3. Excel/CSV File
    csv_path = os.path.join(video_folder, f"{base_name}.csv")
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            if result.get('comments'):
                fieldnames = ['No', 'Author', 'Comment', 'Published', 'Likes', 'Replies']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, comment in enumerate(result.get('comments', []), start=1):
                    writer.writerow({
                        'No': i,
                        'Author': comment.get('author', 'Unknown'),
                        'Comment': comment.get('text', ''),
                        'Published': comment.get('published', 'N/A'),
                        'Likes': comment.get('likes', '0'),
                        'Replies': comment.get('replies_count', '0')
                    })
    except Exception as e:
        print(f"⚠️  Gagal membuat CSV: {e}")
    
    # 4. Summary file
    summary_path = os.path.join(video_folder, "README.txt")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("YouTube Comment Export Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Video: {result.get('video_title', 'N/A')}\n")
        f.write(f"Channel: {result.get('channel_name', 'N/A')}\n")
        f.write(f"Total Comments: {result.get('total_comments', 0):,}\n")
        f.write(f"Scraped: {result.get('scraped_at', 'N/A')}\n\n")
        f.write("Files:\n")
        f.write(f"  - {base_name}.json (Full data in JSON format)\n")
        f.write(f"  - {base_name}.txt (Human-readable text format)\n")
        f.write(f"  - {base_name}.csv (Excel-compatible CSV)\n")
    
    return {
        'folder': video_folder,
        'json': json_path,
        'txt': txt_path,
        'csv': csv_path,
        'summary': summary_path
    }


@browser(
    edge_executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    block_images_and_css=False,
    wait_for_complete_page_load=True,
    headless=False,
    reuse_driver=True,
)
def scrape_youtube_comments(driver: Driver, data):
    """Scraper YouTube comments yang enhanced"""
    url = data["url"]
    target_count = data.get("target_count")
    use_ai = data.get("use_ai", USE_AI_SELECTOR)
    
    print(f"🚀 Membuka video: {url}")
    driver.get(url)
    
    print("⏳ Menunggu halaman dimuat...")
    driver.sleep(10)
    
    print("📍 Scroll ke section komentar...")
    try:
        for i in range(5):
            driver.run_js("window.scrollBy(0, 500);")
            driver.sleep(2)
            if (i + 1) % 2 == 0:
                print(f"  Scroll {i+1}/5")
    except Exception as e:
        print(f"⚠️  Scroll error: {e}")
    
    driver.sleep(5)
    
    html_content = driver.page_html
    debug_folder = "debug_html"
    os.makedirs(debug_folder, exist_ok=True)
    
    video_id_match = re.search(r'v=([a-zA-Z0-9_-]+)', url)
    video_id = video_id_match.group(1) if video_id_match else "unknown"
    
    debug_file = f"{debug_folder}/youtube_{video_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(debug_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"🔍 Debug HTML disimpan: {debug_file}")
    
    if use_ai:
        print("🤖 Menganalisis dengan AI...")
        analyze_selectors_with_ai(html_content)
    
    soup = soupify(driver)
    
    # Ekstrak metadata
    print("📊 Mengekstrak metadata video...")
    
    # Multiple selectors untuk video title
    video_title = None
    title_selectors = [
        "h1 yt-formatted-string",
        "h1.ytd-watch-metadata yt-formatted-string",
        "yt-formatted-string.ytd-watch-metadata",
        "h1.style-scope.ytd-watch-metadata"
    ]
    for selector in title_selectors:
        try:
            elem = soup.select_one(selector)
            if elem:
                video_title = elem.get_text(strip=True)
                if video_title:
                    break
        except:
            continue
    
    if not video_title:
        video_title = "Unknown"
    
    # Multiple selectors untuk channel name
    channel_name = None
    channel_selectors = [
        "ytd-channel-name a",
        "ytd-channel-name yt-formatted-string",
        "yt-formatted-string#text.ytd-channel-name",
        "a.yt-simple-endpoint.ytd-channel-name"
    ]
    for selector in channel_selectors:
        try:
            elem = soup.select_one(selector)
            if elem:
                channel_name = elem.get_text(strip=True)
                if channel_name:
                    break
        except:
            continue
    
    if not channel_name:
        channel_name = "Unknown"
    
    print(f"  📹 Video: {video_title}")
    print(f"  👤 Channel: {channel_name}")
    
    # Fetch comments via API
    if target_count:
        print(f"🎯 Target: {target_count:,} komentar")
    else:
        print("🎯 Target: SEMUA komentar")
    
    print("💬 Mengambil komentar via API YouTube...")
    comments = fetch_comments_via_api(driver, url, target_count) or []
    
    if not comments:
        print("⚠️  Tidak ada komentar yang berhasil diambil")
    
    result = {
        "video_id": video_id,
        "video_url": url,
        "video_title": video_title,
        "channel_name": channel_name,
        "total_comments": len(comments),
        "scraped_at": datetime.now().isoformat(),
        "debug_file": debug_file,
        "comments": comments,
        "comments_source": "api" if comments else "none"
    }
    
    # Save ke multiple formats
    output_folder = "output"
    print("\n💾 Menyimpan output...")
    paths = save_outputs(result, output_folder)
    
    print(f"\n📁 Folder output: {paths['folder']}")
    print(f"  ✅ JSON: {os.path.basename(paths['json'])}")
    print(f"  ✅ TXT: {os.path.basename(paths['txt'])}")
    print(f"  ✅ CSV: {os.path.basename(paths['csv'])}")
    print(f"  ✅ README: {os.path.basename(paths['summary'])}")
    
    return result


def main():
    """Function utama dengan menu interaktif yang lebih baik"""
    print("═" * 70)
    print("🎥 YOUTUBE COMMENT SCRAPER - ENHANCED VERSION")
    print("═" * 70)
    print()
    
    if USE_AI_SELECTOR:
        print("🤖 AI Selector Detection: ✅ AKTIF")
    else:
        print("🤖 AI Selector Detection: ❌ TIDAK AKTIF")
        print("   (Set GEMINI_API_KEY untuk mengaktifkan)")
    print()
    
    # Input URL
    while True:
        url = input("📺 Masukkan URL YouTube video: ").strip()
        if not url:
            print("❌ URL tidak boleh kosong!")
            continue
        if "youtube.com/watch" in url or "youtu.be/" in url:
            break
        else:
            print("❌ URL tidak valid! Masukkan URL YouTube yang benar.")
    
    print()
    print("─" * 70)
    print("💬 PILIHAN JUMLAH KOMENTAR:")
    print("─" * 70)
    print("  1. Ambil SEMUA komentar (recommended)")
    print("  2. Ambil jumlah komentar tertentu (contoh: 100, 500, 1000)")
    print("─" * 70)
    
    while True:
        choice = input("\n📌 Pilihan Anda (1/2): ").strip()
        if choice == "1":
            target_count = None
            print("✅ Mode: Mengambil SEMUA komentar yang tersedia")
            break
        elif choice == "2":
            while True:
                try:
                    count_input = input("💬 Berapa jumlah komentar yang ingin diambil? ").strip()
                    target_count = int(count_input)
                    if target_count > 0:
                        print(f"✅ Mode: Mengambil {target_count:,} komentar")
                        break
                    else:
                        print("❌ Jumlah harus lebih dari 0!")
                except ValueError:
                    print("❌ Masukkan angka yang valid!")
            break
        else:
            print("❌ Pilih 1 atau 2!")
    
    # AI Detection
    use_ai = False
    if USE_AI_SELECTOR:
        print()
        ai_choice = input("🤖 Gunakan AI untuk auto-detect selector? (y/n, default: y): ").strip().lower()
        use_ai = ai_choice != 'n'
    
    print()
    print("═" * 70)
    print("🔄 MEMULAI SCRAPING...")
    print("═" * 70)
    print("⚠️  Note: Proses ini mungkin memakan waktu tergantung jumlah komentar")
    print()
    
    data = {
        "url": url,
        "target_count": target_count,
        "use_ai": use_ai
    }
    
    try:
        result = scrape_youtube_comments(data)
        
        if result and result.get('total_comments', 0) > 0:
            print()
            print("═" * 70)
            print("✅ SCRAPING BERHASIL!")
            print("═" * 70)
            print(f"📹 Video: {result['video_title']}")
            print(f"👤 Channel: {result['channel_name']}")
            print(f"💬 Total Komentar: {result['total_comments']:,}")
            print(f"🕐 Waktu: {result['scraped_at']}")
            
            if result.get('comments'):
                print()
                print("─" * 70)
                print("👀 PREVIEW 5 KOMENTAR TERATAS:")
                print("─" * 70)
                for i, comment in enumerate(result['comments'][:5], 1):
                    print(f"\n[{i}] 👤 {comment['author']}")
                    print(f"    📅 {comment['published']} | 👍 {comment['likes']} | 💬 {comment['replies_count']}")
                    preview = comment['text'][:150]
                    if len(comment['text']) > 150:
                        preview += "..."
                    print(f"    💭 {preview}")
        else:
            print()
            print("═" * 70)
            print("⚠️  TIDAK ADA KOMENTAR YANG BERHASIL DIAMBIL")
            print("═" * 70)
            print("💡 Kemungkinan penyebab:")
            print("   • Video tidak memiliki komentar")
            print("   • Komentar dinonaktifkan")
            print("   • Masalah koneksi atau API YouTube")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping dibatalkan oleh user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("═" * 70)
    print("✅ PROSES SELESAI!")
    print("═" * 70)
    print()


if __name__ == "__main__":
    main()