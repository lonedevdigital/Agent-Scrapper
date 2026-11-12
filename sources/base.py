"""
Modul Base Scraper untuk Multi-Source Dataset Riset Kesehatan Mental
--------------------------------------------------------------------
Menyediakan skema kolom standar, utilitas ekstraksi teks (emoji, capslock,
anonimisasi ID etika riset UU PDP), dan penyimpanan incremental ke CSV.
"""

import os
import re
import hashlib
import subprocess
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable, Optional
import pandas as pd
import emoji

OUTPUT_CSV = "dataset_mental_health.csv"

COLUMNS = [
    "comment_id",
    "platform",
    "search_keyword",
    "author",
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

class BaseScraper(ABC):
    """Kelas dasar (Abstract Base Class) untuk seluruh sumber platform media sosial."""

    def __init__(self, platform_name: str, output_csv: str = OUTPUT_CSV):
        self.platform_name = platform_name
        self.output_csv = output_csv
        self.ensure_csv_exists()

    def ensure_csv_exists(self):
        """Memastikan file dataset CSV sudah ada dengan header standar."""
        if not os.path.exists(self.output_csv):
            df = pd.DataFrame(columns=COLUMNS)
            df.to_csv(self.output_csv, index=False, encoding="utf-8")

    @staticmethod
    def anonymize_id(text: str) -> str:
        """Mengubah username/ID asli menjadi kode hash anonim 8 karakter untuk etika UU PDP."""
        if not text:
            return "user_anon"
        return "user_" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]

    @staticmethod
    def extract_emojis(text: str) -> str:
        """Mengekstrak seluruh emoji yang ada di dalam teks."""
        if not text:
            return ""
        emojis_found = [c for c in text if c in emoji.EMOJI_DATA]
        return "".join(emojis_found)

    @staticmethod
    def detect_capslock(text: str) -> int:
        """Mendeteksi apakah terdapat kata berhuruf kapital penuh (indikasi penekanan/sarkasme)."""
        if not text:
            return 0
        words = re.findall(r"\b[A-Z]{3,}\b", text)
        return 1 if len(words) >= 1 else 0

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        """
        Menyimpan kumpulan record baru secara bertahap (incremental checkpoint).
        Otomatis menggabungkan dengan data yang ada dan menghapus duplikat.
        Mengembalikan jumlah total data di CSV saat ini.
        """
        if not records:
            return self.get_total_records()

        df_new = pd.DataFrame(records)
        for col in COLUMNS:
            if col not in df_new.columns:
                df_new[col] = ""
        df_new = df_new[COLUMNS]

        if os.path.exists(self.output_csv) and os.path.getsize(self.output_csv) > 0:
            try:
                df_existing = pd.read_csv(self.output_csv)
                for col in COLUMNS:
                    if col not in df_existing.columns:
                        df_existing[col] = ""
                df_existing = df_existing[COLUMNS]
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                df_combined.drop_duplicates(subset=["comment_id"], keep="first", inplace=True)
            except Exception:
                df_combined = df_new
        else:
            df_combined = df_new

        df_combined = df_combined[COLUMNS]
        try:
            df_combined.to_csv(self.output_csv, index=False, encoding="utf-8")
        except PermissionError:
            backup_csv = "dataset_mental_health_temp.csv"
            df_combined.to_csv(backup_csv, index=False, encoding="utf-8")
            print(f"[!] Perhatian: '{self.output_csv}' sedang dibuka oleh aplikasi lain (seperti Excel). Data tersimpan di '{backup_csv}'. Tutup Excel agar bisa disimpan ke file utama.")
        return len(df_combined)

    def get_total_records(self) -> int:
        """Mengambil total baris data yang ada di file CSV."""
        if os.path.exists(self.output_csv) and os.path.getsize(self.output_csv) > 0:
            try:
                df = pd.read_csv(self.output_csv)
                return len(df)
            except Exception:
                return 0
        return 0

    @abstractmethod
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
        """Metode abstrak untuk scraping secara batch dengan dukungan callback status & pembatalan."""
        pass


