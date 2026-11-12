"""
Modul GUI Utama Aplikasi Scraper Dataset Kesehatan Mental
---------------------------------------------------------
Dibangun menggunakan CustomTkinter dengan dukungan multi-source (Threads, X, YouTube, Reddit),
sistem batch, auto-save checkpoint, dan live console logging.
"""

import os
import sys
import json
import threading
import subprocess
import webbrowser
import re
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
import pandas as pd
import customtkinter as ctk

from sources.threads_scraper import ThreadsScraper
from sources.twitter_scraper import TwitterScraper
from sources.youtube_scraper import YouTubeScraper
from sources.reddit_scraper import RedditScraper
from sources.instagram_scraper import InstagramScraper
from sources.base import OUTPUT_CSV

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class ThreadsSearchPreviewDialog(ctk.CTkToplevel):
    """
    Jendela dialog pratinjau hasil pencarian Threads dengan fitur:
    - Paginasi kartu hasil pencarian (paging per halaman)
    - Checkbox seleksi interaktif yang konsisten antar-halaman
    - Cuplikan isi teks utas utama & tautan ke postingan
    - Tombol 'Muat Halaman Berikutnya dari Threads' untuk mengambil halaman lanjutan
    - Sekali klik langsung memasukkan postingan terpilih ke antrean scraping utama
    """
    def __init__(self, parent, keyword: str, initial_results: List[Dict[str, str]], scraper: ThreadsScraper):
        super().__init__(parent)
        self.parent = parent
        self.keyword = keyword
        self.scraper = scraper
        self.results = list(initial_results)

        # Kumpulan URL yang dicentang (default: semua dicentang)
        self.selected_urls = {item["url"] for item in self.results}

        # Konfigurasi Paging
        self.items_per_page = 5
        self.current_page = 1

        self.title(f"🔍 Pratinjau Hasil Pencarian Threads: '{self.keyword}'")
        self.geometry("880x680")
        self.minsize(760, 560)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_ui()
        self._render_current_page()

        self.lift()
        self.focus_force()
        self.grab_set()

    def _build_ui(self):
        # 1. Header Frame
        self.header_frame = ctk.CTkFrame(self, corner_radius=8)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 8))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.lbl_title = ctk.CTkLabel(
            self.header_frame,
            text=f"🔍 Hasil Pencarian Threads: \"{self.keyword}\"",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_title.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 2))

        self.lbl_subtitle = ctk.CTkLabel(
            self.header_frame,
            text=f"Total {len(self.results)} utas ditemukan. Pilih postingan yang relevan untuk di-scrape komentarnya.",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.lbl_subtitle.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 10))

        # 2. Toolbar Seleksi
        self.toolbar_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.toolbar_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 6))

        self.btn_select_page = ctk.CTkButton(
            self.toolbar_frame,
            text="✓ Centang Halaman Ini",
            width=140,
            height=26,
            font=ctk.CTkFont(size=11),
            command=self._select_current_page
        )
        self.btn_select_page.pack(side="left", padx=(0, 6))

        self.btn_select_all = ctk.CTkButton(
            self.toolbar_frame,
            text="✓ Centang Semua Utas",
            width=135,
            height=26,
            font=ctk.CTkFont(size=11),
            command=self._select_all_global
        )
        self.btn_select_all.pack(side="left", padx=(0, 6))

        self.btn_deselect_all = ctk.CTkButton(
            self.toolbar_frame,
            text="✕ Hapus Centang",
            width=115,
            height=26,
            fg_color="#475569",
            hover_color="#334155",
            font=ctk.CTkFont(size=11),
            command=self._deselect_all
        )
        self.btn_deselect_all.pack(side="left", padx=(0, 15))

        self.lbl_counter = ctk.CTkLabel(
            self.toolbar_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#4ade80"
        )
        self.lbl_counter.pack(side="right")

        # 3. Area List Scrollable
        self.scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=8)
        self.scroll_frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 8))
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # 4. Baris Paging
        self.paging_frame = ctk.CTkFrame(self, corner_radius=8)
        self.paging_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.paging_frame.grid_columnconfigure(1, weight=1)

        self.btn_prev = ctk.CTkButton(
            self.paging_frame,
            text="◀ Sebelumnya",
            width=110,
            height=28,
            command=self._prev_page
        )
        self.btn_prev.grid(row=0, column=0, padx=10, pady=8)

        self.lbl_page_info = ctk.CTkLabel(
            self.paging_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_page_info.grid(row=0, column=1, padx=10, pady=8)

        self.btn_next = ctk.CTkButton(
            self.paging_frame,
            text="Selanjutnya ▶",
            width=110,
            height=28,
            command=self._next_page
        )
        self.btn_next.grid(row=0, column=2, padx=10, pady=8)

        self.btn_fetch_more = ctk.CTkButton(
            self.paging_frame,
            text="🔄 Muat Halaman Berikutnya dari Threads",
            width=230,
            height=28,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._fetch_more_from_threads
        )
        self.btn_fetch_more.grid(row=0, column=3, padx=(10, 10), pady=8)

        # 5. Tombol Aksi Bawah
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 15))

        self.btn_cancel = ctk.CTkButton(
            self.bottom_frame,
            text="Batal",
            width=100,
            height=32,
            fg_color="#475569",
            hover_color="#334155",
            command=self.destroy
        )
        self.btn_cancel.pack(side="left")

        self.btn_apply = ctk.CTkButton(
            self.bottom_frame,
            text="📥 Masukkan ke Antrean Scraping",
            width=240,
            height=32,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._apply_selected
        )
        self.btn_apply.pack(side="right")

    @property
    def total_pages(self) -> int:
        if not self.results:
            return 1
        return (len(self.results) + self.items_per_page - 1) // self.items_per_page

    def _update_counter_label(self):
        sel_count = len(self.selected_urls)
        tot_count = len(self.results)
        self.lbl_counter.configure(text=f"Terpilih: {sel_count} dari {tot_count} utas")
        if hasattr(self, "btn_apply"):
            self.btn_apply.configure(text=f"📥 Masukkan ke Target Scraping ({sel_count} Dipilih)")

    def _render_current_page(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not self.results:
            empty_lbl = ctk.CTkLabel(
                self.scroll_frame,
                text="Tidak ada postingan yang ditemukan.",
                font=ctk.CTkFont(size=13),
                text_color="gray"
            )
            empty_lbl.pack(pady=40)
            self.btn_prev.configure(state="disabled")
            self.btn_next.configure(state="disabled")
            self.lbl_page_info.configure(text="Halaman 0 dari 0")
            return

        tot_pages = self.total_pages
        if self.current_page > tot_pages:
            self.current_page = tot_pages
        if self.current_page < 1:
            self.current_page = 1

        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.results))
        page_items = self.results[start_idx:end_idx]

        self.btn_prev.configure(state="normal" if self.current_page > 1 else "disabled")
        self.btn_next.configure(state="normal" if self.current_page < tot_pages else "disabled")
        self.lbl_page_info.configure(
            text=f"Halaman {self.current_page} dari {tot_pages}  (Menampilkan #{start_idx+1}-#{end_idx} dari {len(self.results)})"
        )

        for idx, item in enumerate(page_items, start=start_idx + 1):
            url = item["url"]
            is_checked = (url in self.selected_urls)

            card = ctk.CTkFrame(self.scroll_frame, corner_radius=8)
            card.pack(fill="x", padx=5, pady=5)

            card_top = ctk.CTkFrame(card, fg_color="transparent")
            card_top.pack(fill="x", padx=10, pady=(8, 4))

            var = ctk.BooleanVar(value=is_checked)
            chk = ctk.CTkCheckBox(
                card_top,
                text=f"#{idx}  {item['author']}",
                font=ctk.CTkFont(size=12, weight="bold"),
                variable=var,
                command=lambda u=url, v=var: self._toggle_selection(u, v)
            )
            chk.pack(side="left")

            btn_link = ctk.CTkButton(
                card_top,
                text="🔗 Buka Link",
                width=85,
                height=22,
                font=ctk.CTkFont(size=11),
                fg_color="#334155",
                hover_color="#475569",
                command=lambda u=url: webbrowser.open(u)
            )
            btn_link.pack(side="right")

            snippet_text = item.get("snippet", "").strip()
            lbl_snip = ctk.CTkLabel(
                card,
                text=snippet_text,
                font=ctk.CTkFont(size=12),
                wraplength=760,
                justify="left"
            )
            lbl_snip.pack(fill="x", padx=12, pady=(0, 4), anchor="w")

            lbl_url = ctk.CTkLabel(
                card,
                text=url,
                font=ctk.CTkFont(size=10),
                text_color="gray",
                anchor="w"
            )
            lbl_url.pack(fill="x", padx=12, pady=(0, 8), anchor="w")

        self._update_counter_label()

    def _toggle_selection(self, url: str, var: ctk.BooleanVar):
        if var.get():
            self.selected_urls.add(url)
        else:
            self.selected_urls.discard(url)
        self._update_counter_label()

    def _select_current_page(self):
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.results))
        for item in self.results[start_idx:end_idx]:
            self.selected_urls.add(item["url"])
        self._render_current_page()

    def _select_all_global(self):
        for item in self.results:
            self.selected_urls.add(item["url"])
        self._render_current_page()

    def _deselect_all(self):
        self.selected_urls.clear()
        self._render_current_page()

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._render_current_page()

    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._render_current_page()

    def _fetch_more_from_threads(self):
        self.btn_fetch_more.configure(state="disabled", text="⏳ Mengambil...")

        def fetch_worker():
            try:
                existing = {r["url"] for r in self.results}
                more_posts = self.scraper.search_threads_posts(
                    keyword=self.keyword,
                    max_scrolls=5,
                    existing_urls=existing,
                    callback=self.parent.log_message
                )

                def update_ui():
                    self.btn_fetch_more.configure(state="normal", text="🔄 Muat Halaman Berikutnya dari Threads")
                    if more_posts:
                        added_count = 0
                        for p in more_posts:
                            if p["url"] not in existing:
                                self.results.append(p)
                                self.selected_urls.add(p["url"])
                                existing.add(p["url"])
                                added_count += 1
                        self.lbl_subtitle.configure(
                            text=f"Total {len(self.results)} utas ditemukan. Pilih postingan yang relevan untuk di-scrape komentarnya."
                        )
                        self.current_page = self.total_pages
                        self._render_current_page()
                        self.parent.log_message(f"[Pratinjau] Bertambah {added_count} utas baru dari Threads.")
                    else:
                        self.parent.log_message("[Pratinjau] Tidak ada utas tambahan baru yang ditemukan.")

                self.after(0, update_ui)
            except Exception as e:
                def update_err():
                    self.btn_fetch_more.configure(state="normal", text="🔄 Muat Halaman Berikutnya dari Threads")
                    self.parent.log_message(f"[!] Error saat mengambil lebih banyak: {e}")
                self.after(0, update_err)

        threading.Thread(target=fetch_worker, daemon=True).start()

    def _apply_selected(self):
        if not self.selected_urls:
            self.parent.log_message("[!] Tidak ada utas yang dipilih.")
            self.destroy()
            return

        ordered_selected = [r["url"] for r in self.results if r["url"] in self.selected_urls]

        current_text = self.parent.url_textbox.get("1.0", "end").strip()
        current_lines = [l.strip() for l in current_text.splitlines() if l.strip()]

        existing_urls_set = set(self.parent.scrapers["Threads (Utama)"].normalize_targets(current_lines))
        new_urls = [u for u in ordered_selected if u not in existing_urls_set]

        if current_text:
            if new_urls:
                combined_text = current_text + "\n" + "\n".join(new_urls)
            else:
                combined_text = current_text
        else:
            combined_text = "\n".join(ordered_selected)

        self.parent.url_textbox.delete("1.0", "end")
        self.parent.url_textbox.insert("1.0", combined_text.strip())

        self.parent.log_message(
            f"[Pratinjau] Berhasil menambahkan {len(new_urls)} target URL Threads baru ke antrean (Keyword: '{self.keyword}')."
        )
        self.destroy()


