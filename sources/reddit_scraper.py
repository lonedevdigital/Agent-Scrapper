"""
Modul Scraper Reddit
--------------------
Sumber data keempat untuk mengambil postingan dan komentar/diskusi mendalam dari Reddit
(khususnya r/indonesia, r/mentalhealth, dll.) terkait riset dataset kesehatan mental.

Fitur:
- Dual-Mode Extraction: Direct JSON endpoint (sangat cepat, akurat, tanpa browser)
  dengan fallback otomatis ke Playwright Stealth Browser jika akses HTTP dibatasi/diblokir.
- Normalisasi URL (reddit.com/r/..., redd.it/..., old.reddit.com/...)
- Penanganan hierarki komentar bertingkat (root post, top-level comments, nested replies)
- Ekstraksi otomatis emoji, deteksi capslock, upvote score, dan timestamp UTC
- Pemrosesan batch dengan jeda cooldown dan auto-save bertahap ke dataset_mental_health.csv
- Filter URL yang sudah pernah di-scrape (target_sudah scrapping_reddit.txt)
"""

import os
import re
import json
import time
import ssl
import hashlib
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any, Callable, Optional

from sources.base import BaseScraper, OUTPUT_CSV

SESSION_FILE = "reddit_session.json"
HISTORY_FILE = "target_sudah scrapping_reddit.txt"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 "
    "(ResearchBot: MentalHealthDatasetCollector/1.0; Contact: student-research)"
)


