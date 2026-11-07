"""
Scraper Threads (Meta) untuk Dataset Riset Kesehatan Mental
-----------------------------------------------------------
Fitur:
- Anti-Detection (Stealth): Bypass deteksi bot Meta/Instagram (--disable-blink-features, remove navigator.webdriver).
- Fitur --login: Login manual sekali via browser untuk menyimpan sesi (threads_session.json).
- Mengambil postingan utama (root post) sebagai konteks (post_title).
- Mengambil komentar balasan (replies) beserta metrik likes, waktu, dan parent context.
- Otomatis melakukan anonimisasi ID pengguna (hash SHA-256) untuk etika riset & UU PDP.
- Otomatis mengekstrak emoji (🤡, 😭, dll.) dan mendeteksi penekanan capslock.
- Menyimpan hasil ke dataset_mental_health.csv sesuai skema template penelitian.
"""

import os
import sys
import time
import re
import hashlib
from datetime import datetime
import pandas as pd
import emoji
from playwright.sync_api import sync_playwright

OUTPUT_CSV = "dataset_mental_health.csv"
TARGETS_FILE = "targets_threads.txt"
SESSION_FILE = "threads_session.json"

COLUMNS = [
    "comment_id",
    "platform",
    "search_keyword",
    "post_id",
    "post_title",
    "comment_text",
    "parent_id",
    "parent_text",
    "is_reply",
    "created_at",
    "like_count",
    "reply_count",
    "emojis",
    "has_capslock",
    "is_sarcasm",
    "actual_sentiment",
    "topic_category"
]

def anonymize_id(text: str) -> str:
    """Mengubah username/ID asli menjadi kode hash anonim 8 karakter."""
    if not text:
        return "user_anon"
    return "user_" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]

def extract_emojis(text: str) -> str:
    """Mengekstrak seluruh emoji yang ada di dalam teks."""
    if not text:
        return ""
    emojis_found = [c for c in text if c in emoji.EMOJI_DATA]
    return "".join(emojis_found)

def detect_capslock(text: str) -> int:
    """Mendeteksi apakah terdapat kata dengan huruf kapital penuh (penekanan emosi/sarkasme)."""
    if not text:
        return 0
    words = re.findall(r"\b[A-Z]{3,}\b", text)
    return 1 if len(words) >= 1 else 0

def load_targets(filename: str) -> list:
    """Membaca dan menormalisasi daftar URL Threads dari file teks."""
    if not os.path.exists(filename):
        print(f"[!] File target '{filename}' tidak ditemukan.")
        return []
    
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    targets = []
    for line in lines:
        cleaned = line.strip()
        # Lewati baris kosong atau komentar
        if not cleaned or cleaned.startswith("#"):
            continue

        # Ekstrak URL valid (mengabaikan awalan '1. ', '2) ', '- ', '[1]', dsb.)
        match = re.search(r"https?://(?:www\.)?threads\.(?:net|com)/[^\s]+", cleaned)
        if match:
            url = match.group(0).rstrip(".,;)\"'>")
            # Normalisasi domain threads.com ke domain resmi threads.net
            normalized_url = url.replace("threads.com", "threads.net")
            targets.append(normalized_url)
        else:
            # Fallback jika URL dimasukkan tanpa awalan http/https
            match_no_proto = re.search(r"(?:www\.)?threads\.(?:net|com)/[^\s]+", cleaned)
            if match_no_proto:
                url = "https://" + match_no_proto.group(0).rstrip(".,;)\"'>")
                normalized_url = url.replace("threads.com", "threads.net")
                targets.append(normalized_url)

    return targets

def ensure_csv_exists():
    """Memastikan file dataset CSV sudah ada dengan header yang sesuai."""
    if not os.path.exists(OUTPUT_CSV):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
        print(f"[+] Membuat berkas baru '{OUTPUT_CSV}'.")

