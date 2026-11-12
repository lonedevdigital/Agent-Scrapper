"""
Modul Scraper YouTube
---------------------
Mengambil data video edukasi/pembahasan beserta komentar & balasannya dari YouTube:
- Mengambil judul dan deskripsi video sebagai Postingan Utama (Root Post)
- Mengambil komentar pengguna (ytd-comment-view-model & ytd-comment-thread-renderer)
- Konversi waktu relatif ke ISO UTC timestamp (YYYY-MM-DDTHH:MM:SSZ)
- Ekstraksi emoji, metrik suka (likes), capslock detector, dan pembersihan spasi/newline
- Penyimpanan bertahap (incremental checkpoint) ke dataset_mental_health.csv
"""

import os
import re
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Callable, Optional
from playwright.sync_api import sync_playwright

from sources.base import BaseScraper, OUTPUT_CSV

HISTORY_FILE = "target_sudah scrapping_youtube.txt"
TARGETS_FILE = "targets_youtube.txt"

class YouTubeScraper(BaseScraper):
    def __init__(self, output_csv: str = OUTPUT_CSV):
        super().__init__(platform_name="youtube", output_csv=output_csv)
        self.history_file = HISTORY_FILE
        self.targets_file = TARGETS_FILE

    @staticmethod
    def normalize_targets(lines_or_text) -> List[str]:
        """
        Mengekstrak dan menormalisasi URL YouTube dari teks input.
        Mendukung format watch (youtube.com/watch?v=...), share link (youtu.be/...),
        dan shorts (youtube.com/shorts/...).
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

            # Standard watch link
            m_watch = re.search(r"https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})", cleaned)
            if m_watch:
                targets.append(f"https://www.youtube.com/watch?v={m_watch.group(1)}")
                continue

            # Short link youtu.be
            m_short = re.search(r"https?://youtu\.be/([a-zA-Z0-9_-]{11})", cleaned)
            if m_short:
                targets.append(f"https://www.youtube.com/watch?v={m_short.group(1)}")
                continue

            # Shorts link
            m_shorts = re.search(r"https?://(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})", cleaned)
            if m_shorts:
                targets.append(f"https://www.youtube.com/watch?v={m_shorts.group(1)}")
                continue

            # Live stream link youtube.com/live/...
            m_live = re.search(r"https?://(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})", cleaned)
            if m_live:
                targets.append(f"https://www.youtube.com/watch?v={m_live.group(1)}")
                continue

            # Embed link youtube.com/embed/...
            m_embed = re.search(r"https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})", cleaned)
            if m_embed:
                targets.append(f"https://www.youtube.com/watch?v={m_embed.group(1)}")
                continue

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
        """Mengekstrak YouTube Video ID (11 karakter)."""
        m = re.search(r"(?:v=|youtu\.be/|shorts/|live/|embed/)([a-zA-Z0-9_-]{11})", url)
        if m:
            return m.group(1)
        return "YT_" + hashlib.md5(url.encode()).hexdigest()[:8]

    @staticmethod
    def parse_metric_number(val_str: str) -> int:
        """Mengubah format metrik teks (cth: '2,9 rb', '1.5K', '230', '1.2M') menjadi integer."""
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
    def relative_time_to_iso(time_str: str) -> str:
        """Mengonversi teks waktu relatif YouTube ke ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ)."""
        now = datetime.now(timezone.utc)
        if not time_str:
            return now.strftime("%Y-%m-%dT%H:%M:%SZ")

        text = time_str.lower().strip()
        m = re.search(r"(\d+)", text)
        qty = int(m.group(1)) if m else 1

        delta = timedelta()
        if any(k in text for k in ["detik", "second", "sec"]):
            delta = timedelta(seconds=qty)
        elif any(k in text for k in ["menit", "minute", "min"]):
            delta = timedelta(minutes=qty)
        elif any(k in text for k in ["jam", "hour", "hr"]):
            delta = timedelta(hours=qty)
        elif any(k in text for k in ["hari", "day"]):
            delta = timedelta(days=qty)
        elif any(k in text for k in ["minggu", "week", "wk"]):
            delta = timedelta(weeks=qty)
        elif any(k in text for k in ["bulan", "month", "mo"]):
            delta = timedelta(days=qty * 30)
        elif any(k in text for k in ["tahun", "year", "yr"]):
            delta = timedelta(days=qty * 365)

        approx_time = now - delta
        return approx_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def scrape_url(
        self,
        page,
        url: str,
        max_scrolls: int = 20,
        log_func: Optional[Callable[[str], None]] = None,
        search_keyword: str = "mental health"
    ) -> List[Dict[str, Any]]:
        """
        Membuka satu URL YouTube Video dan mengekstrak video info (root) beserta seluruh komentar.
        """
        def log(m):
            if log_func:
                log_func(m)

        raw_video_id = self.parse_post_id(url)
        post_id_val = f"YT_{raw_video_id}"

        # Buka video YouTube
        loaded = False
        for attempt in range(1, 3):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                loaded = True
                break
            except Exception as e:
                if attempt == 1:
                    log(f"    [!] Percobaan 1 gagal: {e}. Mencoba ulang...")
                    time.sleep(3)
                else:
                    log("    [!] Gagal memuat URL YouTube setelah 2 percobaan.")
                    return []

        time.sleep(3.5)

        # 1. Ekstrak Metadata Video (Root Post)
        root_data = page.evaluate("""
            () => {
                const titleEl = document.querySelector('h1.ytd-watch-metadata yt-formatted-string') || document.querySelector('h1.title');
                const title = titleEl ? titleEl.innerText.trim() : document.title.replace(' - YouTube', '').trim();
                
                const channelEl = document.querySelector('#owner #channel-name a') || document.querySelector('ytd-channel-name a');
                const channel = channelEl ? channelEl.innerText.trim() : '';
                const channelHandle = document.querySelector('#owner a[href*="/@"]')?.getAttribute('href')?.replace('/', '') || (channel ? '@' + channel.replace(/\\s+/g, '') : '@channel_anon');
                
                const uploadDate = document.querySelector('meta[itemprop="uploadDate"]')?.content || '';
                const descEl = document.querySelector('#description-inline-expander') || document.querySelector('#description');
                const desc = descEl ? descEl.innerText.trim() : '';
                
                return {
                    title: title || 'YouTube Video',
                    author: channelHandle.startsWith('@') ? channelHandle : '@' + channelHandle,
                    uploadDate,
                    desc
                };
            }
        """)

        video_title = root_data.get("title", "YouTube Video")
        video_author = root_data.get("author", "@channel_anon")
        upload_date = root_data.get("uploadDate", "")
        if upload_date:
            upload_date = re.sub(r"\.\d+Z$", "Z", upload_date)
            # Format timezone +07:00 or -07:00 to Z if needed
            if "T" in upload_date and ("+" in upload_date or "-" in upload_date[10:]):
                try:
                    dt = datetime.fromisoformat(upload_date)
                    upload_date = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                except Exception:
                    pass
        if not upload_date:
            upload_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        video_desc = root_data.get("desc", "")
        # Buat root comment_text gabungan judul dan deskripsi ringkas
        root_text = video_title
        if video_desc:
            cleaned_desc = re.sub(r"[\r\n]+", " ", video_desc).strip()
            root_text = f"{video_title} - {cleaned_desc[:300]}"

        # 2. Scroll ke bagian komentar
        page.evaluate("window.scrollTo(0, 650)")
        time.sleep(2.5)

        all_comments = {}
        consecutive_no_change = 0
        last_total_count = 0

        for scroll_round in range(max_scrolls):
            # Klik 'Lihat balasan' / 'balasan' jika ada
            try:
                reply_buttons = page.query_selector_all('#more-replies, button[aria-label*="balasan"], button[aria-label*="replies"]')
                for b in reply_buttons[:3]:
                    try:
                        b.click(timeout=800)
                        time.sleep(0.5)
                    except Exception:
                        pass
            except Exception:
                pass

            # Ekstrak komentar dari DOM (mendukung desain modern ytd-comment-view-model)
            comments_extracted = page.evaluate("""
                () => {
                    const results = [];
                    const vms = Array.from(document.querySelectorAll('#comments ytd-comment-view-model'));
                    vms.forEach(vm => {
                        const authorEl = vm.querySelector('#author-text span, #author-text, a#author-text');
                        const author = authorEl ? authorEl.innerText.trim() : '@user_anon';
                        
                        const textEl = vm.querySelector('#content-text');
                        const text = textEl ? textEl.innerText.trim() : '';
                        
                        const likeEl = vm.querySelector('#vote-count-middle');
                        const likes = likeEl ? likeEl.innerText.trim() : '0';
                        
                        const timeEl = vm.querySelector('.published-time-text a, #published-time-text a');
                        const timeStr = timeEl ? timeEl.innerText.trim() : '';
                        
                        if (text && text.length > 1) {
                            results.push({ author, text, likes, timeStr });
                        }
                    });
                    return results;
                }
            """)

            for c in comments_extracted:
                c_text = c.get("text", "")
                c_text_clean = re.sub(r"[\r\n]+", " ", c_text).strip()
                c_text_clean = re.sub(r"\s{2,}", " ", c_text_clean)

                if not c_text_clean or len(c_text_clean) < 2:
                    continue

                # Kunci unik: hash dari author + teks
                c_author = c.get("author", "@user_anon")
                if not c_author.startswith("@"):
                    c_author = f"@{c_author}"

                c_key = hashlib.md5(f"{c_author}:{c_text_clean}".encode("utf-8")).hexdigest()
                if c_key not in all_comments:
                    all_comments[c_key] = {
                        "author": c_author,
                        "text": c_text_clean,
                        "likes": self.parse_metric_number(c.get("likes", "0")),
                        "created_at": self.relative_time_to_iso(c.get("timeStr", ""))
                    }

            current_total = len(all_comments)
            if current_total == last_total_count and current_total > 0:
                consecutive_no_change += 1
                if consecutive_no_change >= 4:
                    log(f"    [i] Selesai scrolling YouTube: {current_total} komentar dikumpulkan.")
                    break
            else:
                consecutive_no_change = 0
                last_total_count = current_total

            page.evaluate("window.scrollBy(0, 1800)")
            time.sleep(2.0)

        items = []

        # 1. Postingan Utama (Root Video: is_reply=0, parent_id="", parent_text="")
        items.append({
            "comment_id": f"YT_{raw_video_id}_000",
            "platform": "youtube",
            "search_keyword": search_keyword if search_keyword else "mental health",
            "author": video_author,
            "post_id": post_id_val,
            "post_title": video_title,
            "comment_text": root_text,
            "parent_id": "",
            "parent_text": "",
            "is_reply": 0,
            "created_at": upload_date,
            "like_count": 0,
            "reply_count": len(all_comments),
            "emojis": self.extract_emojis(root_text),
            "has_capslock": self.detect_capslock(root_text),
            "is_sarcasm": "",
            "actual_sentiment": "",
            "topic_category": ""
        })

        # 2. Komentar Pengguna (Replies: is_reply=1, parent_id=post_id_val, parent_text=video_title)
        reply_idx = 1
        for k, c in all_comments.items():
            comment_id = f"YT_{raw_video_id}_{reply_idx:03d}"
            reply_idx += 1

            comment_text = c["text"]
            items.append({
                "comment_id": comment_id,
                "platform": "youtube",
                "search_keyword": search_keyword if search_keyword else "mental health",
                "author": c["author"],
                "post_id": post_id_val,
                "post_title": video_title,
                "comment_text": comment_text,
                "parent_id": post_id_val,
                "parent_text": video_title,
                "is_reply": 1,
                "created_at": c["created_at"],
                "like_count": c["likes"],
                "reply_count": 0,
                "emojis": self.extract_emojis(comment_text),
                "has_capslock": self.detect_capslock(comment_text),
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
        """Menjalankan proses scraping bertahap (batch) pada daftar target video YouTube."""
        def log(msg):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)

        normalized_targets = self.normalize_targets(targets)
        if not normalized_targets:
            log("[!] Tidak ada URL target YouTube yang valid.")
            return []

        if skip_already_scraped:
            history = self.get_already_scraped_urls()
            active_targets = [u for u in normalized_targets if u not in history]
            skipped_count = len(normalized_targets) - len(active_targets)
            if skipped_count > 0:
                log(f"[i] Melewati {skipped_count} video YouTube yang sudah pernah di-scrape sebelumnya.")
        else:
            active_targets = normalized_targets

        total_targets = len(active_targets)
        if total_targets == 0:
            log("[✓] Semua video YouTube dalam daftar target sudah pernah di-scrape!")
            return []

        log(f"[+] Memulai scraping {total_targets} video YouTube dengan ukuran batch {batch_size}...")

        all_collected = []
        total_batches = (total_targets + batch_size - 1) // batch_size

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            for target_idx, url in enumerate(active_targets, 1):
                if stop_event and stop_event.is_set():
                    log("\n[!] Scraping YouTube dihentikan oleh pengguna.")
                    break

                current_batch = ((target_idx - 1) // batch_size) + 1
                log(f"\n[{target_idx}/{total_targets}] Batch {current_batch}/{total_batches} -> {url}")

                records = self.scrape_url(page, url, log_func=log, search_keyword=search_keyword)
                if records:
                    all_collected.extend(records)
                    total_in_csv = self.save_records(records)
                    self.append_to_history(url)
                    log(f"    [✓] +{len(records)} komentar diekstrak. Total dataset saat ini: {total_in_csv} baris.")
                else:
                    log("    [-] Tidak ada komentar yang berhasil diambil dari video ini.")

                if progress_callback:
                    progress_callback(target_idx, total_targets, len(all_collected))

                if target_idx % batch_size == 0 and target_idx < total_targets:
                    log(f"\n[⏸ Batch {current_batch} Selesai] Cooldown {cooldown} detik...")
                    for _ in range(cooldown):
                        if stop_event and stop_event.is_set():
                            break
                        time.sleep(1)
                else:
                    time.sleep(2.5)

            try:
                browser.close()
            except Exception:
                pass

        log(f"\n[✓] Selesai! Berhasil mengumpulkan {len(all_collected)} data baru dari YouTube.")
        return all_collected