class RedditScraper(BaseScraper):
    """
    Konektor scraper untuk mengumpulkan postingan dan komentar dari Reddit.
    Mendukung format tautan modern Reddit, old.reddit, maupun shortlink redd.it.
    """

    def __init__(
        self,
        output_csv: str = OUTPUT_CSV,
        session_file: str = SESSION_FILE,
        history_file: str = HISTORY_FILE
    ):
        super().__init__(platform_name="reddit", output_csv=output_csv)
        self.session_file = session_file
        self.history_file = history_file

    @staticmethod
    def normalize_targets(lines_or_text) -> List[str]:
        """
        Mengekstrak dan menormalisasi URL Reddit dari input teks atau list.
        Mendukung format bernomor ('1. https://...', '2) ...'), bullet ('- ...'),
        domain reddit.com, old.reddit.com, sh.reddit.com, maupun shortlink redd.it.
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

            # 1. Cek pola reddit.com dengan r/subreddit/comments/post_id
            match_sub = re.search(
                r"https?://(?:www\.|old\.|new\.|sh\.)?reddit\.com/r/([A-Za-z0-9_]+)/comments/([A-Za-z0-9]+)[^\s]*",
                cleaned
            )
            if match_sub:
                sub = match_sub.group(1)
                post_id = match_sub.group(2)
                targets.append(f"https://www.reddit.com/r/{sub}/comments/{post_id}/")
                continue

            # 2. Cek pola reddit.com/comments/post_id
            match_post = re.search(
                r"https?://(?:www\.|old\.|new\.|sh\.)?reddit\.com/comments/([A-Za-z0-9]+)[^\s]*",
                cleaned
            )
            if match_post:
                post_id = match_post.group(1)
                targets.append(f"https://www.reddit.com/comments/{post_id}/")
                continue

            # 3. Cek shortlink redd.it/post_id
            match_short = re.search(r"https?://(?:www\.)?redd\.it/([A-Za-z0-9]+)", cleaned)
            if match_short:
                post_id = match_short.group(1)
                targets.append(f"https://www.reddit.com/comments/{post_id}/")
                continue

            # 4. Fallback jika tanpa protokol https://
            match_no_proto = re.search(
                r"(?:www\.|old\.|new\.|sh\.)?reddit\.com/r/([A-Za-z0-9_]+)/comments/([A-Za-z0-9]+)[^\s]*",
                cleaned
            )
            if match_no_proto:
                sub = match_no_proto.group(1)
                post_id = match_no_proto.group(2)
                targets.append(f"https://www.reddit.com/r/{sub}/comments/{post_id}/")
                continue

            match_short_no_proto = re.search(r"(?:www\.)?redd\.it/([A-Za-z0-9]+)", cleaned)
            if match_short_no_proto:
                post_id = match_short_no_proto.group(1)
                targets.append(f"https://www.reddit.com/comments/{post_id}/")
                continue

        return targets

    def get_already_scraped_urls(self) -> set:
        """Membaca daftar URL yang sudah pernah di-scrape dari file riwayat."""
        if not os.path.exists(self.history_file):
            return set()
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return set(self.normalize_targets(lines))
        except Exception:
            return set()

    def append_to_history(self, url: str):
        """Mencatat URL yang sukses di-scrape ke file riwayat."""
        try:
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(f"\n{url}")
        except Exception:
            pass

    @staticmethod
    def parse_post_id(url: str) -> str:
        """Mengekstrak ID postingan dari URL Reddit."""
        match = re.search(r"/comments/([A-Za-z0-9]+)", url)
        if match:
            return match.group(1)
        match_short = re.search(r"redd\.it/([A-Za-z0-9]+)", url)
        if match_short:
            return match_short.group(1)
        return "RD_" + hashlib.md5(url.encode()).hexdigest()[:8]

    @staticmethod
    def parse_subreddit(url: str) -> Optional[str]:
        """Mengekstrak nama subreddit dari URL Reddit jika ada."""
        match = re.search(r"/r/([A-Za-z0-9_]+)/", url)
        return match.group(1) if match else None

    def fetch_reddit_json(self, post_id: str, subreddit: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Mengambil representasi JSON langsung dari endpoint publik Reddit.
        Sangat cepat dan tidak memerlukan rendering browser.
        """
        if subreddit:
            json_url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json?limit=500&raw_json=1"
        else:
            json_url = f"https://www.reddit.com/comments/{post_id}.json?limit=500&raw_json=1"

        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Cache-Control": "no-cache",
        }

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(json_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            if response.status == 200:
                raw_bytes = response.read()
                data = json.loads(raw_bytes.decode("utf-8", errors="ignore"))
                if isinstance(data, list) and len(data) >= 2:
                    return data
        return None

    def parse_json_response(
        self,
        data: List[Dict[str, Any]],
        post_id: str,
        search_keyword: str = "mental health"
    ) -> List[Dict[str, Any]]:
        """
        Mengurai payload JSON Reddit menjadi baris-baris dataset terstandarisasi.
        Mencakup postingan utama (root post) dan seluruh rantai komentar bertingkat.
        """
        records: List[Dict[str, Any]] = []

        # 1. Ekstraksi Postingan Utama (Listing Pertama)
        post_listing = data[0].get("data", {}).get("children", [])
        if not post_listing:
            return records

        post_data = post_listing[0].get("data", {})
        post_title = " ".join([l.strip() for l in str(post_data.get("title", "")).splitlines() if l.strip()])
        post_selftext = " ".join([l.strip() for l in str(post_data.get("selftext", "")).splitlines() if l.strip()])
        root_body = post_selftext if post_selftext else post_title

        author_raw = post_data.get("author", "user_anon")
        if not author_raw or author_raw in ["[deleted]", "[removed]"]:
            author = "user_anon"
        else:
            author = f"u/{author_raw}"

        created_utc = post_data.get("created_utc")
        created_iso = ""
        if created_utc:
            try:
                created_iso = datetime.fromtimestamp(float(created_utc), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                created_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            created_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        like_count = max(0, int(post_data.get("score", 0)))
        reply_count = int(post_data.get("num_comments", 0))

        # Simpan Record Postingan Utama
        root_record = {
            "comment_id": f"RD_{post_id}_root",
            "platform": "reddit",
            "search_keyword": search_keyword if search_keyword else "mental health",
            "author": author,
            "post_id": post_id,
            "post_title": post_title,
            "comment_text": root_body,
            "parent_id": "null",
            "parent_text": "null",
            "is_reply": 0,
            "created_at": created_iso,
            "like_count": like_count,
            "reply_count": reply_count,
            "emojis": self.extract_emojis(root_body),
            "has_capslock": self.detect_capslock(root_body),
            "is_sarcasm": "",
            "actual_sentiment": "",
            "topic_category": ""
        }
        records.append(root_record)

        # 2. Ekstraksi Pohon Komentar (Listing Kedua)
        comments_listing = data[1].get("data", {}).get("children", [])

        def traverse_comments(children: List[Dict[str, Any]], parent_id: str, parent_text: str):
            for child in children:
                if child.get("kind") != "t1":
                    continue
                c_data = child.get("data", {})
                c_id = c_data.get("id")
                raw_body = str(c_data.get("body", "")).strip()

                # Abaikan komentar yang telah dihapus atau kosong total
                if not raw_body or raw_body in ["[deleted]", "[removed]"]:
                    continue

                body = " ".join([l.strip() for l in raw_body.splitlines() if l.strip()])

                c_author_raw = c_data.get("author", "user_anon")
                if not c_author_raw or c_author_raw in ["[deleted]", "[removed]"]:
                    c_author = "user_anon"
                else:
                    c_author = f"u/{c_author_raw}"

                c_created = c_data.get("created_utc")
                c_time_iso = ""
                if c_created:
                    try:
                        c_time_iso = datetime.fromtimestamp(float(c_created), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    except Exception:
                        c_time_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                else:
                    c_time_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                replies_obj = c_data.get("replies")
                child_comments = []
                if isinstance(replies_obj, dict):
                    child_comments = replies_obj.get("data", {}).get("children", [])

                direct_replies_count = sum(1 for r in child_comments if r.get("kind") == "t1")
                comment_key = f"RD_{post_id}_{c_id}"

                records.append({
                    "comment_id": comment_key,
                    "platform": "reddit",
                    "search_keyword": search_keyword if search_keyword else "mental health",
                    "author": c_author,
                    "post_id": post_id,
                    "post_title": post_title,
                    "comment_text": body,
                    "parent_id": parent_id,
                    "parent_text": parent_text if parent_text else "null",
                    "is_reply": 1,
                    "created_at": c_time_iso,
                    "like_count": max(0, int(c_data.get("score", 0))),
                    "reply_count": direct_replies_count,
                    "emojis": self.extract_emojis(body),
                    "has_capslock": self.detect_capslock(body),
                    "is_sarcasm": "",
                    "actual_sentiment": "",
                    "topic_category": ""
                })

                if child_comments:
                    traverse_comments(child_comments, parent_id=comment_key, parent_text=body)

        traverse_comments(comments_listing, parent_id=post_id, parent_text=root_body)
        return records

    def setup_stealth_browser(self, playwright_instance, headless: bool = True):
        """Menyiapkan peramban Playwright dengan konfigurasi stealth anti-bot."""
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
                if browser:
                    break
            except Exception:
                continue

        if not browser:
            browser = playwright_instance.chromium.launch(headless=headless, args=launch_args)

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=DEFAULT_USER_AGENT,
            locale="id-ID"
        )
        return browser, context

    def scrape_with_playwright(
        self,
        page,
        url: str,
        search_keyword: str = "mental health",
        log_func: Optional[Callable[[str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Mengambil postingan dan komentar Reddit menggunakan peramban Playwright.
        Digunakan ketika direct HTTP diblokir oleh ISP / Cloudflare.
        """
        def log(m):
            if log_func:
                log_func(m)

        post_id = self.parse_post_id(url)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            # Tunggu elemen komentar Reddit terhidrasi di halaman
            try:
                page.wait_for_selector("shreddit-comment, [data-testid='comment'], .comment", timeout=12000)
            except Exception:
                pass

            # Scroll adaptif ke bawah untuk memicu lazy-loading seluruh rantai komentar
            last_count = 0
            for _ in range(4):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)
                current_elements = page.query_selector_all("shreddit-comment, [data-testid='comment'], .comment")
                if len(current_elements) > 0 and len(current_elements) == last_count:
                    break
                last_count = len(current_elements)
        except Exception as e:
            log(f"    [!] Browser Playwright gagal memuat '{url}': {e}")
            return []

        # Fallback: Scrape elemen DOM langsung (Shreddit / Modern Reddit / Old Reddit)
        records: List[Dict[str, Any]] = []
        try:
            # Ambil elemen post container jika ada (shreddit-post)
            post_elem = page.query_selector("shreddit-post")
            root_score = 0
            root_reply_count = 0
            root_author = "user_anon"

            if post_elem:
                try:
                    root_score = max(0, int(post_elem.get_attribute("score") or "0"))
                except Exception:
                    root_score = 0
                try:
                    root_reply_count = max(0, int(post_elem.get_attribute("comment-count") or "0"))
                except Exception:
                    root_reply_count = 0
                p_author = post_elem.get_attribute("author")
                if p_author and p_author not in ["[deleted]", "[dihapus]", "[removed]"]:
                    root_author = f"u/{p_author}"

            # Klik tombol expand jika terdapat teks yang diciutkan (read more / selengkapnya)
            try:
                expand_buttons = page.query_selector_all("button:has-text('Tampilkan selengkapnya'), button:has-text('Read more'), button:has-text('Selengkapnya')")
                for btn in expand_buttons:
                    try:
                        if btn.is_visible():
                            btn.click()
                            time.sleep(0.2)
                    except Exception:
                        pass
            except Exception:
                pass

            # Ambil judul
            title_elem = page.query_selector("h1, [slot='title'], [data-testid='post-title']")
            raw_title = title_elem.inner_text().strip() if title_elem else page.title().replace(" : r/", " - ")
            post_title = " ".join([l.strip() for l in raw_title.splitlines() if l.strip()])

            # Ambil teks postingan utama
            body_elem = page.query_selector("[slot='text-body'], div[data-click-id='text'], .usertext-body")
            raw_post_body = body_elem.inner_text().strip() if body_elem else post_title
            post_body = " ".join([l.strip() for l in raw_post_body.splitlines() if l.strip()])

            root_record = {
                "comment_id": f"RD_{post_id}_root",
                "platform": "reddit",
                "search_keyword": search_keyword if search_keyword else "mental health",
                "author": root_author,
                "post_id": post_id,
                "post_title": post_title,
                "comment_text": post_body,
                "parent_id": "null",
                "parent_text": "null",
                "is_reply": 0,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "like_count": root_score,
                "reply_count": root_reply_count,
                "emojis": self.extract_emojis(post_body),
                "has_capslock": self.detect_capslock(post_body),
                "is_sarcasm": "",
                "actual_sentiment": "",
                "topic_category": ""
            }
            records.append(root_record)

            # Ambil komentar melalui selector modern <shreddit-comment> atau .comment
            comment_elements = page.query_selector_all("shreddit-comment, [data-testid='comment'], .comment")
            comment_text_map = {}
            parsed_comments = []

            for idx, c_el in enumerate(comment_elements, 1):
                # Cari slot teks komentar murni tanpa header username / timestamp
                body_el = c_el.query_selector("div[slot='comment'], div[id*='-comment-rtjson-content'], div.md")
                if body_el:
                    raw_comment_text = body_el.inner_text().strip()
                else:
                    raw_comment_text = c_el.inner_text().strip()

                if not raw_comment_text or len(raw_comment_text) < 3:
                    continue

                clean_text = " ".join([l.strip() for l in raw_comment_text.splitlines() if l.strip()])

                # Ambil metadata dari atribut shreddit-comment jika ada
                thingid = c_el.get_attribute("thingid")
                parentid = c_el.get_attribute("parentid")
                author_val = c_el.get_attribute("author") or "user_anon"
                score_attr = c_el.get_attribute("score") or "0"

                if thingid:
                    c_id = thingid.replace("t1_", "")
                    comment_key = f"RD_{post_id}_{c_id}"
                else:
                    c_id = f"{idx:03d}"
                    comment_key = f"RD_{post_id}_{c_id}"

                comment_text_map[thingid if thingid else comment_key] = clean_text

                try:
                    score_val = max(0, int(score_attr))
                except Exception:
                    score_val = 0

                author_clean = f"u/{author_val}" if author_val not in ["user_anon", "[deleted]", "[dihapus]", "[removed]"] else "user_anon"

                parsed_comments.append({
                    "comment_key": comment_key,
                    "thingid": thingid,
                    "parentid": parentid,
                    "author": author_clean,
                    "clean_text": clean_text,
                    "score_val": score_val
                })

            # Hitung jumlah balasan langsung untuk tiap komentar
            parent_count_map = {}
            for pc in parsed_comments:
                pid = pc["parentid"]
                if pid:
                    parent_count_map[pid] = parent_count_map.get(pid, 0) + 1

            # Bangun record dataset lengkap dengan relasi parent_id dan parent_text utuh
            for pc in parsed_comments:
                raw_pid = pc["parentid"]
                if not raw_pid or raw_pid.startswith("t3_") or raw_pid in ["None", "null"]:
                    actual_parent_id = post_id
                    actual_parent_text = post_body
                else:
                    parent_c_id = raw_pid.replace("t1_", "")
                    actual_parent_id = f"RD_{post_id}_{parent_c_id}"
                    actual_parent_text = comment_text_map.get(raw_pid, post_body)

                direct_replies = parent_count_map.get(pc["thingid"], 0) if pc["thingid"] else 0

                records.append({
                    "comment_id": pc["comment_key"],
                    "platform": "reddit",
                    "search_keyword": search_keyword if search_keyword else "mental health",
                    "author": pc["author"],
                    "post_id": post_id,
                    "post_title": post_title,
                    "comment_text": pc["clean_text"],
                    "parent_id": actual_parent_id,
                    "parent_text": actual_parent_text,
                    "is_reply": 1,
                    "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "like_count": pc["score_val"],
                    "reply_count": direct_replies,
                    "emojis": self.extract_emojis(pc["clean_text"]),
                    "has_capslock": self.detect_capslock(pc["clean_text"]),
                    "is_sarcasm": "",
                    "actual_sentiment": "",
                    "topic_category": ""
                })
        except Exception as e:
            log(f"    [!] Error saat parsing DOM Reddit: {e}")

        return records

    def scrape_url(
        self,
        url: str,
        page=None,
        log_func: Optional[Callable[[str], None]] = None,
        search_keyword: str = "mental health"
    ) -> List[Dict[str, Any]]:
        """
        Mengekstrak satu URL Reddit.
        Jika page Playwright tersedia, langsung menggunakan browser Playwright Stealth
        untuk menghindari blokir bot/Cloudflare pada akses HTTP biasa.
        """
        def log(m):
            if log_func:
                log_func(m)

        post_id = self.parse_post_id(url)
        subreddit = self.parse_subreddit(url)

        # 1. Jika peramban Playwright aktif, gunakan Playwright langsung
        if page:
            return self.scrape_with_playwright(
                page=page,
                url=url,
                search_keyword=search_keyword,
                log_func=log_func
            )

        # 2. Mode fallback Direct HTTP jika tanpa browser
        try:
            data = self.fetch_reddit_json(post_id, subreddit)
            if data:
                records = self.parse_json_response(data, post_id, search_keyword=search_keyword)
                if records:
                    return records
        except Exception:
            pass

        return []

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
        Menjalankan proses scraping Reddit secara bertahap (batch) dengan auto-save
        ke CSV, jeda cooldown antar-batch, serta pencegahan kehilangan data.
        """
        def log(msg):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)

        # Normalisasi seluruh target URL
        normalized_targets = self.normalize_targets(targets)
        if not normalized_targets:
            log("[!] Tidak ada URL target Reddit yang valid dalam daftar.")
            return []

        # Filter URL yang sudah pernah di-scrape
        if skip_already_scraped:
            history = self.get_already_scraped_urls()
            active_targets = [u for u in normalized_targets if u not in history]
            skipped_count = len(normalized_targets) - len(active_targets)
            if skipped_count > 0:
                log(f"[i] Melewati {skipped_count} URL Reddit yang sudah pernah di-scrape sebelumnya.")
        else:
            active_targets = normalized_targets

        total_targets = len(active_targets)
        if total_targets == 0:
            log("[✓] Semua URL Reddit dalam daftar sudah pernah di-scrape!")
            return []

        log(f"[+] Memulai scraping {total_targets} URL Reddit dengan ukuran batch {batch_size}...")

        all_collected: List[Dict[str, Any]] = []
        total_batches = (total_targets + batch_size - 1) // batch_size

        # Inisialisasi Playwright secara opsional untuk URL yang butuh browser fallback
        playwright_obj = None
        browser = None
        context = None
        page = None

        try:
            from playwright.sync_api import sync_playwright
            playwright_mgr = sync_playwright()
            playwright_obj = playwright_mgr.start()
            browser, context = self.setup_stealth_browser(playwright_obj, headless=True)
            page = context.new_page()
        except Exception as pe:
            log(f"[i] Peramban Playwright tidak diaktifkan ({pe}). Menjalankan scraping mode Direct HTTP.")
            page = None

        try:
            for target_idx, url in enumerate(active_targets, 1):
                if stop_event and stop_event.is_set():
                    log("\n[!] Scraping Reddit dihentikan oleh pengguna.")
                    break

                current_batch = ((target_idx - 1) // batch_size) + 1
                log(f"\n[{target_idx}/{total_targets}] Batch {current_batch}/{total_batches} -> {url}")

                records = self.scrape_url(
                    url=url,
                    page=page,
                    log_func=log,
                    search_keyword=search_keyword
                )

                if records:
                    all_collected.extend(records)
                    total_in_csv = self.save_records(records)
                    self.append_to_history(url)
                    log(f"    [✓] +{len(records)} komentar diekstrak. Total dataset saat ini: {total_in_csv} baris.")
                else:
                    log(f"    [-] Tidak ada komentar yang berhasil diambil dari URL ini.")

                if progress_callback:
                    progress_callback(target_idx, total_targets, len(all_collected))

                # Cooldown antar-batch
                if target_idx % batch_size == 0 and target_idx < total_targets:
                    log(f"\n[⏸ Batch {current_batch} Selesai] Cooldown {cooldown} detik agar jaringan & API stabil...")
                    for _ in range(cooldown):
                        if stop_event and stop_event.is_set():
                            break
                        time.sleep(1)
                else:
                    time.sleep(2.0)

        finally:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            if playwright_obj:
                try:
                    playwright_obj.stop()
                except Exception:
                    pass

        log(f"\n[✓] Selesai! Berhasil mengumpulkan {len(all_collected)} data baru dari Reddit.")
        return all_collected

    def search_reddit_posts(
        self,
        keyword: str,
        subreddit: Optional[str] = "indonesia",
        limit: int = 25,
        callback: Optional[Callable[[str], None]] = None
    ) -> List[Dict[str, str]]:
        """
        Mencari postingan Reddit berdasarkan kata kunci (search_keyword).
        Dapat difokuskan pada subreddit tertentu (misal 'indonesia' atau 'mentalhealth').
        """
        def log(m):
            if callback:
                callback(m)

        encoded_kw = urllib.parse.quote(keyword)
        if subreddit:
            search_url = f"https://www.reddit.com/r/{subreddit}/search.json?q={encoded_kw}&restrict_sr=1&sort=relevance&limit={limit}&raw_json=1"
        else:
            search_url = f"https://www.reddit.com/search.json?q={encoded_kw}&sort=relevance&limit={limit}&raw_json=1"

        req = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json"
            }
        )

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        results = []
        try:
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                    children = data.get("data", {}).get("children", [])
                    for child in children:
                        item = child.get("data", {})
                        p_id = item.get("id")
                        title = item.get("title", "")
                        sub = item.get("subreddit", "")
                        permalink = item.get("permalink", "")
                        full_url = f"https://www.reddit.com{permalink}" if permalink else f"https://www.reddit.com/r/{sub}/comments/{p_id}/"

                        results.append({
                            "id": p_id,
                            "title": title,
                            "url": full_url,
                            "score": str(item.get("score", 0)),
                            "num_comments": str(item.get("num_comments", 0)),
                            "subreddit": sub,
                            "text_snippet": item.get("selftext", "")[:120].replace("\n", " ")
                        })
                    log(f"[✓] Ditemukan {len(results)} postingan Reddit untuk kata kunci '{keyword}'.")
        except Exception as e:
            log(f"[!] Gagal mencari di Reddit: {e}")

        return results