def parse_post_id(url: str) -> str:
    """Mengekstrak ID postingan dari URL Threads."""
    match = re.search(r"/post/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)
    return "TH_" + hashlib.md5(url.encode()).hexdigest()[:8]

def setup_stealth_browser(playwright_instance, headless: bool = False, storage_state: str = None):
    """
    Meluncurkan browser dengan konfigurasi Stealth untuk menghindari
    deteksi bot otomatis oleh Meta / Instagram (mengatasi 'unexpected error').
    """
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-infobars",
        "--window-position=0,0",
        "--ignore-certificate-errors",
        "--ignore-certificate-errors-spki-list"
    ]

    # Coba gunakan Google Chrome asli jika terpasang di Windows
    browser = None
    for channel_name in ["chrome", "msedge", None]:
        try:
            if channel_name:
                browser = playwright_instance.chromium.launch(
                    headless=headless,
                    channel=channel_name,
                    args=launch_args
                )
            else:
                browser = playwright_instance.chromium.launch(
                    headless=headless,
                    args=launch_args
                )
            break
        except Exception:
            continue

    if browser is None:
        browser = playwright_instance.chromium.launch(headless=headless, args=launch_args)

    context_kwargs = {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1280, "height": 800},
        "locale": "id-ID",
        "timezone_id": "Asia/Jakarta"
    }
    if storage_state and os.path.exists(storage_state):
        context_kwargs["storage_state"] = storage_state

    context = browser.new_context(**context_kwargs)

    # Injeksi script untuk mematikan penanda otomatisasi
    context.add_init_script("""
        // 1. Sembunyikan navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });

        // 2. Tirukan objek window.chrome milik browser asli
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };

        // 3. Atur plugin dan bahasa lokal
        Object.defineProperty(navigator, 'languages', {
            get: () => ['id-ID', 'id', 'en-US', 'en']
        });
    """)

    return browser, context

def run_login():
    """
    Membuka browser interaktif dengan Stealth Mode untuk login Threads secara manual,
    lalu menyimpan cookies dan sesi ke threads_session.json.
    """
    print("=" * 60)
    print("  LOGIN MANUAL THREADS (META) - STEALTH MODE")
    print("=" * 60)
    print("[*] Meluncurkan peramban dengan proteksi anti-deteksi bot...")
    print("[*] Membuka halaman login Threads...")

    with sync_playwright() as p:
        browser, context = setup_stealth_browser(p, headless=False)
        page = context.new_page()

        # Buka halaman login Threads
        page.goto("https://www.threads.net/login", wait_until="domcontentloaded")

        print("\n" + "=" * 60)
        print("PETUNJUK LOGIN:")
        print("1. Masukkan username dan password Anda pada jendela browser.")
        print("2. (TIPS) Jika muncul opsi 'Masuk dengan Instagram', Anda juga")
        print("   bisa membuka tab baru ke https://www.instagram.com, login")
        print("   di sana, lalu kembali refresh halaman Threads.")
        print("3. Setelah berhasil masuk ke Beranda / Feed Threads,")
        print("   KEMBALI KE TERMINAL INI lalu tekan tombol [ENTER].")
        print("=" * 60 + "\n")

        input(">> Tekan [ENTER] di sini setelah Anda selesai login di browser... ")

        # Simpan state sesi
        context.storage_state(path=SESSION_FILE)
        print(f"\n[✓] Sesi login BERHASIL disimpan ke '{SESSION_FILE}'!")
        print("[*] Untuk berikutnya, Anda dapat langsung menjalankan scraping:")
        print("    py scraper_threads.py\n")
        browser.close()

def parse_metric_number(val_str: str) -> int:
    """Mengubah format angka teks Threads (misal: '1,7 rb', '2.5k', '450') menjadi integer."""
    if not val_str:
        return 0
    val_str = str(val_str).strip().lower().replace("\xa0", " ")
    try:
        if "rb" in val_str or "k" in val_str:
            num_part = re.sub(r"[^\d,\.]", "", val_str).replace(",", ".")
            return int(float(num_part) * 1000)
        elif "jt" in val_str or "m" in val_str:
            num_part = re.sub(r"[^\d,\.]", "", val_str).replace(",", ".")
            return int(float(num_part) * 1000000)
        else:
            num_part = re.sub(r"[^\d]", "", val_str)
            return int(num_part) if num_part else 0
    except Exception:
        return 0