def auto_install_playwright_browsers(log_func: Optional[Callable[[str], None]] = None) -> bool:
    """
    Mengunduh dan memasang Chromium untuk Playwright secara otomatis jika
    tidak ditemukan browser lokal (Edge/Chrome).
    Dapat berjalan baik pada mode Python biasa maupun file executable (.exe) mandiri.
    """
    def log(msg):
        if log_func:
            log_func(msg)
        else:
            print(msg)

    log("[i] Memeriksa & mengunduh browser Chromium Playwright otomatis...")
    try:
        from playwright._impl._driver import compute_driver_executable
        driver_exec, driver_cli = compute_driver_executable()
        cmd = [driver_exec, driver_cli, "install", "chromium"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode == 0:
            log("[✓] Browser Chromium Playwright berhasil dipasang!")
            return True
        else:
            log(f"[!] Gagal memasang browser Playwright: {proc.stderr or proc.stdout}")
            return False
    except Exception as e:
        log(f"[!] Terjadi kesalahan saat auto-install Playwright: {e}")
        return False


def safe_launch_browser(
    playwright_instance,
    headless: bool = True,
    args: Optional[List[str]] = None,
    log_func: Optional[Callable[[str], None]] = None,
    **kwargs
):
    """
    Meluncurkan browser Chromium dengan urutan fallback cerdas:
    1. 'msedge' (Bawaan Windows 10/11 - langsung jalan tanpa download)
    2. 'chrome' (Google Chrome jika terpasang di sistem pengguna)
    3. None (Chromium Playwright jika sudah ada di sistem)
    4. Auto-install Chromium via driver internal Playwright jika belum ada browser sama sekali.
    """
    launch_args = args or [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox"
    ]

    base_kwargs = dict(kwargs)
    base_kwargs["headless"] = headless
    base_kwargs["args"] = launch_args

    # Coba channel browser bawaan terlebih dahulu (msedge diutamakan karena bawaan Windows)
    for channel in ["msedge", "chrome", None]:
        try:
            curr_kwargs = base_kwargs.copy()
            if channel:
                curr_kwargs["channel"] = channel
            browser = playwright_instance.chromium.launch(**curr_kwargs)
            if log_func and channel:
                log_func(f"[i] Menggunakan peramban sistem: {channel.upper()}")
            return browser
        except Exception:
            continue

    if log_func:
        log_func("[!] Browser lokal (Edge/Chrome) tidak ditemukan. Memasang Chromium Playwright otomatis...")
    auto_install_playwright_browsers(log_func=log_func)
    return playwright_instance.chromium.launch(**base_kwargs)


def safe_launch_persistent_context(
    playwright_instance,
    user_data_dir: str,
    headless: bool = True,
    args: Optional[List[str]] = None,
    log_func: Optional[Callable[[str], None]] = None,
    **kwargs
):
    """
    Meluncurkan persistent context Chromium dengan fallback bertingkat:
    msedge -> chrome -> default Playwright -> auto-install.
    """
    launch_args = args or [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox"
    ]

    base_kwargs = dict(kwargs)
    base_kwargs["user_data_dir"] = user_data_dir
    base_kwargs["headless"] = headless
    base_kwargs["args"] = launch_args

    for channel in ["msedge", "chrome", None]:
        try:
            curr_kwargs = base_kwargs.copy()
            if channel:
                curr_kwargs["channel"] = channel
            context = playwright_instance.chromium.launch_persistent_context(**curr_kwargs)
            if log_func and channel:
                log_func(f"[i] Menggunakan peramban sistem (persistent): {channel.upper()}")
            return context
        except Exception:
            continue

    if log_func:
        log_func("[!] Browser lokal (Edge/Chrome) tidak ditemukan. Memasang Chromium Playwright otomatis...")
    auto_install_playwright_browsers(log_func=log_func)
    return playwright_instance.chromium.launch_persistent_context(**base_kwargs)

