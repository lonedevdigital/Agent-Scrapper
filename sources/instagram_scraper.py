"""
Modul Scraper Instagram
-----------------------
Mengambil postingan dan komentar Instagram (Reels & Posts):
- Ekstraksi caption dan username pembuat sebagai Postingan Utama (Root Post)
- Penanganan modal login otomatis (bypass modal dialog)
- Pengambilan komentar dan balasan bertahap (Load more comments)
- Ekstraksi waktu ISO asli dari tag <time> (YYYY-MM-DDTHH:MM:SSZ)
- Sanitasi teks, deteksi capslock, ekstraksi emoji unicode asli
- Auto-save bertahap (incremental checkpoint) ke dataset_mental_health.csv
"""

import os
import re
import time
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Callable, Optional
from playwright.sync_api import sync_playwright

from sources.base import BaseScraper, OUTPUT_CSV

HISTORY_FILE = "target_sudah scrapping_instagram.txt"
TARGETS_FILE = "targets_instagram.txt"

class InstagramScraper(BaseScraper):
    def __init__(self, output_csv: str = OUTPUT_CSV):
        super().__init__(platform_name="instagram", output_csv=output_csv)
        self.history_file = HISTORY_FILE
        self.targets_file = TARGETS_FILE

    @staticmethod
    def normalize_targets(lines_or_text) -> List[str]:
        """
        Mengekstrak dan menormalisasi URL Instagram (Reels, Posts, IGTV) dari teks input.
        Membersihkan parameter query string seperti ?utm_source=...
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

            match = re.search(r"https?://(?:www\.)?instagram\.com/(?:reel|p|tv)/([A-Za-z0-9_-]+)", cleaned)
            if match:
                shortcode = match.group(1)
                targets.append(f"https://www.instagram.com/reel/{shortcode}/")

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
        """Mengekstrak shortcode postingan/reel Instagram."""
        match = re.search(r"instagram\.com/(?:reel|p|tv)/([A-Za-z0-9_-]+)", url)
        if match:
            return match.group(1)
        return "IG_" + hashlib.md5(url.encode()).hexdigest()[:8]

    @staticmethod
    def parse_metric_number(val_str: str) -> int:
        """Mengubah format angka teks metrik (cth: '1,5 rb', '2.5K', '450') menjadi integer."""
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
        max_load_clicks: int = 15,
        log_func: Optional[Callable[[str], None]] = None,
        search_keyword: str = "mental health"
    ) -> List[Dict[str, Any]]:
        """
        Membuka satu URL Instagram Reel/Post dan mengekstrak postingan utama beserta komentarnya.
        """
        def log(m):
            if log_func:
                log_func(m)

        raw_shortcode = self.parse_post_id(url)
        post_id_val = f"IG_{raw_shortcode}"

        # Buka URL Instagram
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
                    log("    [!] Gagal memuat URL Instagram setelah 2 percobaan.")
                    return []

        time.sleep(3.5)

        # Tutup dialog login jika muncul
        try:
            close_btn = page.query_selector('div[role="dialog"] [aria-label="Close"], svg[aria-label="Close"]')
            if close_btn:
                close_btn.click(timeout=1500)
                time.sleep(1.0)
            else:
                page.evaluate("""() => {
                    const d = document.querySelector('div[role="dialog"]');
                    if (d && d.parentElement) d.parentElement.remove();
                    document.body.style.overflow = 'auto';
                }""")
        except Exception:
            pass

        # 1. Ekstrak Root Post (Caption, Author, Timestamp)
        root_data = page.evaluate("""
            () => {
                const ogTitle = document.querySelector('meta[property="og:title"]')?.content || '';
                const ogDesc = document.querySelector('meta[property="og:description"]')?.content || '';
                
                // Cari username penulis
                let author = '';
                const mTitle = ogTitle.match(/^(.*?)\\s+on Instagram/i);
                if (mTitle) {
                    author = mTitle[1].trim();
                } else {
                    const mDesc = ogDesc.match(/- @([a-zA-Z0-9_\\.]+)/);
                    if (mDesc) author = mDesc[1].trim();
                }
                
                // Cari timestamp postingan utama
                const timeEl = document.querySelector('time');
                const datetime = timeEl ? timeEl.getAttribute('datetime') : '';
                
                // Cari teks caption
                const h1 = document.querySelector('h1');
                let caption = h1 ? h1.innerText.trim() : '';
                if (!caption && ogDesc) {
                    caption = ogDesc.split(' - @')[0].trim();
                }
                
                return {
                    author: author || 'user_anon',
                    caption: caption || ogTitle || 'Instagram Post',
                    datetime
                };
            }
        """)

        author_raw = root_data.get("author", "user_anon")
        author_val = f"@{author_raw.lstrip('@')}" if author_raw else "@user_anon"

        caption_raw = root_data.get("caption", "Instagram Post")
        clean_caption = re.sub(r"[\r\n]+", " ", caption_raw).strip()
        clean_caption = re.sub(r"\s{2,}", " ", clean_caption)

        dt_raw = root_data.get("datetime", "")
        if dt_raw:
            root_created_at = re.sub(r"\.\d+Z$", "Z", dt_raw)
        else:
            root_created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 2. Muat komentar lanjutan secara berulang (Load more comments)
        consecutive_no_change = 0
        last_comments_count = 0

        for round_idx in range(max_load_clicks):
            # Coba klik tombol 'Load more comments'
            try:
                load_more = page.query_selector('svg[aria-label="Load more comments"], button:has-text("Load more comments"), div[role="button"]:has-text("Load more comments")')
                if load_more:
                    page.evaluate("(el) => el.closest('div[role=\"button\"], button, div').click()", load_more)
                    time.sleep(1.8)
                else:
                    # Scroll ke bawah di kolom komentar
                    page.evaluate("window.scrollBy(0, 800)")
                    time.sleep(1.5)
            except Exception:
                pass

        # 3. Ekstrak seluruh elemen komentar dari DOM
        raw_comments = page.evaluate("""
            () => {
                const results = [];
                // Identifikasi tombol Reply / Balas sebagai penanda blok komentar
                const replyBtns = Array.from(document.querySelectorAll('div[role="button"], span, button')).filter(
                    el => el.children.length === 0 && (el.innerText.trim() === 'Reply' || el.innerText.trim() === 'Balas')
                );
                
                const seen = new Set();
                replyBtns.forEach(btn => {
                    let container = btn;
                    for (let i = 0; i < 4; i++) {
                        if (container.parentElement) container = container.parentElement;
                    }
                    
                    const timeEl = container.querySelector('time');
                    const isoTime = timeEl ? timeEl.getAttribute('datetime') : '';
                    
                    const rawText = container.innerText.trim();
                    const lines = rawText.split('\\n').map(l => l.trim()).filter(l => l && l !== '\\xa0');
                    if (lines.length >= 3) {
                        const author = lines[0];
                        if (['Like', 'Reply', 'Balas', 'Suka'].includes(author)) return;
                        
                        // Ekstrak teks komentar murni
                        const contentLines = lines.slice(1).filter(l => 
                            !['Like', 'Reply', 'Balas', 'Suka', 'Edited', 'Diedit'].includes(l) && 
                            !/^\\d+[wdhms]$/.test(l) &&
                            !/^\\d+\\s*(?:likes?|suka)$/i.test(l)
                        );
                        const text = contentLines.join(' ');
                        
                        // Deteksi like count pada baris
                        let likes = 0;
                        lines.forEach(l => {
                            const m = l.match(/(\\d+(?:[,\\.]\\d+)?\\s*(?:rb|k)?)\\s*(?:likes?|suka)/i);
                            if (m) likes = m[1];
                        });
                        
                        const key = author + ':' + text;
                        if (!seen.has(key) && text.length > 0) {
                            seen.add(key);
                            results.push({ author, text, isoTime, likes });
                        }
                    }
                });
                return results;
            }
        """)

        items = []

        # 1. Postingan Utama (Root Post: is_reply=0, parent_id="", parent_text="")
        items.append({
            "comment_id": f"IG_{raw_shortcode}_000",
            "platform": "instagram",
            "search_keyword": search_keyword if search_keyword else "mental health",
            "author": author_val,
            "post_id": post_id_val,
            "post_title": clean_caption,
            "comment_text": clean_caption,
            "parent_id": "",
            "parent_text": "",
            "is_reply": 0,
            "created_at": root_created_at,
            "like_count": 0,
            "reply_count": len(raw_comments),
            "emojis": self.extract_emojis(clean_caption),
            "has_capslock": self.detect_capslock(clean_caption),
            "is_sarcasm": "",
            "actual_sentiment": "",
            "topic_category": ""
        })

        # 2. Komentar Balasan (Replies: is_reply=1, parent_id=post_id_val, parent_text=clean_caption)
        reply_idx = 1
        for c in raw_comments:
            c_text = c.get("text", "")
            c_clean = re.sub(r"[\r\n]+", " ", c_text).strip()
            c_clean = re.sub(r"\s{2,}", " ", c_clean)

            if not c_clean or len(c_clean) < 2:
                continue

            comment_id = f"IG_{raw_shortcode}_{reply_idx:03d}"
            reply_idx += 1

            c_author_raw = c.get("author", "user_anon")
            c_author = f"@{c_author_raw.lstrip('@')}"

            c_time_raw = c.get("isoTime", "")
            if c_time_raw:
                c_created_at = re.sub(r"\.\d+Z$", "Z", c_time_raw)
            else:
                c_created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            items.append({
                "comment_id": comment_id,
                "platform": "instagram",
                "search_keyword": search_keyword if search_keyword else "mental health",
                "author": c_author,
                "post_id": post_id_val,
                "post_title": clean_caption,
                "comment_text": c_clean,
                "parent_id": post_id_val,
                "parent_text": clean_caption,
                "is_reply": 1,
                "created_at": c_created_at,
                "like_count": self.parse_metric_number(str(c.get("likes", 0))),
                "reply_count": 0,
                "emojis": self.extract_emojis(c_clean),
                "has_capslock": self.detect_capslock(c_clean),
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
        """Menjalankan proses scraping bertahap (batch) pada daftar target Instagram."""
        def log(msg):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)

        normalized_targets = self.normalize_targets(targets)
        if not normalized_targets:
            log("[!] Tidak ada URL target Instagram yang valid.")
            return []

        if skip_already_scraped:
            history = self.get_already_scraped_urls()
            active_targets = [u for u in normalized_targets if u not in history]
            skipped_count = len(normalized_targets) - len(active_targets)
            if skipped_count > 0:
                log(f"[i] Melewati {skipped_count} URL Instagram yang sudah pernah di-scrape sebelumnya.")
        else:
            active_targets = normalized_targets

        total_targets = len(active_targets)
        if total_targets == 0:
            log("[✓] Semua URL Instagram dalam daftar target sudah pernah di-scrape!")
            return []

        log(f"[+] Memulai scraping {total_targets} URL target Instagram dengan ukuran batch {batch_size}...")

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
                    log("\n[!] Scraping Instagram dihentikan oleh pengguna.")
                    break

                current_batch = ((target_idx - 1) // batch_size) + 1
                log(f"\n[{target_idx}/{total_targets}] Batch {current_batch}/{total_batches} -> {url}")

                records = self.scrape_url(page, url, log_func=log, search_keyword=search_keyword)
                if records:
                    all_collected.extend(records)
                    total_in_csv = self.save_records(records)
                    self.append_to_history(url)
                    log(f"    [✓] +{len(records)} baris diekstrak. Total dataset saat ini: {total_in_csv} baris.")
                else:
                    log("    [-] Tidak ada komentar yang berhasil diambil dari URL ini.")

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

        log(f"\n[✓] Selesai! Berhasil mengumpulkan {len(all_collected)} data baru dari Instagram.")
        return all_collected