def scrape_threads_url(page, url: str, max_scrolls: int = 10):
    """
    Membuka URL Threads, menunggu konten dirender, melakukan scroll adaptif
    (berhenti otomatis saat komentar habis), dan mengekstrak metrik likes & replies.
    """
    print(f"\n[*] Mengakses: {url}")
    post_id = parse_post_id(url)
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as e:
        print(f"[!] Gagal memuat halaman: {e}")
        return []

    time.sleep(2.5)  # Jeda render awal
    
    # Scroll adaptif ke bawah: berhenti otomatis jika komentar sudah habis
    last_height = page.evaluate("document.body.scrollHeight")
    consecutive_no_change = 0
    for i in range(max_scrolls):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        print(f"[*] Melakukan scroll adaptif ({i+1}/{max_scrolls})...")
        time.sleep(2.2)

        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            consecutive_no_change += 1
            if consecutive_no_change >= 2:
                print(f"[i] Komentar sudah habis termuat (berhenti di scroll ke-{i+1}).")
                break
        else:
            consecutive_no_change = 0
            last_height = new_height

    items = []
    
    # 1. Cari postingan utama (root post)
    root_text = ""
    try:
        post_elements = page.query_selector_all('div[data-pressable-container="true"], article')
        if post_elements:
            first_elem = post_elements[0]
            raw_root = first_elem.inner_text().strip()
            lines = [l for l in raw_root.split("\n") if l.strip() and not l.lower() in ["balas", "bagikan", "suka", "threads"]]
            root_text = " ".join(lines[:4])
    except Exception as e:
        print(f"[!] Catatan saat ekstraksi postingan utama: {e}")

    if not root_text:
        root_text = page.title().replace(" | Threads", "").strip()

    print(f"[+] Konteks Postingan Utama: \"{root_text[:75]}...\"")

    # 2. Ambil seluruh teks komentar / balasan
    comment_blocks = page.query_selector_all('div[data-pressable-container="true"]')
    if not comment_blocks:
        comment_blocks = page.query_selector_all('article')

    seen_texts = set()
    root_saved = False

    for idx, block in enumerate(comment_blocks):
        try:
            raw_content = block.inner_text().strip()
            if not raw_content or len(raw_content) < 5:
                continue

            lines = [l.strip() for l in raw_content.split("\n") if l.strip()]
            filtered_lines = [
                l for l in lines 
                if l.lower() not in ["balas", "bagikan", "suka", "repost", "threads", "ikuti", "follow", "terjemahkan", "populer", "lihat aktivitas", "belum ada balasan"]
                and not l.lower().startswith("balas ke")
            ]
            if not filtered_lines:
                continue

            raw_joined = " ".join(filtered_lines)

            # Ekstraksi metrik (likes & replies) dan pembersihan teks komentar
            like_count = 0
            reply_count = 0
            clean_comment = raw_joined

            if idx == 0 and not root_saved:
                # Postingan Utama
                m_root = re.search(r'(\d+(?:[,\.]\d+)?\s*(?:rb|k|jt|m)?)\s+(\d+)\s*(?:\d+\s+)?(?:\d+\s+)?(?:Populer|Lihat aktivitas|Balas ke.*)?$', raw_joined)
                if m_root:
                    like_count = parse_metric_number(m_root.group(1))
                    reply_count = parse_metric_number(m_root.group(2))
                    clean_comment = raw_joined[:m_root.start()].strip()
            else:
                # Komentar Balasan
                m_two = re.search(r'(\d+(?:[,\.]\d+)?\s*(?:rb|k)?)\s+(\d+)\s*$', raw_joined)
                if m_two:
                    like_count = parse_metric_number(m_two.group(1))
                    reply_count = parse_metric_number(m_two.group(2))
                    clean_comment = raw_joined[:m_two.start()].strip()
                else:
                    m_one = re.search(r'(\d+(?:[,\.]\d+)?\s*(?:rb|k)?)\s*$', raw_joined)
                    if m_one:
                        like_count = parse_metric_number(m_one.group(1))
                        clean_comment = raw_joined[:m_one.start()].strip()

            clean_comment = re.sub(r'\s*Terjemahkan\s*$', '', clean_comment).strip()
            if not clean_comment:
                clean_comment = raw_joined
            
            text_hash = hashlib.md5(clean_comment.encode()).hexdigest()
            if text_hash in seen_texts:
                continue
            seen_texts.add(text_hash)

            is_reply = 1
            parent_id = post_id
            parent_text = root_text

            if idx == 0 and not root_saved:
                is_reply = 0
                parent_id = "null"
                parent_text = "null"
                root_saved = True

            comment_item = {
                "comment_id": f"TH_{post_id}_{idx:03d}",
                "platform": "threads",
                "search_keyword": "mental health",
                "post_id": post_id,
                "post_title": root_text,
                "comment_text": clean_comment,
                "parent_id": parent_id,
                "parent_text": parent_text,
                "is_reply": is_reply,
                "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "like_count": like_count,
                "reply_count": reply_count,
                "emojis": extract_emojis(clean_comment),
                "has_capslock": detect_capslock(clean_comment),
                "is_sarcasm": "",
                "actual_sentiment": "",
                "topic_category": ""
            }
            items.append(comment_item)

        except Exception as e:
            continue

    print(f"[+] Berhasil mengekstrak {len(items)} baris data dari URL ini.")
    return items

