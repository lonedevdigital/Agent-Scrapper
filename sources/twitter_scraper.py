"""
Modul Scraper X (Twitter)
-------------------------
Mengambil postingan dan komentar/balasan dari X (Twitter) dengan fitur:
- Persistent Browser Context (profil browser lokal untuk lolos dari deteksi bot zero-history)
- Penghapusan flag automasi (--enable-automation bypass) & deep stealth injection
- Manajemen sesi cookies (twitter_session.json & .twitter_user_data)
- Scrolling adaptif untuk memuat seluruh balasan cuitan
- Ekstraksi Twemoji/emoji asli unicode, metrik, timestamp, dan teks
- Auto-save bertahap (incremental checkpoint) ke CSV
"""

import os
import time
import re
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from playwright.sync_api import sync_playwright

from sources.base import BaseScraper, OUTPUT_CSV, safe_launch_persistent_context

SESSION_FILE = "twitter_session.json"
HISTORY_FILE = "target_sudah scrapping_twitter.txt"
USER_DATA_DIR = os.path.abspath(".twitter_user_data")

class TwitterScraper(BaseScraper):
    def __init__(
        self,
        output_csv: str = OUTPUT_CSV,
        session_file: str = SESSION_FILE,
        user_data_dir: str = USER_DATA_DIR
    ):
        super().__init__(platform_name="twitter", output_csv=output_csv)
        self.session_file = session_file
        self.history_file = HISTORY_FILE
        self.user_data_dir = user_data_dir
        os.makedirs(self.user_data_dir, exist_ok=True)

    @staticmethod
    def normalize_targets(lines_or_text) -> List[str]:
        """
        Mengekstrak dan menormalisasi URL status X (Twitter) dari input teks atau list.
        Mendukung format bernomor ('1. https://...', '2) ...'), bullet ('- ...'),
        domain twitter.com maupun x.com, serta membersihkan query string (misal ?s=20).
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

            match = re.search(r"https?://(?:www\.)?(?:twitter|x)\.com/[A-Za-z0-9_]+/status/\d+", cleaned)
            if match:
                url = match.group(0).rstrip(".,;)\"'>")
                normalized_url = re.sub(r"https?://(?:www\.)?twitter\.com", "https://x.com", url)
                targets.append(normalized_url)
            else:
                match_no_proto = re.search(r"(?:www\.)?(?:twitter|x)\.com/[A-Za-z0-9_]+/status/\d+", cleaned)
                if match_no_proto:
                    url = "https://" + match_no_proto.group(0).rstrip(".,;)\"'>")
                    normalized_url = re.sub(r"https?://(?:www\.)?twitter\.com", "https://x.com", url)
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
        """Mengekstrak Tweet / Status ID dari URL X (Twitter)."""
        match = re.search(r"/status/(\d+)", url)
        if match:
            return match.group(1)
        return "TW_" + hashlib.md5(url.encode()).hexdigest()[:8]

    def setup_persistent_browser(self, playwright_instance, headless: bool = True):
        """
        Menyiapkan peramban dengan Persistent Context (User Data Directory asli)
        untuk menghindari deteksi bot zero-history dan menghapus flag automasi.
        """
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-position=0,0",
            "--ignore-certificate-errors",
            "--ignore-certificate-errors-spki-list",
            "--disable-features=IsolateOrigins,site-per-process",
        ]

        context = safe_launch_persistent_context(
            playwright_instance,
            user_data_dir=self.user_data_dir,
            headless=headless,
            args=launch_args,
            ignore_default_args=["--enable-automation"],
            viewport={"width": 1280, "height": 800},
            locale="id-ID",
            timezone_id="Asia/Jakarta",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        context.add_init_script("""
            // Hapus navigator.webdriver sepenuhnya
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            try { delete Object.getPrototypeOf(navigator).webdriver; } catch (e) {}

            // Mock window.chrome lengkap
            window.chrome = {
                app: { isInstalled: false, InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }, RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' } },
                runtime: { OnInstalledReason: {}, OnRestartRequiredReason: {}, PlatformArch: {}, PlatformNaclArch: {}, PlatformOs: {}, RequestUpdateCheckStatus: {} },
                loadTimes: function() {},
                csi: function() {}
            };

            // Mock navigator.plugins agar terdeteksi seperti Google Chrome fisik
            if (!navigator.plugins || navigator.plugins.length === 0) {
                const dummyPlugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
                ];
                Object.defineProperty(navigator, 'plugins', { get: () => dummyPlugins });
            }

            // Normalisasi bahasa
            Object.defineProperty(navigator, 'languages', { get: () => ['id-ID', 'id', 'en-US', 'en'] });
        """)

        # Muat dan suntikkan cookies dari session_file jika ada
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                cookies = state_data.get("cookies", [])
                if cookies:
                    context.add_cookies(cookies)
            except Exception:
                pass

        return context

    def save_auth_token_session(self, auth_token: str, callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Menyimpan cookie auth_token dari peramban fisik ke session_file dan persistent context,
        lalu memverifikasi koneksi login ke x.com/home.
        """
        def log(msg):
            if callback:
                callback(msg)
            else:
                print(msg)

        clean_token = auth_token.strip()
        if not clean_token:
            log("[!] auth_token tidak boleh kosong.")
            return False

        # Siapkan struktur cookies standar Playwright
        session_data = {
            "cookies": [
                {
                    "name": "auth_token",
                    "value": clean_token,
                    "domain": ".x.com",
                    "path": "/",
                    "expires": 1893456000,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None"
                },
                {
                    "name": "auth_token",
                    "value": clean_token,
                    "domain": ".twitter.com",
                    "path": "/",
                    "expires": 1893456000,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None"
                }
            ],
            "origins": [
                {
                    "origin": "https://x.com",
                    "localStorage": []
                }
            ]
        }

        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2)
            log(f"[*] Cookie auth_token tersimpan ke '{self.session_file}'.")
            log("[*] Memverifikasi status sesi login ke x.com...")

            with sync_playwright() as p:
                context = self.setup_persistent_browser(p, headless=True)
                page = context.pages[0] if context.pages else context.new_page()
                try:
                    page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
                    time.sleep(3.5)
                    # Simpan full storage state terbaru dengan cookie respons dari X
                    context.storage_state(path=self.session_file)

                    if "login" not in page.url and "flow" not in page.url:
                        log("[✓] Verifikasi Berhasil! Sesi login X / Twitter aktif (Halaman Beranda terdeteksi).")
                        return True
                    else:
                        log("[!] Token tersimpan, namun halaman dialihkan ke login. Pastikan auth_token masih aktif dan belum logout.")
                        return False
                except Exception as e:
                    log(f"[i] Token tersimpan ke file, namun verifikasi jaringan mengalami timeout: {e}")
                    return True
                finally:
                    try:
                        context.close()
                    except Exception:
                        pass
        except Exception as e:
            log(f"[!] Gagal menyimpan cookie auth_token: {e}")
            return False

    def run_login(self, callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Membuka peramban interaktif (Persistent Context) untuk login manual ke X (Twitter)
        dan menyimpan session cookies.
        """
        def log(msg):
            if callback:
                callback(msg)
            else:
                print(msg)

        log("[*] Membuka browser Chrome Persistent Context untuk login X (Twitter)...")
        log("[i] Profil pengguna lokal diaktifkan (bebas dari deteksi automasi zero-history).")
        with sync_playwright() as p:
            context = self.setup_persistent_browser(p, headless=False)
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")
                log("[!] Silakan login ke akun X / Twitter Anda di jendela browser yang terbuka.")
                log("[*] Sistem otomatis mendeteksi ketika Anda berhasil masuk ke beranda (home)...")

                # Cek berkala apakah sudah berhasil login (maksimal tunggu 5 menit)
                for _ in range(150):
                    time.sleep(2)
                    try:
                        # Cek semua tab/halaman yang terbuka
                        for p_item in context.pages:
                            current_url = p_item.url
                            if "x.com" in current_url and "login" not in current_url and "flow" not in current_url:
                                time.sleep(3)
                                context.storage_state(path=self.session_file)
                                log(f"[✓] Deteksi login berhasil! Sesi disimpan ke '{self.session_file}' & profil lokal.")
                                context.close()
                                return True

                        cookies = context.cookies()
                        has_auth_token = any(c.get("name") == "auth_token" for c in cookies)
                        if has_auth_token:
                            time.sleep(3)
                            context.storage_state(path=self.session_file)
                            log(f"[✓] Deteksi cookie login (auth_token) berhasil! Sesi tersimpan.")
                            context.close()
                            return True
                    except Exception:
                        pass
            except Exception as e:
                log(f"[!] Error saat proses login X / Twitter: {e}")
            finally:
                try:
                    context.close()
                except Exception:
                    pass
        return False

    @staticmethod
    def parse_metric_number(val_str: str) -> int:
        """Mengubah format angka teks metrik X (misal: '1,7 rb', '2.5K', '450', '1.2M') menjadi integer."""
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

    @staticmethod
    def extract_element_metric(tweet_el, test_id: str) -> int:
        """Mengekstrak jumlah metrik (likes/replies) dari elemen tweet berdasarkan testid atau aria-label."""
        try:
            btn = tweet_el.query_selector(f'div[data-testid="{test_id}"], button[data-testid="{test_id}"]')
            if not btn:
                return 0

            # Cek teks langsung di dalam tombol
            txt = btn.inner_text().strip()
            if txt:
                parsed = TwitterScraper.parse_metric_number(txt)
                if parsed > 0:
                    return parsed

            # Cek aria-label (misal: "24 Suka", "12 Balasan", "350 Likes", "15 Replies")
            aria = btn.get_attribute("aria-label") or ""
            if aria:
                m = re.search(r"(\d+(?:[,\.]\d+)?\s*(?:rb|k|jt|m)?)", aria, re.IGNORECASE)
                if m:
                    return TwitterScraper.parse_metric_number(m.group(1))
        except Exception:
            pass
        return 0

    @staticmethod
    def extract_tweet_author(tweet_el) -> str:
        """Mengekstrak @handle bersih dari elemen tweet tanpa display name yang berantakan."""
        try:
            user_el = tweet_el.query_selector('div[data-testid="User-Name"]')
            if not user_el:
                return "@user_anon"
            raw_text = user_el.inner_text()
            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
            for line in lines:
                if line.startswith("@"):
                    # Bersihkan spasi atau karakter aneh setelah handle
                    handle = line.split()[0]
                    return handle
            # Fallback jika tidak ada yang berawalan @
            if lines:
                clean_name = re.sub(r'[^a-zA-Z0-9_]', '', lines[0])
                return f"@{clean_name}" if clean_name else "@user_anon"
        except Exception:
            pass
        return "@user_anon"

    @staticmethod
    def extract_clean_tweet_text(page, tweet_el) -> str:
        """
        Mengekstrak teks tweet lengkap dengan konversi Twemoji (img[alt]) ke emoji unicode,
        serta merapikan spasi/newline agar tidak merusak tata letak baris di Excel/CSV.
        """
        try:
            text_el = tweet_el.query_selector('div[data-testid="tweetText"]')
            if not text_el:
                return ""

            # Ekstrak dengan mengganti img[alt] menjadi karakter emoji asli
            raw_text = page.evaluate("""
                (el) => {
                    const clone = el.cloneNode(true);
                    const images = clone.querySelectorAll('img[alt]');
                    images.forEach(img => {
                        const alt = img.getAttribute('alt') || '';
                        img.replaceWith(alt);
                    });
                    return clone.innerText;
                }
            """, text_el)

            if not raw_text:
                return ""

            # Ganti baris baru berulang dengan spasi agar tampilan tabel CSV rapi
            cleaned = re.sub(r'[\r\n]+', ' ', raw_text).strip()
            cleaned = re.sub(r'\s{2,}', ' ', cleaned)
            return cleaned
        except Exception:
            try:
                text_el = tweet_el.query_selector('div[data-testid="tweetText"]')
                if text_el:
                    cleaned = re.sub(r'[\r\n]+', ' ', text_el.inner_text()).strip()
                    return re.sub(r'\s{2,}', ' ', cleaned)
                return ""
            except Exception:
                return ""

    @staticmethod
    def extract_tweet_timestamp(tweet_el) -> str:
        """Mengekstrak timestamp UTC ISO standar (YYYY-MM-DDTHH:MM:SSZ)."""
        try:
            time_el = tweet_el.query_selector("time")
            if time_el:
                dt = time_el.get_attribute("datetime")
                if dt:
                    return re.sub(r'\.\d+Z$', 'Z', dt)
        except Exception:
            pass
        return datetime.now(getattr(datetime, "UTC", None) or None).strftime("%Y-%m-%dT%H:%M:%SZ")

    def scrape_url(
        self,
        page,
        url: str,
        max_scrolls: int = 25,
        log_func: Optional[Callable[[str], None]] = None,
        search_keyword: str = "mental health mahasiswa"
    ) -> List[Dict[str, Any]]:
        """
        Membuka satu URL Tweet X dan mengekstrak cuitan utama beserta seluruh komentar/balasannya
        secara bertahap (iterative scroll collection) untuk mengatasi virtualized list Twitter DOM.
        """
        def log(m):
            if log_func:
                log_func(m)

        raw_post_id = self.parse_post_id(url)
        post_id_val = f"TW_{raw_post_id}"

        # Coba buka halaman tweet dengan auto-retry 1x
        loaded = False
        for attempt in range(1, 3):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                loaded = True
                break
            except Exception as e:
                if attempt == 1:
                    log(f"    [!] Sinyal lambat/gagal memuat cuitan: {e}. Mencoba ulang dalam 4 detik...")
                    time.sleep(4)
                else:
                    log("    [!] Gagal memuat setelah percobaan ke-2. Melewati URL ini.")
                    return []

        time.sleep(3.5)

        # Cek apakah diarahkan ke halaman login karena sesi kosong
        current_url = page.url
        if "login" in current_url or "i/flow/login" in current_url:
            log("    [!] Perhatian: X mengharuskan login untuk membaca komentar balasan.")
            log("    [!] Silakan gunakan tombol '🍪 Input Auth Token Twitter' di sidebar terlebih dahulu.")

        all_tweets: Dict[str, Dict[str, Any]] = {}
        root_tweet_info: Optional[Dict[str, Any]] = None
        consecutive_no_change = 0
        last_total_count = 0

        # Iterasi Scroll & Ekstraksi Bertahap (Mengatasi Virtualized DOM Twitter)
        for scroll_round in range(max_scrolls):
            # 1. Buka teks panjang ('Show more' / 'Tampilkan lainnya')
            try:
                show_more_elements = page.query_selector_all('[data-testid="tweet-text-show-more-link"]')
                for btn in show_more_elements:
                    try:
                        btn.click(timeout=600)
                    except Exception:
                        pass
            except Exception:
                pass

            # 2. Cek apakah ada tombol buka balasan tersembunyi / spam / lanjutan
            try:
                expand_buttons = page.query_selector_all(
                    'button:has-text("Show replies"), div[role="button"]:has-text("Show replies"), '
                    'button:has-text("Tampilkan balasan"), div[role="button"]:has-text("Tampilkan balasan"), '
                    'button:has-text("Show more replies"), div[role="button"]:has-text("Show more replies"), '
                    'button:has-text("Show probable spam"), div[role="button"]:has-text("Show probable spam")'
                )
                for btn in expand_buttons[:3]:
                    try:
                        btn.click(timeout=800)
                        time.sleep(0.8)
                    except Exception:
                        pass
            except Exception:
                pass

            # 3. Ekstrak seluruh artikel tweet yang sedang terpasang di DOM saat ini
            articles = page.query_selector_all('article[data-testid="tweet"]')
            for art in articles:
                try:
                    # Lewati tweet promosi / iklan sponsor
                    raw_text_check = art.inner_text()
                    if "Dipromosikan" in raw_text_check or "Promoted" in raw_text_check or "Ad" in raw_text_check.split("\n")[:2]:
                        continue

                    # Identifikasi status_id dari link internal tweet
                    status_id = None
                    for a in art.query_selector_all('a[href*="/status/"]'):
                        href = a.get_attribute("href") or ""
                        m = re.search(r"/status/(\d+)", href)
                        if m:
                            status_id = m.group(1)
                            break

                    tweet_text = self.extract_clean_tweet_text(page, art)
                    if not tweet_text or len(tweet_text) < 2:
                        continue

                    # Filter tweet yang hanya mention user tanpa teks & tanpa emoji
                    clean_no_mentions = re.sub(r'@\w+', '', tweet_text).strip()
                    if not clean_no_mentions and not self.extract_emojis(tweet_text):
                        continue

                    author = self.extract_tweet_author(art)
                    like_count = self.extract_element_metric(art, "like")
                    reply_count = self.extract_element_metric(art, "reply")
                    created_at = self.extract_tweet_timestamp(art)

                    is_root = (status_id == raw_post_id) if status_id else False

                    tweet_data = {
                        "status_id": status_id,
                        "author": author,
                        "text": tweet_text,
                        "like_count": like_count,
                        "reply_count": reply_count,
                        "created_at": created_at,
                        "is_root": is_root
                    }

                    # Tangkap root tweet yang cocok dengan ID postingan utama
                    if is_root and root_tweet_info is None:
                        root_tweet_info = tweet_data

                    # Gunakan status_id atau hash teks sebagai kunci unik
                    tweet_key = status_id if status_id else hashlib.md5(tweet_text.encode("utf-8")).hexdigest()
                    if tweet_key not in all_tweets:
                        all_tweets[tweet_key] = tweet_data
                except Exception:
                    continue

            # Cek konvergensi scroll: jika tidak ada tweet baru bertambah 4 putaran berturut-turut, hentikan
            current_total = len(all_tweets)
            if current_total == last_total_count and current_total > 0:
                consecutive_no_change += 1
                if consecutive_no_change >= 4:
                    log(f"    [i] Scroll adaptif: seluruh balasan termuat ({current_total} cuitan dikumpulkan).")
                    break
            else:
                consecutive_no_change = 0
                last_total_count = current_total

            # Gulir ke bawah
            page.evaluate("window.scrollBy(0, 1500)")
            time.sleep(2.0)

        if not all_tweets:
            log("    [-] Tidak ditemukan elemen cuitan (mungkin cuitan diproteksi, dihapus, atau memerlukan login).")
            return []

        # Fallback jika link status root tweet tidak terdeteksi spesifik:
        # cuitan pertama pada saat halaman baru dimuat adalah root tweet
        if root_tweet_info is None and all_tweets:
            root_tweet_info = list(all_tweets.values())[0]
            root_tweet_info["is_root"] = True

        root_text = root_tweet_info.get("text", "")
        root_author = root_tweet_info.get("author", "@user_anon")
        root_created_at = root_tweet_info.get("created_at", datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
        root_likes = root_tweet_info.get("like_count", 0)
        root_replies = root_tweet_info.get("reply_count", 0)

        items = []

        # 1. Simpan Cuitan Utama (Root Post: is_reply=0, parent_id="", parent_text="")
        items.append({
            "comment_id": f"TW_{raw_post_id}_000",
            "platform": "twitter",
            "search_keyword": search_keyword if search_keyword else "mental health mahasiswa",
            "author": root_author,
            "post_id": post_id_val,
            "post_title": root_text,
            "comment_text": root_text,
            "parent_id": "",
            "parent_text": "",
            "is_reply": 0,
            "created_at": root_created_at,
            "like_count": root_likes,
            "reply_count": root_replies,
            "emojis": self.extract_emojis(root_text),
            "has_capslock": self.detect_capslock(root_text),
            "is_sarcasm": "",
            "actual_sentiment": "",
            "topic_category": ""
        })

        # 2. Simpan Seluruh Balasan (Replies: is_reply=1, parent_id=post_id_val, parent_text=root_text)
        reply_idx = 1
        for key, tw in all_tweets.items():
            if tw.get("is_root"):
                continue

            # Hindari menduplikasi teks yang persis cuitan utama
            if tw.get("text") == root_text:
                continue

            comment_id = f"TW_{raw_post_id}_{reply_idx:03d}"
            reply_idx += 1

            reply_text = tw.get("text", "")
            items.append({
                "comment_id": comment_id,
                "platform": "twitter",
                "search_keyword": search_keyword if search_keyword else "mental health mahasiswa",
                "author": tw.get("author", "@user_anon"),
                "post_id": post_id_val,
                "post_title": root_text,
                "comment_text": reply_text,
                "parent_id": post_id_val,
                "parent_text": root_text,
                "is_reply": 1,
                "created_at": tw.get("created_at", datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")),
                "like_count": tw.get("like_count", 0),
                "reply_count": tw.get("reply_count", 0),
                "emojis": self.extract_emojis(reply_text),
                "has_capslock": self.detect_capslock(reply_text),
                "is_sarcasm": "",
                "actual_sentiment": "",
                "topic_category": ""
            })

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
        Menjalankan proses scraping bertahap (batch) pada daftar target URL X (Twitter)
        dengan persistent browser, auto-save per URL, cooldown antar-batch, dan anti-kehilangan data.
        """
        def log(msg):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)

        # Normalisasi target URLs
        normalized_targets = self.normalize_targets(targets)
        if not normalized_targets:
            log("[!] Tidak ada URL target X / Twitter yang valid.")
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

        log(f"[+] Memulai scraping {total_targets} URL target X dengan ukuran batch {batch_size}...")

        all_collected = []
        total_batches = (total_targets + batch_size - 1) // batch_size

        with sync_playwright() as p:
            context = self.setup_persistent_browser(p, headless=True)
            page = context.pages[0] if context.pages else context.new_page()

            for target_idx, url in enumerate(active_targets, 1):
                # Cek pembatalan oleh user via GUI
                if stop_event and stop_event.is_set():
                    log("\n[!] Scraping X / Twitter dihentikan oleh pengguna.")
                    break

                current_batch = ((target_idx - 1) // batch_size) + 1
                log(f"\n[{target_idx}/{total_targets}] Batch {current_batch}/{total_batches} -> {url}")

                records = self.scrape_url(page, url, log_func=log, search_keyword=search_keyword)
                if records:
                    all_collected.extend(records)
                    # AUTO-SAVE LANGSUNG KE CSV (Anti Data-Loss)
                    total_in_csv = self.save_records(records)
                    self.append_to_history(url)
                    log(f"    [✓] +{len(records)} cuitan/komentar diekstrak. Total dataset saat ini: {total_in_csv} baris.")
                else:
                    log("    [-] Tidak ada cuitan/komentar yang berhasil diambil dari URL ini.")

                # Kirim sinyal progress ke GUI
                if progress_callback:
                    progress_callback(target_idx, total_targets, len(all_collected))

                # Jeda cooldown antar-batch jika bukan target terakhir
                if target_idx % batch_size == 0 and target_idx < total_targets:
                    log(f"\n[⏸ Batch {current_batch} Selesai] Istirahat {cooldown} detik agar aman dari rate limit X...")
                    for s in range(cooldown):
                        if stop_event and stop_event.is_set():
                            break
                        time.sleep(1)
                else:
                    time.sleep(2.5)

            try:
                context.close()
            except Exception:
                pass

        log(f"\n[✓] Selesai! Berhasil mengumpulkan {len(all_collected)} data baru dari X (Twitter).")
        return all_collected