class TwitterAuthTokenDialog(ctk.CTkToplevel):
    """
    Modal dialog untuk memasukkan cookie auth_token dari peramban fisik (Chrome/Edge),
    sehingga terbebas dari kendala verifikasi bot di form login web X.
    """
    def __init__(self, parent, scraper: TwitterScraper):
        super().__init__(parent)
        self.parent = parent
        self.scraper = scraper

        self.title("🔑 Set Cookie Login X (auth_token)")
        self.geometry("640x370")
        self.minsize(580, 340)
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)

        self._build_ui()

        self.lift()
        self.focus_force()
        self.grab_set()

    def _build_ui(self):
        # Card Utama
        self.card = ctk.CTkFrame(self, corner_radius=10)
        self.card.pack(fill="both", expand=True, padx=20, pady=20)
        self.card.grid_columnconfigure(0, weight=1)

        # Header
        self.lbl_title = ctk.CTkLabel(
            self.card,
            text="🔑 Masukkan Cookie auth_token X (Twitter)",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_title.pack(anchor="w", padx=20, pady=(15, 4))

        self.lbl_desc = ctk.CTkLabel(
            self.card,
            text="Metode ini 100% melewati verifikasi keamanan dan tombol macet pada form X.\nSalin nilai cookie 'auth_token' dari browser Chrome/Edge yang sudah login X di laptop Anda.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            justify="left"
        )
        self.lbl_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Input Entry
        self.lbl_entry = ctk.CTkLabel(
            self.card,
            text="Nilai Cookie (auth_token):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_entry.pack(anchor="w", padx=20, pady=(0, 4))

        self.entry_token = ctk.CTkEntry(
            self.card,
            placeholder_text="Tempelkan kode auth_token di sini (40 karakter)...",
            height=34,
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.entry_token.pack(fill="x", padx=20, pady=(0, 10))

        # Coba isi dari file twitter_session.json jika sudah ada
        if os.path.exists(self.scraper.session_file):
            try:
                with open(self.scraper.session_file, "r", encoding="utf-8") as f:
                    s_data = json.load(f)
                for c in s_data.get("cookies", []):
                    if c.get("name") == "auth_token":
                        self.entry_token.insert(0, c.get("value", ""))
                        break
            except Exception:
                pass

        # Tips bantuan
        self.lbl_tips = ctk.CTkLabel(
            self.card,
            text="💡 Cara ambil: Di Chrome, tekan F12 > Tab Application > Cookies > x.com > copy baris auth_token",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.lbl_tips.pack(anchor="w", padx=20, pady=(0, 15))

        # Tombol-tombol Aksi
        self.btn_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.btn_cancel = ctk.CTkButton(
            self.btn_frame,
            text="Batal",
            width=90,
            height=32,
            fg_color="#475569",
            hover_color="#334155",
            command=self.destroy
        )
        self.btn_cancel.pack(side="left")

        self.btn_save = ctk.CTkButton(
            self.btn_frame,
            text="💾 Simpan & Verifikasi Login",
            width=210,
            height=32,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_save
        )
        self.btn_save.pack(side="right")

        self.btn_manual_browser = ctk.CTkButton(
            self.btn_frame,
            text="🌐 Buka Browser X",
            width=140,
            height=32,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=12),
            command=self._on_open_browser
        )
        self.btn_manual_browser.pack(side="right", padx=(0, 10))

    def _on_save(self):
        raw_val = self.entry_token.get().strip()
        token_val = raw_val
        # Bersihkan jika user menempelkan format seperti 'auth_token  ff353d...'
        if "auth_token" in token_val:
            parts = token_val.replace("auth_token", "").replace("=", "").replace(":", "").replace("\t", " ").strip()
            if parts:
                token_val = parts.split()[0]

        if not token_val:
            self.parent.log_message("[!] Harap tempelkan kode auth_token terlebih dahulu.")
            return

        self.btn_save.configure(state="disabled", text="⏳ Memverifikasi...")
        self.btn_manual_browser.configure(state="disabled")

        def worker():
            success = self.scraper.save_auth_token_session(token_val, callback=self.parent.log_message)

            def done():
                self.btn_save.configure(state="normal", text="💾 Simpan & Verifikasi Login")
                self.btn_manual_browser.configure(state="normal")
                if success:
                    self.parent.log_message("[✓] Sesi X (Twitter) aktif dan siap digunakan untuk scraping!")
                    self.destroy()

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_open_browser(self):
        self.destroy()
        self.parent._run_browser_login(self.scraper)


class DataCleaningDialog(ctk.CTkToplevel):
    """
    Modal dialog untuk membersihkan dataset teks kesehatan mental dari noise artefak scraper:
    - Menghapus artefak tombol medsos (Threads, X, Reddit, YT)
    - Menghapus username dan tanggal yang menempel di awal komentar
    - Menghapus duplikasi komentar (deduplikasi)
    - Memfilter komentar kosong atau terlalu pendek (< 10 karakter)
    - Menyimpan ke dataset_mental_health_cleaned.csv agar data asli tetap aman
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("🧹 Pembersih & Preprocessing Dataset (Data Cleaning)")
        self.geometry("640x530")
        self.minsize(580, 480)
        self.resizable(False, False)

        self.input_file = OUTPUT_CSV
        self.output_file = "dataset_mental_health_cleaned.csv"

        self._build_ui()

        self.lift()
        self.focus_force()
        self.grab_set()

    def _build_ui(self):
        self.card = ctk.CTkFrame(self, corner_radius=10)
        self.card.pack(fill="both", expand=True, padx=20, pady=20)
        self.card.grid_columnconfigure(0, weight=1)

        # Header
        self.lbl_title = ctk.CTkLabel(
            self.card,
            text="🧹 Pembersih & Normalisasi Dataset Riset",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_title.pack(padx=20, pady=(15, 5))

        self.lbl_desc = ctk.CTkLabel(
            self.card,
            text="Membersihkan artefak tombol medsos, metadata tanggal/author di awal teks,\n"
                 "menghapus duplikasi, dan membuang baris teks bising agar siap dilatih AI.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            justify="center"
        )
        self.lbl_desc.pack(padx=20, pady=(0, 15))

        # Info File Box
        self.file_info_frame = ctk.CTkFrame(self.card, fg_color="#1e293b", corner_radius=8)
        self.file_info_frame.pack(fill="x", padx=20, pady=(0, 12))

        self.lbl_in_file = ctk.CTkLabel(
            self.file_info_frame,
            text=f"📂 File Sumber: {self.input_file}",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        self.lbl_in_file.pack(fill="x", padx=15, pady=(8, 2))

        self.lbl_out_file = ctk.CTkLabel(
            self.file_info_frame,
            text=f"💾 File Hasil Bersih: {self.output_file} (Aman, file mentah asli tidak hilang)",
            font=ctk.CTkFont(size=11),
            text_color="#4ade80",
            anchor="w"
        )
        self.lbl_out_file.pack(fill="x", padx=15, pady=(0, 8))

        # Checkbox Opsi Cleaning
        self.options_frame = ctk.CTkFrame(self.card, fg_color="#0f172a", corner_radius=8)
        self.options_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.opt_clean_ui = ctk.CTkCheckBox(
            self.options_frame,
            text="Bersihkan artefak tombol medsos ('Lihat aktivitas', 'Terjemahkan', dsb.)",
            font=ctk.CTkFont(size=12)
        )
        self.opt_clean_ui.select()
        self.opt_clean_ui.pack(anchor="w", padx=15, pady=(10, 4))

        self.opt_clean_header = ctk.CTkCheckBox(
            self.options_frame,
            text="Bersihkan nama author & tanggal nempel di awal komentar",
            font=ctk.CTkFont(size=12)
        )
        self.opt_clean_header.select()
        self.opt_clean_header.pack(anchor="w", padx=15, pady=4)

        self.opt_dedup = ctk.CTkCheckBox(
            self.options_frame,
            text="Hapus komentar kembar / duplikat (Deduplikasi teks identik)",
            font=ctk.CTkFont(size=12)
        )
        self.opt_dedup.select()
        self.opt_dedup.pack(anchor="w", padx=15, pady=4)

        self.opt_filter_short = ctk.CTkCheckBox(
            self.options_frame,
            text="Filter teks kosong atau terlalu pendek (< 10 karakter / angka doang)",
            font=ctk.CTkFont(size=12)
        )
        self.opt_filter_short.select()
        self.opt_filter_short.pack(anchor="w", padx=15, pady=(4, 10))

        # Status & Progress Area
        self.status_label = ctk.CTkLabel(
            self.card,
            text="Siap membersihkan dataset.",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e2e8f0"
        )
        self.status_label.pack(padx=20, pady=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(self.card)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 15))
        self.progress_bar.set(0)

        # Tombol Aksi Bawah
        self.btn_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=20, pady=(5, 10))

        self.btn_cancel = ctk.CTkButton(
            self.btn_frame,
            text="Tutup",
            width=100,
            height=34,
            fg_color="#475569",
            hover_color="#334155",
            command=self.destroy
        )
        self.btn_cancel.pack(side="left")

        self.btn_start = ctk.CTkButton(
            self.btn_frame,
            text="🚀 Mulai Bersihkan Dataset",
            width=220,
            height=34,
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_start_cleaning
        )
        self.btn_start.pack(side="right")

        self.btn_open_cleaned = ctk.CTkButton(
            self.btn_frame,
            text="📊 Buka File Bersih",
            width=150,
            height=34,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=12),
            state="disabled",
            command=self._open_cleaned_file
        )
        self.btn_open_cleaned.pack(side="right", padx=(0, 10))

    def _open_cleaned_file(self):
        if os.path.exists(self.output_file):
            try:
                os.startfile(self.output_file)
            except Exception as e:
                self.parent.log_message(f"[!] Gagal membuka file bersih: {e}")

    def _clean_text_record(self, text: str, clean_ui: bool, clean_header: bool) -> str:
        if not isinstance(text, str):
            return ""
        t = text
        if clean_header:
            t = re.sub(r'^[a-zA-Z0-9._-]+\s+\d{1,2}/\d{1,2}/\d{4}(\s*·\s*Pembuat)?\s*', '', t)
        if clean_ui:
            t = re.sub(r'[\d,.]+\s*(rb|k|jt)?\s*[\d\s]*Populer\s+Lihat aktivitas.*$', '', t, flags=re.IGNORECASE)
            t = re.sub(r'Populer\s+Lihat aktivitas.*$', '', t, flags=re.IGNORECASE)
            t = re.sub(r'Lihat aktivitas.*$', '', t, flags=re.IGNORECASE)
            t = re.sub(r'Balas ke\s+[a-zA-Z0-9._-]+(\.{3})?.*$', '', t, flags=re.IGNORECASE)
            t = re.sub(r'Terjemahkan(\s+\d+)*', '', t, flags=re.IGNORECASE)
            t = re.sub(r'\s+\d+(\s+\d+)*$', '', t)
            t = re.sub(r'https?://\S+|www\.\S+', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def _on_start_cleaning(self):
        if not os.path.exists(self.input_file):
            self.status_label.configure(text=f"File '{self.input_file}' tidak ditemukan!", text_color="#ef4444")
            self.parent.log_message(f"[!] Error: File '{self.input_file}' belum ditemukan.")
            return

        self.btn_start.configure(state="disabled", text="⏳ Sedang Membersihkan...")
        self.btn_cancel.configure(state="disabled")
        self.progress_bar.set(0.2)
        self.status_label.configure(text="Membaca dataset...", text_color="#38bdf8")

        def worker():
            try:
                self.parent.log_message(f"[Cleaning] Memulai proses pembersihan pada '{self.input_file}'...")
                df = pd.read_csv(self.input_file)
                total_raw = len(df)
                self.parent.log_message(f"[Cleaning] Total data mentah awal: {total_raw:,} baris.")

                self.progress_bar.set(0.4)
                clean_ui = bool(self.opt_clean_ui.get())
                clean_header = bool(self.opt_clean_header.get())
                do_dedup = bool(self.opt_dedup.get())
                do_filter_short = bool(self.opt_filter_short.get())

                if "comment_text" in df.columns:
                    df["comment_text"] = df["comment_text"].apply(
                        lambda t: self._clean_text_record(t, clean_ui, clean_header)
                    )

                self.progress_bar.set(0.6)

                # Filter teks pendek / kosong
                if do_filter_short and "comment_text" in df.columns:
                    df = df[df["comment_text"].str.len() >= 10].copy()
                after_filter = len(df)

                self.progress_bar.set(0.8)

                # Deduplikasi
                if do_dedup and "comment_text" in df.columns:
                    df = df.drop_duplicates(subset=["comment_text"]).copy()
                total_clean = len(df)

                # Simpan ke CSV
                df.to_csv(self.output_file, index=False, encoding="utf-8")
                self.progress_bar.set(1.0)

                removed_short = total_raw - after_filter
                removed_dups = after_filter - total_clean

                msg_summary = (
                    f"[Cleaning] ✓ Selesai! {total_raw:,} baris -> {total_clean:,} baris bersih tersimpan di '{self.output_file}'.\n"
                    f"           (Dibuang: {removed_short} data pendek/noise, {removed_dups} duplikat identik)"
                )
                self.parent.log_message(msg_summary)

                def done():
                    self.status_label.configure(
                        text=f"✓ Selesai! Tersimpan {total_clean:,} baris bersih di '{self.output_file}'.",
                        text_color="#4ade80"
                    )
                    self.btn_start.configure(state="normal", text="🚀 Bersihkan Ulang")
                    self.btn_cancel.configure(state="normal")
                    self.btn_open_cleaned.configure(state="normal")
                    self.parent._update_total_records_display()

                self.after(0, done)

            except Exception as e:
                err_msg = f"[!] Gagal membersihkan dataset: {e}"
                self.parent.log_message(err_msg)
                def fail():
                    self.status_label.configure(text=f"Gagal: {e}", text_color="#ef4444")
                    self.btn_start.configure(state="normal", text="🚀 Coba Lagi")
                    self.btn_cancel.configure(state="normal")
                self.after(0, fail)

        threading.Thread(target=worker, daemon=True).start()


class ScraperApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Mental Health Research Dataset Collector v2.0.1")
        self.geometry("1060x740")
        self.minsize(920, 620)

        # Inisialisasi sumber scraper
        self.scrapers = {
            "Threads (Utama)": ThreadsScraper(),
            "X / Twitter (Kedua)": TwitterScraper(),
            "YouTube (Ketiga)": YouTubeScraper(),
            "Reddit (Keempat)": RedditScraper(),
            "Instagram (Kelima)": InstagramScraper()
        }
        self.current_platform = "Threads (Utama)"
        self.worker_thread = None
        self.stop_event = threading.Event()

        self._build_ui()
        self._update_total_records_display()

    def _build_ui(self):
        # Layout 2 Kolom: Sidebar Kiri (Navigasi) & Konten Kanan (Utama)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # SIDEBAR KIRI
        # ==========================================
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="🧠 Mental Health\nData Collector v2.0.1",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 15))

        # Pilihan Platform (Multi-Source)
        self.platform_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="PILIH SUMBER DATA:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray"
        )
        self.platform_label.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")

        self.platform_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["Threads (Utama)", "X / Twitter (Kedua)", "YouTube (Ketiga)", "Reddit (Keempat)", "Instagram (Kelima)"],
            command=self._on_platform_change
        )
        self.platform_menu.set(self.current_platform)
        self.platform_menu.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")

        # Kartu Statistik Dataset
        self.stats_card = ctk.CTkFrame(self.sidebar_frame, corner_radius=8)
        self.stats_card.grid(row=3, column=0, padx=15, pady=10, sticky="ew")

        self.stats_title = ctk.CTkLabel(
            self.stats_card,
            text="TOTAL DATASET",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="gray"
        )
        self.stats_title.pack(padx=10, pady=(10, 0))

        self.stats_value = ctk.CTkLabel(
            self.stats_card,
            text="0 Baris",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#4ade80"
        )
        self.stats_value.pack(padx=10, pady=(0, 10))

        # Tombol Aksi File
        self.btn_open_csv = ctk.CTkButton(
            self.sidebar_frame,
            text="📊 Buka File Dataset CSV",
            fg_color="#334155",
            hover_color="#475569",
            command=self._open_csv_file
        )
        self.btn_open_csv.grid(row=4, column=0, padx=20, pady=6, sticky="ew")

        self.btn_clean_data = ctk.CTkButton(
            self.sidebar_frame,
            text="🧹 Bersihkan Dataset (Cleaning)",
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._open_cleaning_dialog
        )
        self.btn_clean_data.grid(row=5, column=0, padx=20, pady=6, sticky="ew")

        self.btn_open_folder = ctk.CTkButton(
            self.sidebar_frame,
            text="📁 Buka Folder Kerja",
            fg_color="#334155",
            hover_color="#475569",
            command=self._open_work_dir
        )
        self.btn_open_folder.grid(row=6, column=0, padx=20, pady=6, sticky="ew")

        # Tombol Login Sesi
        self.btn_login = ctk.CTkButton(
            self.sidebar_frame,
            text="🔑 Login Akun Threads",
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self._start_login
        )
        self.btn_login.grid(row=7, column=0, padx=20, pady=(15, 6), sticky="ew")

        # Pengaturan Tampilan Tema
        self.theme_label = ctk.CTkLabel(self.sidebar_frame, text="Tema:", text_color="gray")
        self.theme_label.grid(row=9, column=0, padx=20, pady=(10, 0), sticky="w")
        self.theme_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["Dark", "Light", "System"],
            command=ctk.set_appearance_mode
        )
        self.theme_menu.grid(row=10, column=0, padx=20, pady=(0, 20), sticky="ew")

        # ==========================================
        # KONTEN UTAMA (KANAN)
        # ==========================================
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=15)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

        # Header Platform Info
        self.header_frame = ctk.CTkFrame(self.main_frame, corner_radius=8)
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.header_title = ctk.CTkLabel(
            self.header_frame,
            text="Platform: Threads (Meta)",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.header_title.pack(side="left", padx=15, pady=10)

        self.header_desc = ctk.CTkLabel(
            self.header_frame,
            text="Sumber Utama: Curhat personal naratif & respons interaksi kesehatan mental.",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self.header_desc.pack(side="left", padx=10, pady=10)

        # Area Input URL / Target
        self.input_card = ctk.CTkFrame(self.main_frame, corner_radius=8)
        self.input_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.input_header_frame = ctk.CTkFrame(self.input_card, fg_color="transparent")
        self.input_header_frame.pack(fill="x", padx=15, pady=(10, 5))

        self.input_title = ctk.CTkLabel(
            self.input_header_frame,
            text="Daftar Target URL (Mendukung format bernomor '1. ', '2. ', atau link langsung):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.input_title.pack(side="left")

        self.btn_load_file = ctk.CTkButton(
            self.input_header_frame,
            text="📥 Muat dari targets_threads.txt",
            width=180,
            height=26,
            font=ctk.CTkFont(size=11),
            command=self._load_from_targets_file
        )
        self.btn_load_file.pack(side="right", padx=(5, 0))

        self.btn_clear_input = ctk.CTkButton(
            self.input_header_frame,
            text="🗑 Bersihkan",
            width=80,
            height=26,
            fg_color="#ef4444",
            hover_color="#dc2626",
            font=ctk.CTkFont(size=11),
            command=self._clear_input_text
        )
        self.btn_clear_input.pack(side="right")

        # Frame Input Keyword Pencarian Dinamis
        self.keyword_frame = ctk.CTkFrame(self.input_card, fg_color="transparent")
        self.keyword_frame.pack(fill="x", padx=15, pady=(5, 4))

        self.lbl_keyword = ctk.CTkLabel(
            self.keyword_frame,
            text="🔍 Kata Kunci (search_keyword):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_keyword.pack(side="left", padx=(0, 8))

        # Muat keyword terakhir yang tersimpan jika ada
        default_kw = "mental health"
        self.keyword_file = "last_keyword.txt"
        if os.path.exists(self.keyword_file):
            try:
                with open(self.keyword_file, "r", encoding="utf-8") as f:
                    saved_kw = f.read().strip()
                    if saved_kw:
                        default_kw = saved_kw
            except Exception:
                pass

        self.active_keyword = default_kw

        self.entry_keyword = ctk.CTkEntry(
            self.keyword_frame,
            placeholder_text="Ketik keyword dinamis (misal: depresi, anxiety, burnout)...",
            height=30
        )
        self.entry_keyword.insert(0, default_kw)
        self.entry_keyword.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_keyword.bind("<Return>", lambda event: self._save_active_keyword())

        self.btn_save_keyword = ctk.CTkButton(
            self.keyword_frame,
            text="💾 Simpan Keyword",
            width=135,
            height=30,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_active_keyword
        )
        self.btn_save_keyword.pack(side="left", padx=(0, 8))

        self.btn_search_preview = ctk.CTkButton(
            self.keyword_frame,
            text="🔍 Cari di Threads",
            width=140,
            height=30,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_search_threads_preview
        )
        self.btn_search_preview.pack(side="right")

        # Baris Indikator Status Keyword Aktif
        self.keyword_status_frame = ctk.CTkFrame(self.input_card, fg_color="transparent")
        self.keyword_status_frame.pack(fill="x", padx=15, pady=(0, 6))

        self.lbl_keyword_status = ctk.CTkLabel(
            self.keyword_status_frame,
            text=f"✓ Keyword Aktif: '{default_kw}' (Tersimpan & siap untuk scraping)",
            font=ctk.CTkFont(size=11),
            text_color="#4ade80"
        )
        self.lbl_keyword_status.pack(side="left")

        self.url_textbox = ctk.CTkTextbox(self.input_card, height=110, font=ctk.CTkFont(size=12))
        self.url_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # Panel Pengaturan Batch & Kontrol Mulai
        self.controls_card = ctk.CTkFrame(self.main_frame, corner_radius=8)
        self.controls_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.controls_card.grid_columnconfigure(5, weight=1)

        # Batch Size Setting
        self.lbl_batch = ctk.CTkLabel(self.controls_card, text="Ukuran Batch:")
        self.lbl_batch.grid(row=0, column=0, padx=(15, 5), pady=12)
        self.opt_batch = ctk.CTkOptionMenu(
            self.controls_card,
            values=["3 URL", "5 URL (Rekomendasi)", "10 URL", "15 URL"],
            width=140
        )
        self.opt_batch.set("5 URL (Rekomendasi)")
        self.opt_batch.grid(row=0, column=1, padx=(0, 15), pady=12)

        # Cooldown Setting
        self.lbl_cooldown = ctk.CTkLabel(self.controls_card, text="Jeda Antar-Batch:")
        self.lbl_cooldown.grid(row=0, column=2, padx=(5, 5), pady=12)
        self.opt_cooldown = ctk.CTkOptionMenu(
            self.controls_card,
            values=["5 Detik", "10 Detik (Aman)", "15 Detik", "20 Detik"],
            width=130
        )
        self.opt_cooldown.set("10 Detik (Aman)")
        self.opt_cooldown.grid(row=0, column=3, padx=(0, 15), pady=12)

        # Checkbox Skip History
        self.chk_skip = ctk.CTkCheckBox(
            self.controls_card,
            text="Lewati URL yang sudah pernah di-scrape",
            font=ctk.CTkFont(size=12)
        )
        self.chk_skip.select()
        self.chk_skip.grid(row=0, column=4, padx=(5, 15), pady=12)

        # Tombol Start/Stop
        self.btn_start = ctk.CTkButton(
            self.controls_card,
            text="▶ Mulai Scraping",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#16a34a",
            hover_color="#15803d",
            width=150,
            height=34,
            command=self._toggle_scraping
        )
        self.btn_start.grid(row=0, column=5, padx=(10, 15), pady=12, sticky="e")

        # Area Progress & Live Terminal Log
        self.log_card = ctk.CTkFrame(self.main_frame, corner_radius=8)
        self.log_card.grid(row=3, column=0, sticky="nsew", pady=(0, 0))
        self.log_card.grid_columnconfigure(0, weight=1)
        self.log_card.grid_rowconfigure(2, weight=1)

        # Progress Bar & Status Text
        self.progress_frame = ctk.CTkFrame(self.log_card, fg_color="transparent")
        self.progress_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.lbl_progress = ctk.CTkLabel(
            self.progress_frame,
            text="Status: Siap dijalankan.",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_progress.grid(row=0, column=0, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.log_card)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.progress_bar.set(0)

        # Terminal Log Box
        self.log_textbox = ctk.CTkTextbox(
            self.log_card,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#e2e8f0",
            fg_color="#0f172a"
        )
        self.log_textbox.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))

        self.log_message("[Sistem Siap] Aplikasi Dataset Riset Kesehatan Mental berhasil dimuat.")
        self.log_message(f"[Database] File dataset: {OUTPUT_CSV}")

    # ==========================================
    # LOGGING & PROGRESS HELPERS
    # ==========================================
    def log_message(self, message: str):
        """Menambahkan pesan log ke konsol terminal GUI secara thread-safe."""
        def append():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_textbox.insert("end", f"[{timestamp}] {message}\n")
            self.log_textbox.see("end")
        self.after(0, append)

    def update_progress(self, current: int, total: int, new_records: int):
        """Memperbarui status progress bar dan label counter."""
        def update():
            ratio = (current / total) if total > 0 else 0
            self.progress_bar.set(ratio)
            self.lbl_progress.configure(
                text=f"Proses: {current}/{total} URL ({int(ratio*100)}%) | +{new_records} data baru tersimpan"
            )
            self._update_total_records_display()
        self.after(0, update)

    def _update_total_records_display(self):
        """Mengambil total baris data aktual di CSV dan menampilkannya di sidebar."""
        scraper = self.scrapers.get(self.current_platform)
        if scraper:
            count = scraper.get_total_records()
            self.stats_value.configure(text=f"{count:,} Baris")

    # ==========================================
    # EVENT HANDLERS
    # ==========================================
    def _on_platform_change(self, selected_platform: str):
        self.current_platform = selected_platform
        self.header_title.configure(text=f"Platform: {selected_platform}")
        if "Threads" in selected_platform:
            self.header_desc.configure(text="Sumber Utama: Curhat personal naratif & respons interaksi.")
            self.btn_login.configure(state="normal", text="🔑 Login Akun Threads")
            self.btn_load_file.configure(state="normal", text="📥 Muat dari targets_threads.txt")
            if hasattr(self, "btn_search_preview"):
                self.btn_search_preview.configure(state="normal")
        elif "Twitter" in selected_platform:
            self.header_desc.configure(text="Sumber Kedua: Penjaring bahasa slang getir, sarkasme, & sindiran.")
            self.btn_login.configure(state="normal", text="🔑 Set Cookie auth_token X")
            self.btn_load_file.configure(state="normal", text="📥 Muat dari targets_twitter.txt")
            if hasattr(self, "btn_search_preview"):
                self.btn_search_preview.configure(state="disabled")
        elif "YouTube" in selected_platform:
            self.header_desc.configure(text="Sumber Ketiga: Curhat panjang & reflektif di bawah video edukasi mental.")
            self.btn_login.configure(state="disabled", text="🔑 Akses Publik (N/A)")
            self.btn_load_file.configure(state="normal", text="📥 Muat dari targets_youtube.txt")
            if hasattr(self, "btn_search_preview"):
                self.btn_search_preview.configure(state="disabled")
        elif "Reddit" in selected_platform:
            self.header_desc.configure(text="Sumber Keempat: Diskusi mendalam, curhat anonim di forum & komunitas.")
            self.btn_login.configure(state="disabled", text="🔑 Akses Publik / Anonim")
            self.btn_load_file.configure(state="normal", text="📥 Muat dari targets_reddit.txt")
            if hasattr(self, "btn_search_preview"):
                self.btn_search_preview.configure(state="disabled")
        elif "Instagram" in selected_platform:
            self.header_desc.configure(text="Sumber Kelima: Tanggapan singkat, reaksi emosional pada Reels & Posts.")
            self.btn_login.configure(state="disabled", text="🔑 Akses Publik / Auto-Bypass")
            self.btn_load_file.configure(state="normal", text="📥 Muat dari targets_instagram.txt")
            if hasattr(self, "btn_search_preview"):
                self.btn_search_preview.configure(state="disabled")

        self.log_message(f"[Navigasi] Beralih ke sumber data: {selected_platform}")

    def _load_from_targets_file(self):
        if "Twitter" in self.current_platform:
            filename = "targets_twitter.txt"
        elif "Reddit" in self.current_platform:
            filename = "targets_reddit.txt"
        elif "YouTube" in self.current_platform:
            filename = "targets_youtube.txt"
        elif "Instagram" in self.current_platform:
            filename = "targets_instagram.txt"
        else:
            filename = "targets_threads.txt"

        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            self.url_textbox.delete("1.0", "end")
            self.url_textbox.insert("1.0", content)
            self.log_message(f"[File] Berhasil memuat daftar dari '{filename}'.")
        else:
            self.log_message(f"[!] File '{filename}' belum ada.")

    def _clear_input_text(self):
        self.url_textbox.delete("1.0", "end")
        self.log_message("[Input] Kotak target URL dibersihkan.")

    def _open_csv_file(self):
        if os.path.exists(OUTPUT_CSV):
            try:
                os.startfile(OUTPUT_CSV)
                self.log_message(f"[File] Membuka '{OUTPUT_CSV}' di aplikasi default.")
            except Exception as e:
                self.log_message(f"[!] Gagal membuka file: {e}")
        else:
            self.log_message(f"[!] File '{OUTPUT_CSV}' belum ditemukan.")

    def _open_cleaning_dialog(self):
        DataCleaningDialog(parent=self)

    def _open_work_dir(self):
        try:
            os.startfile(os.getcwd())
            self.log_message(f"[Folder] Membuka direktori kerja.")
        except Exception as e:
            self.log_message(f"[!] Gagal membuka folder: {e}")

    def _start_login(self):
        if "Threads" in self.current_platform:
            scraper = self.scrapers["Threads (Utama)"]
            self._run_browser_login(scraper)
        elif "Twitter" in self.current_platform:
            scraper = self.scrapers["X / Twitter (Kedua)"]
            TwitterAuthTokenDialog(parent=self, scraper=scraper)
        elif "Reddit" in self.current_platform:
            self.log_message("[i] Reddit dapat diakses secara publik & anonim tanpa perlu login.")
        else:
            return

    def _run_browser_login(self, scraper):
        def login_worker():
            self.btn_login.configure(state="disabled")
            if hasattr(scraper, "run_login"):
                scraper.run_login(callback=self.log_message)
            self.btn_login.configure(state="normal")

        threading.Thread(target=login_worker, daemon=True).start()

    def _save_active_keyword(self):
        """Menyimpan keyword yang diketik menjadi keyword aktif yang disimpan ke file dan sesi."""
        kw = self.entry_keyword.get().strip()
        if not kw:
            kw = "mental health"
            self.entry_keyword.delete(0, "end")
            self.entry_keyword.insert(0, kw)

        self.active_keyword = kw
        try:
            with open(self.keyword_file, "w", encoding="utf-8") as f:
                f.write(kw)
        except Exception:
            pass

        self.lbl_keyword_status.configure(
            text=f"✓ Keyword Aktif: '{kw}' (Tersimpan & siap untuk scraping)",
            text_color="#4ade80"
        )
        self.log_message(f"[Keyword] Kata kunci aktif berhasil disimpan: '{kw}'. Scraping berikutnya akan menggunakan keyword ini.")

    def _on_search_threads_preview(self):
        keyword_val = self.entry_keyword.get().strip()
        if not keyword_val:
            self.log_message("[!] Harap isi kata kunci pencarian terlebih dahulu.")
            return

        scraper = self.scrapers.get("Threads (Utama)")
        if not scraper:
            return

        self.btn_search_preview.configure(state="disabled", text="⏳ Mencari Threads...")
        self.log_message(f"[Pencarian] Mengakses Threads Search untuk keyword: '{keyword_val}'...")

        def search_worker():
            try:
                results = scraper.search_threads_posts(
                    keyword=keyword_val,
                    max_scrolls=3,
                    callback=self.log_message
                )

                def show_dialog():
                    self.btn_search_preview.configure(state="normal", text="🔍 Cari & Pratinjau Threads")
                    if not results:
                        self.log_message(f"[!] Tidak ada hasil yang ditemukan untuk kata kunci '{keyword_val}'.")
                        return

                    ThreadsSearchPreviewDialog(
                        parent=self,
                        keyword=keyword_val,
                        initial_results=results,
                        scraper=scraper
                    )

                self.after(0, show_dialog)
            except Exception as e:
                def show_error():
                    self.btn_search_preview.configure(state="normal", text="🔍 Cari & Pratinjau Threads")
                    self.log_message(f"[!] Gagal mencari Threads: {e}")
                self.after(0, show_error)

        threading.Thread(target=search_worker, daemon=True).start()

    def _toggle_scraping(self):
        if self.worker_thread and self.worker_thread.is_alive():
            # Minta stop
            self.log_message("[*] Mengirim sinyal berhenti... Menunggu proses URL aktif selesai.")
            self.stop_event.set()
            self.btn_start.configure(state="disabled", text="⏳ Menghentikan...")
        else:
            # Mulai scraping
            raw_text = self.url_textbox.get("1.0", "end").strip()
            if not raw_text:
                self.log_message("[!] Silakan tempelkan daftar URL target terlebih dahulu.")
                return

            # Parse parameter batch
            batch_val = int(self.opt_batch.get().split()[0])
            cooldown_val = int(self.opt_cooldown.get().split()[0])
            skip_history = bool(self.chk_skip.get())

            # Ambil keyword pencarian aktif
            keyword_val = self.entry_keyword.get().strip()
            if not keyword_val:
                keyword_val = getattr(self, "active_keyword", "mental health") or "mental health"
            self.active_keyword = keyword_val

            # Perbarui label status keyword
            self.lbl_keyword_status.configure(
                text=f"✓ Keyword Aktif: '{keyword_val}' (Tersimpan & sedang dijalankan)",
                text_color="#4ade80"
            )

            self.stop_event.clear()
            self.btn_start.configure(text="⏹ Hentikan Scraping", fg_color="#dc2626", hover_color="#b91c1c")
            self.progress_bar.set(0)

            scraper = self.scrapers[self.current_platform]

            def scraping_worker():
                try:
                    self.log_message(f"[Keyword] Menggunakan keyword pencarian: '{keyword_val}'")
                    scraper.run_batch_scrape(
                        targets=raw_text.splitlines(),
                        batch_size=batch_val,
                        cooldown=cooldown_val,
                        skip_already_scraped=skip_history,
                        search_keyword=keyword_val,
                        log_callback=self.log_message,
                        progress_callback=self.update_progress,
                        stop_event=self.stop_event
                    )
                except Exception as e:
                    self.log_message(f"[!] Error saat scraping: {e}")
                finally:
                    def reset_btn():
                        self.btn_start.configure(
                            text="▶ Mulai Scraping",
                            fg_color="#16a34a",
                            hover_color="#15803d",
                            state="normal"
                        )
                        self._update_total_records_display()
                    self.after(0, reset_btn)

            self.worker_thread = threading.Thread(target=scraping_worker, daemon=True)
            self.worker_thread.start()

def run_app():
    app = ScraperApp()
    app.mainloop()

if __name__ == "__main__":
    run_app()