def main():
    if "--login" in sys.argv:
        run_login()
        return

    print("=" * 60)
    print("  SCRAPER THREADS (META) - DATASET KESEHATAN MENTAL")
    print("=" * 60)

    ensure_csv_exists()
    targets = load_targets(TARGETS_FILE)

    if not targets:
        print(f"\n[!] Belum ada URL target di '{TARGETS_FILE}'.")
        print("    Silakan buka berkas 'targets_threads.txt' dan tempel tautan Threads yang ingin di-scrape.")
        return

    print(f"\n[+] Ditemukan {len(targets)} URL target yang siap di-scrape.")
    
    all_new_records = []

    with sync_playwright() as p:
        storage = SESSION_FILE if os.path.exists(SESSION_FILE) else None
        if storage:
            print(f"[+] Memuat sesi login tersimpan ('{SESSION_FILE}'). Scraping berjalan dalam status login.")
        else:
            print("[i] Sesi login tidak ditemukan. Berjalan sebagai tamu (guest).")
            print("    Tips: Jalankan 'py scraper_threads.py --login' untuk menyimpan sesi login.")

        print("[*] Meluncurkan browser otomatis (Stealth Mode)...")
        browser, context = setup_stealth_browser(p, headless=True, storage_state=storage)
        page = context.new_page()

        for idx, url in enumerate(targets, 1):
            print(f"\n--- Memproses Target ({idx}/{len(targets)}) ---")
            records = scrape_threads_url(page, url)
            all_new_records.extend(records)
            time.sleep(3)

        browser.close()

    if all_new_records:
        df_new = pd.DataFrame(all_new_records)
        if os.path.exists(OUTPUT_CSV) and os.path.getsize(OUTPUT_CSV) > 0:
            df_existing = pd.read_csv(OUTPUT_CSV)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.drop_duplicates(subset=["comment_id"], keep="first", inplace=True)
        else:
            df_combined = df_new

        df_combined.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
        print(f"\n[✓] SUKSES! Total {len(df_combined)} data kini tersimpan di '{OUTPUT_CSV}'.")
    else:
        print("\n[!] Tidak ada data baru yang diekstrak. Pastikan URL dapat diakses secara publik.")

if __name__ == "__main__":
    main()
