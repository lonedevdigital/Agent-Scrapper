"""
Modul Scraper Threads (Meta)
----------------------------
Mengambil postingan dan komentar Threads dengan fitur Stealth Mode,
auto-retry saat sinyal terputus, pemrosesan batch, dan penyimpanan bertahap.
"""

import os
import time
import re
import hashlib
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from playwright.sync_api import sync_playwright

from sources.base import BaseScraper, OUTPUT_CSV

SESSION_FILE = "threads_session.json"
HISTORY_FILE = "target_sudah scrapping.txt"

class ThreadsScraper(BaseScraper):
    def __init__(self, output_csv: str = OUTPUT_CSV, session_file: str = SESSION_FILE):
        super().__init__(platform_name="threads", output_csv=output_csv)
        self.session_file = session_file
        self.history_file = HISTORY_FILE

    @staticmethod
    def normalize_targets(lines_or_text) -> List[str]:
        """
        Mengekstrak dan menormalisasi URL Threads dari teks input.
        Mendukung format list berangka ('1. https://...', '2) ...'), bullet ('- ...'),
        domain threads.com, maupun share link.
        """
        if isinstance(lines_or_text, str):
            lines = lines_or_text.splitlines()
        else:
            lines = lines_or_text

        targets = []
        for line in lines:
            cleaned = line.strip()
            if not cleaned or cleaned.startswith("#"):
                continue

            match = re.search(r"https?://(?:www\.)?threads\.(?:net|com)/[^\s]+", cleaned)
            if match:
                url = match.group(0).rstrip(".,;)\"'>")
                normalized_url = url.replace("threads.com", "threads.net")
                targets.append(normalized_url)
            else:
                match_no_proto = re.search(r"(?:www\.)?threads\.(?:net|com)/[^\s]+", cleaned)
                if match_no_proto:
                    url = "https://" + match_no_proto.group(0).rstrip(".,;)\"'>")
                    normalized_url = url.replace("threads.com", "threads.net")
                    targets.append(normalized_url)

        return targets

    def get_already_scraped_urls(self) -> set:
        """Membaca daftar URL yang sudah pernah di-scrape dari file riwayat."""
        if not os.path.exists(self.history_file):
            return set()
        with open(self.history_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return set(self.normalize_targets(lines))

    def append_to_history(self, url: str):
        """Mencatat URL yang sukses di-scrape ke file riwayat."""
        try:
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(f"\n{url}")
        except Exception:
            pass

    @staticmethod
    def parse_post_id(url: str) -> str:
        """Mengekstrak ID postingan dari URL Threads."""
        match = re.search(r"/post/([A-Za-z0-9_-]+)", url)
        if match:
            return match.group(1)
        return "TH_" + hashlib.md5(url.encode()).hexdigest()[:8]

    def setup_stealth_browser(self, playwright_instance, headless: bool = True):
        """Menyiapkan peramban dengan konfigurasi anti-bot deteksi Meta/Instagram."""
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-position=0,0",
            "--ignore-certificate-errors",
            "--ignore-certificate-errors-spki-list"
        ]

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
        if os.path.exists(self.session_file):
            context_kwargs["storage_state"] = self.session_file

        context = browser.new_context(**context_kwargs)
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['id-ID', 'id', 'en-US', 'en'] });
        """)

        return browser, context

    def run_login(self, callback: Optional[Callable[[str], None]] = None) -> bool:
        """Membuka peramban interaktif untuk login manual dan menyimpan session cookies."""
        def log(msg):
            if callback:
                callback(msg)
            else:
                print(msg)

        log("[*] Membuka browser untuk login Threads...")
        with sync_playwright() as p:
            browser, context = self.setup_stealth_browser(p, headless=False)
            page = context.new_page()
            try:
                page.goto("https://www.threads.net/login", wait_until="domcontentloaded")
                log("[!] Silakan login di jendela browser yang terbuka.")
                log("[*] Menunggu Anda selesai login (klik/tutup halaman login)...")

                # Cek berkala apakah sudah berhasil login (halaman bukan login lagi)
                for _ in range(120): # Maksimal tunggu 4 menit
                    time.sleep(2)
                    current_url = page.url
                    if "login" not in current_url:
                        log("[✓] Deteksi login berhasil!")
                        time.sleep(3)
                        context.storage_state(path=self.session_file)
                        log(f"[✓] Sesi disimpan ke '{self.session_file}'.")
                        browser.close()
                        return True
            except Exception as e:
                log(f"[!] Error saat proses login: {e}")
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
        return False

    @staticmethod
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

    def scrape_url(
        self,
        page,
        url: str,
        max_scrolls: int = 10,
        log_func: Optional[Callable[[str], None]] = None,
        search_keyword: str = "mental health"
    ) -> List[Dict[str, Any]]:
        """
        Membuka satu URL Threads dan mengekstrak postingan utama beserta komentarnya
        menggunakan Scroll Adaptif (berhenti otomatis saat komentar habis).
        """
        def log(m):
            if log_func:
                log_func(m)

        post_id = self.parse_post_id(url)

        # Coba buka halaman dengan auto-retry 1x jika sinyal ngadat
        loaded = False
        for attempt in range(1, 3):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                loaded = True
                break
            except Exception as e:
                if attempt == 1:
                    log(f"    [!] Sinyal lambat/gagal memuat: {e}. Mencoba ulang dalam 4 detik...")
                    time.sleep(4)
                else:
                    log(f"    [!] Gagal memuat setelah percobaan ke-2. Melewati URL ini.")
                    return []

        time.sleep(2.5)

        # Scroll Adaptif: mendeteksi jika halaman bertambah panjang atau sudah mentok di akhir
        last_height = page.evaluate("document.body.scrollHeight")
        consecutive_no_change = 0
        for i in range(max_scrolls):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2.2)

            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                consecutive_no_change += 1
                if consecutive_no_change >= 2:
                    log(f"    [i] Scroll adaptif: seluruh komentar telah termuat (berhenti di scroll ke-{i+1}).")
                    break
            else:
                consecutive_no_change = 0
                last_height = new_height

        items = []
        root_text = ""
        try:
            post_elements = page.query_selector_all('div[data-pressable-container="true"], article')
            if post_elements:
                first_elem = post_elements[0]
                raw_root = first_elem.inner_text().strip()
                lines = [l for l in raw_root.split("\n") if l.strip() and l.lower() not in ["balas", "bagikan", "suka", "threads"]]
                root_text = " ".join(lines[:4])
        except Exception:
            pass

        if not root_text:
            root_text = page.title().replace(" | Threads", "").strip()

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
                        like_count = self.parse_metric_number(m_root.group(1))
                        reply_count = self.parse_metric_number(m_root.group(2))
                        clean_comment = raw_joined[:m_root.start()].strip()
                else:
                    # Komentar Balasan
                    m_two = re.search(r'(\d+(?:[,\.]\d+)?\s*(?:rb|k)?)\s+(\d+)\s*$', raw_joined)
                    if m_two:
                        like_count = self.parse_metric_number(m_two.group(1))
                        reply_count = self.parse_metric_number(m_two.group(2))
                        clean_comment = raw_joined[:m_two.start()].strip()
                    else:
                        m_one = re.search(r'(\d+(?:[,\.]\d+)?\s*(?:rb|k)?)\s*$', raw_joined)
                        if m_one:
                            like_count = self.parse_metric_number(m_one.group(1))
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

                m_auth = re.match(r"^([a-zA-Z0-9_\.]+)", clean_comment)
                threads_author = m_auth.group(1) if m_auth else "user_anon"

                items.append({
                    "comment_id": f"TH_{post_id}_{idx:03d}",
                    "platform": "threads",
                    "search_keyword": search_keyword if search_keyword else "mental health",
                    "author": threads_author,
                    "post_id": post_id,
                    "post_title": root_text,
                    "comment_text": clean_comment,
                    "parent_id": parent_id,
                    "parent_text": parent_text,
                    "is_reply": is_reply,
                    "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "like_count": like_count,
                    "reply_count": reply_count,
                    "emojis": self.extract_emojis(clean_comment),
                    "has_capslock": self.detect_capslock(clean_comment),
                    "is_sarcasm": "",
                    "actual_sentiment": "",
                    "topic_category": ""
                })
            except Exception:
                continue

        return items

    def run_batch_scrape(
        self,
        targets: List[str],
        batch_size: int = 5,
        cooldown: int = 10,
        skip_already_scraped: bool = True,
        search_keyword: str = "mental health",
        log_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
        stop_event: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Menjalankan proses scraping bertahap (batch) dengan auto-save per URL,
        jeda cooldown antar-batch, serta pencegahan kehilangan data jika sinyal putus.
        """
        def log(msg):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)

        # Normalisasi targets
        normalized_targets = self.normalize_targets(targets)
        if not normalized_targets:
            log("[!] Tidak ada URL target yang valid.")
            return []

        # Filter URL yang sudah pernah di-scrape jika opsi aktif
        if skip_already_scraped:
            history = self.get_already_scraped_urls()
            active_targets = [u for u in normalized_targets if u not in history]
            skipped_count = len(normalized_targets) - len(active_targets)
            if skipped_count > 0:
                log(f"[i] Melewati {skipped_count} URL yang sudah pernah di-scrape sebelumnya.")
        else:
            active_targets = normalized_targets

        total_targets = len(active_targets)
        if total_targets == 0:
            log("[✓] Semua target dalam daftar sudah pernah di-scrape!")
            return []

        log(f"[+] Memulai scraping {total_targets} URL target dengan ukuran batch {batch_size}...")

        all_collected = []
        total_batches = (total_targets + batch_size - 1) // batch_size

        with sync_playwright() as p:
            browser, context = self.setup_stealth_browser(p, headless=True)
            page = context.new_page()

            for target_idx, url in enumerate(active_targets, 1):
                # Cek pembatalan oleh user via GUI
                if stop_event and stop_event.is_set():
                    log("\n[!] Scraping dihentikan oleh pengguna.")
                    break

                current_batch = ((target_idx - 1) // batch_size) + 1
                log(f"\n[{target_idx}/{total_targets}] Batch {current_batch}/{total_batches} -> {url}")

                # Scrape URL ini
                records = self.scrape_url(page, url, log_func=log, search_keyword=search_keyword)
                if records:
                    all_collected.extend(records)
                    # AUTO-SAVE LANGSUNG KE CSV (Anti Data-Loss)
                    total_in_csv = self.save_records(records)
                    self.append_to_history(url)
                    log(f"    [✓] +{len(records)} komentar diekstrak. Total dataset saat ini: {total_in_csv} baris.")
                else:
                    log(f"    [-] Tidak ada komentar yang berhasil diambil dari URL ini.")

                # Kirim sinyal progress ke GUI
                if progress_callback:
                    progress_callback(target_idx, total_targets, len(all_collected))

                # Cek jika batch saat ini selesai dan bukan target terakhir
                if target_idx % batch_size == 0 and target_idx < total_targets:
                    log(f"\n[⏸ Batch {current_batch} Selesai] Istirahat {cooldown} detik agar jaringan stabil...")
                    for s in range(cooldown):
                        if stop_event and stop_event.is_set():
                            break
                        time.sleep(1)
                else:
                    time.sleep(2.5)

            try:
                browser.close()
            except Exception:
                pass

        log(f"\n[✓] Selesai! Berhasil mengumpulkan {len(all_collected)} data baru.")
        return all_collected

    def search_threads_posts(
        self,
        keyword: str,
        max_scrolls: int = 3,
        existing_urls: Optional[set] = None,
        callback: Optional[Callable[[str], None]] = None
    ) -> List[Dict[str, str]]:
        """
        Mencari postingan utas utama di Threads berdasarkan kata kunci,
        mengambil URL kanonikal, nama penulis (@username), ID, dan cuplikan teks utas utama.
        """
        def log(msg):
            if callback:
                callback(msg)
            else:
                print(msg)

        if not keyword.strip():
            log("[!] Kata kunci pencarian kosong.")
            return []

        encoded_kw = urllib.parse.quote(keyword.strip())
        search_url = f"https://www.threads.net/search?q={encoded_kw}&serp_type=default"

        log(f"[*] Menghubungi Threads Search untuk keyword: '{keyword}'...")

        results = []
        seen_urls = set(existing_urls) if existing_urls else set()

        try:
            with sync_playwright() as p:
                browser, context = self.setup_stealth_browser(p, headless=True)
                page = context.new_page()

                try:
                    page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
                except Exception as e:
                    log(f"[!] Gagal membuka halaman pencarian: {e}")
                    browser.close()
                    return []

                time.sleep(3.5)

                for scroll_idx in range(max_scrolls):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1.8)

                links = page.query_selector_all('a[href*="/post/"]')
                log(f"[i] Menganalisis {len(links)} tautan postingan...")

                for l in links:
                    href = l.get_attribute("href")
                    if not href:
                        continue

                    match = re.search(r"/(?:@([A-Za-z0-9_.-]+)/)?post/([A-Za-z0-9_-]+)", href)
                    if not match:
                        continue

                    author = f"@{match.group(1)}" if match.group(1) else "@threads_user"
                    post_id = match.group(2)
                    canonical_url = f"https://www.threads.net/{author}/post/{post_id}"

                    if canonical_url in seen_urls:
                        continue
                    seen_urls.add(canonical_url)

                    # Ambil teks container postingan terdekat
                    container_text = page.evaluate("""(elem) => {
                        let curr = elem;
                        for (let i = 0; i < 7; i++) {
                            if (!curr) break;
                            if (curr.innerText && curr.innerText.length > 40 && curr.querySelectorAll('a[href*="/post/"]').length <= 2) {
                                return curr.innerText;
                            }
                            curr = curr.parentElement;
                        }
                        return elem.parentElement ? elem.parentElement.innerText : "";
                    }""", l)

                    raw_lines = [x.strip() for x in container_text.splitlines() if x.strip()]
                    clean_lines = []
                    for line in raw_lines:
                        l_strip = line.strip()
                        if l_strip.lower() == author.lstrip("@").lower():
                            continue
                        if re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$", l_strip) or re.match(r"^\d+\s*(?:hari|jam|m|d|h|w|detik)$", l_strip.lower()):
                            continue
                        if l_strip.lower() in ["balas", "bagikan", "suka", "threads", "populer", "lihat aktivitas", "terjemahkan"]:
                            continue
                        if re.match(r"^\d+(?:[,\.]\d+)?\s*(?:rb|k)?$", l_strip.lower()):
                            continue
                        clean_lines.append(l_strip)

                    snippet = " ".join(clean_lines[:4]) if clean_lines else (container_text[:150])
                    snippet = re.sub(r"\s+", " ", snippet).strip()

                    results.append({
                        "author": author,
                        "post_id": post_id,
                        "url": canonical_url,
                        "snippet": snippet if snippet else "(Tidak ada teks cuplikan)"
                    })

                browser.close()
        except Exception as e:
            log(f"[!] Error saat pencarian Threads: {e}")

        log(f"[✓] Berhasil menemukan {len(results)} utas postingan baru terkait '{keyword}'.")
        return results
