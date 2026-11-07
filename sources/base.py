"""
Modul Base Scraper untuk Multi-Source Dataset Riset Kesehatan Mental
--------------------------------------------------------------------
Menyediakan skema kolom standar, utilitas ekstraksi teks (emoji, capslock,
anonimisasi ID etika riset UU PDP), dan penyimpanan incremental ke CSV.
"""

import os
import re
import hashlib
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
