# 🧠 Mental Health Multi-Platform Dataset Scraper & Workstation

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-Automated%20Browser-green.svg)](https://playwright.dev)
[![CustomTkinter UI](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://customtkinter.tomschimansky.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/lonedevdigital/Agent-Scrapper?color=orange)](https://github.com/lonedevdigital/Agent-Scrapper/releases)

Sistem ekstraksi data media sosial multi-platform terpadu (*Threads*, *X / Twitter*, *YouTube*, *Reddit*, dan *Instagram*) yang dirancang khusus untuk riset **Analisis Sentimen, Deteksi Sarkasme, dan Klasifikasi Kesehatan Mental (*Mental Health*)** di Indonesia. Dilengkapi antarmuka grafis modern (**CustomTkinter GUI v2.0.1**), mesin perayap anti-deteksi bot (*Deep Stealth & Persistent Context*), sistem checkpoint inkremental anti-kehilangan data, serta workstation anotasi data (**TagForge Labeling Engine**).

---

## 📌 Daftar Isi
- [Latar Belakang Riset](#-latar-belakang-riset)
- [Arsitektur & Matriks Platform](#-arsitektur--matriks-platform)
- [Standarisasi Skema Dataset (18 Kolom)](#-standarisasi-skema-dataset-18-kolom)
- [Fitur Utama](#-fitur-utama)
- [Struktur Repositori](#-struktur-repositori)
- [Panduan Penggunaan Cepat](#-panduan-penggunaan-cepat)
  - [Opsi A: Menggunakan Executable Siap Pakai (Rilis .ZIP)](#opsi-a-menggunakan-executable-siap-pakai-rilis-zip)
  - [Opsi B: Menjalankan dari Source Code (Python)](#opsi-b-menjalankan-dari-source-code-python)
- [Tata Cara Scraping per Platform](#-tata-cara-scraping-per-platform)
  - [1. X / Twitter (Cookie Auth Token)](#1-x--twitter-cookie-auth-token)
  - [2. Threads (Meta)](#2-threads-meta)
  - [3. YouTube (Video & Shorts)](#3-youtube-video--shorts)
  - [4. Reddit (Komunitas & Forum Diskusi)](#4-reddit-komunitas--forum-diskusi)
  - [5. Instagram (Reels & Posts)](#5-instagram-reels--posts)
- [Aplikasi Anotasi (TagForge Labeling)](#-aplikasi-anotasi-tagforge-labeling)
- [Build ke Executable (.exe)](#-build-ke-executable-exe)
- [Etika Penelitian & Kepatuhan UU PDP](#-etika-penelitian--kepatuhan-uu-pdp)

---

## 🔬 Latar Belakang Riset

Isu kesehatan mental (*burnout*, depresi, kecemasan akademis, *quarter-life crisis*) marak diekspresikan di media sosial Indonesia dengan nuansa bahasa yang sangat kompleks:
- **Campuran Slang & Sarkasme:** Ungkapan getir seperti *"Mental health-ku aman banget hari ini lembur sambil disindir dosen"* yang bermakna kebalikan dari arti harfiah.
- **Dukungan Teman Sebaya (*Peer Support*):** Kolom komentar yang menyediakan validasi empati maupun perdebatan.
- **Ketergantungan Konteks:** Komentar balasan tidak dapat dipahami tanpa mengetahui isi postingan utama (*root post*).

Repositori ini menyediakan crawler cerdas yang tidak hanya mengunduh komentar, tetapi secara otomatis **menautkan relasi hierarkis antara postingan utama dan balasannya**, mengekstrak emoji asli, mendeteksi penekanan *capslock*, dan mengurutkannya ke skema tabular seragam.

---

## 🌐 Arsitektur & Matriks Platform

| Platform | Peran dalam Riset | Karakteristik Bahasa & Data | Metode Akses |
| :--- | :--- | :--- | :--- |
| **Threads (Meta)** | **Sumber Utama** | Narasi curhat personal panjang (*open-diary*), validasi emosional di kolom komentar. | Playwright Stealth Browser |
| **X (Twitter)** | **Sumber Kedua** | Bahasa slang getir, sindiran tajam, sarkasme murni, dan reaksi spontan warganet. | Persistent Context + `auth_token` |
| **YouTube** | **Sumber Ketiga** | Refleksi emosional panjang di bawah video edukasi kesehatan mental & psikologi. | Playwright Auto-Scroll Parser |
| **Reddit** | **Sumber Keempat** | Diskusi mendalam di subreddit r/indonesia, curhat anonim komprehensif tanpa batasan karakter. | Public JSON API Parser |
| **Instagram** | **Sumber Kelima** | Tanggapan spontan, komentar reaktif, dan reaksi audio-visual pada Reels & Posts. | Playwright Dialog Bypass Parser |

---

## 📋 Standarisasi Skema Dataset (18 Kolom)

Semua perayap (*Threads, X, YouTube, Reddit, Instagram*) menghasilkan struktur dataset yang **100% seragam** di [`dataset_mental_health.csv`](file:///d:/KULIAH/TUGAS_AKHIR_JURNAL/dataset_mental_health.csv):

| No | Nama Kolom | Tipe Data | Deskripsi & Contoh |
|:---|:---|:---|:---|
| 1 | `comment_id` | String | ID unik record (cth: `TH_DZeUk_001`, `TW_1413544_002`, `YT_r1MUHI_001`, `IG_DdQ2ou_001`, `RD_ycx1nd_001`). |
| 2 | `platform` | String | Platform sumber: `threads`, `twitter`, `youtube`, `reddit`, atau `instagram`. |
| 3 | `search_keyword` | String | Kata kunci penelusuran (cth: `mental health mahasiswa`). |
| 4 | `author` | String | Handle/Username bersih penulis (cth: `@usaidasmadi_`, `@RaymondChins`, `@kuku_kaki_kakek_ku`, `rinicruzz`). |
| 5 | `post_id` | String | ID postingan utama (cth: `TW_1413544816357650447`, `YT_r1MUHIUkYxs`, `IG_DdQ2ouFlQwr`, `DZeUkUCGYnK`). |
| 6 | `post_title` | String | Teks lengkap dari cuitan/video/postingan utama (sebagai konteks). |
| 7 | `comment_text` | String | Teks isi komentar/balasan (atau teks postingan jika root). |
| 8 | `parent_id` | String | ID induk (bernilai kosong untuk root, dan `post_id` untuk balasan). |
| 9 | `parent_text` | String | Teks induk yang dibalas (bernilai kosong untuk root). |
| 10 | `is_reply` | Integer | `0` = Postingan Utama (Root), `1` = Balasan / Komentar. |
| 11 | `created_at` | String | Waktu pembuatan format ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`). |
| 12 | `like_count` | Integer | Jumlah suka / upvote (cth: `23000`, `2900`). |
| 13 | `reply_count` | Integer | Jumlah balasan ke komentar tersebut. |
| 14 | `emojis` | String | Seluruh emoji unicode yang diekstrak (cth: `😭😭😭`, `🙏`, `🔥`). |
| 15 | `has_capslock` | Integer | `1` jika mengandung kata kapital penuh (indikasi emosi/sarkasme), `0` jika tidak. |
| 16 | `is_sarcasm` | Float/Empty | Nilai anotasi sarkasme (diisi saat proses labeling). |
| 17 | `actual_sentiment`| String/Empty | Label sentimen: `Normal`, `Stress`, `Cemas`, `Depresi`. |
| 18 | `topic_category` | String/Empty | Kategori topik penelitian (cth: `Akademik / Skripsi`, `Burnout`). |

---

## ⚡ Fitur Utama

1. **GUI Interaktif (CustomTkinter)**:
   - Manajemen platform satu klik melalui sidebar.
   - Kotak log real-time, progress bar, dan statistik total data di CSV.
   - Pengaturan ukuran batch dan jeda *cooldown* otomatis untuk mencegah pemblokiran *rate-limit*.
2. **Anti-Detection Bot Stealth**:
   - Penghapusan flag automasi Chrome (`--disable-blink-features=AutomationControlled`, bypass `navigator.webdriver`).
   - *Persistent Browser Context* dengan profil pengguna nyata lokal (`.twitter_user_data`).
3. **Penyimpanan Bertahap (Incremental Auto-Save)**:
   - Data otomatis disimpan per tautan URL yang berhasil di-scrape langsung ke CSV.
   - Pengecekan duplikasi otomatis berbasis `comment_id` (*deduplication on write*).
   - Pencatatan riwayat otomatis ke `target_sudah scrapping_*.txt` agar URL tidak di-scrape dua kali.
4. **Pembersihan Teks Terintegrasi**:
   - Konversi Twemoji / web images ke unicode emoji asli.
   - Normalisasi spasi dan sanitasi karakter baris baru agar tidak merusak format sel tabel Excel / CSV.

---

## 📁 Struktur Repositori

```text
├── apps/
│   ├── gui.py                  # Antarmuka CustomTkinter GUI Desktop
│   └── __init__.py
├── sources/
│   ├── base.py                 # Abstract Base Scraper & utilitas ekstraksi data
│   ├── threads_scraper.py      # Crawler Threads (Meta)
│   ├── twitter_scraper.py      # Crawler X (Twitter) teroptimasi
│   ├── youtube_scraper.py      # Crawler YouTube Comments & Video Meta
│   ├── reddit_scraper.py       # Crawler Reddit (r/indonesia, r/mentalhealth)
│   └── instagram_scraper.py    # Crawler Instagram Reels & Posts (Auto-Bypass Modal)
├── Labelingapps/
│   ├── index.html              # Antarmuka Web Labeling Workstation (TagForge)
│   ├── app.js                  # Engine parsing, hotkeys, & ekspor CSV
│   └── style.css               # Desain antarmuka editorial
├── dataset_mental_health.csv   # Dataset utama hasil scraping multi-platform
├── template_dataset_mental_health.csv # Format template skema 18 kolom
├── MentalHealthScraper.spec    # Spesifikasi build PyInstaller
├── MentalHealthScraper_Build.zip # Arsip build rilis siap pakai (.exe)
├── requirements.txt            # Dependensi Python
├── run_app.py                  # Entry-point menjalankan aplikasi GUI
└── targets_*.txt               # Daftar input target URL per platform
```

---

## 🚀 Panduan Penggunaan Cepat

### Opsi A: Menggunakan Executable Siap Pakai (Rilis .ZIP)

Jika Anda tidak ingin memasang Python atau dependensi:
1. Unduh **`MentalHealthScraper_Build.zip`** dari tab [Releases](https://github.com/lonedevdigital/Agent-Scrapper/releases).
2. Ekstrak file zip ke folder komputer Anda.
3. Klik ganda **`MentalHealthScraper.exe`**.
4. Aplikasi GUI langsung terbuka dan siap digunakan!

### Opsi B: Menjalankan dari Source Code (Python)

1. **Clone Repositori:**
   ```bash
   git clone https://github.com/lonedevdigital/Agent-Scrapper.git
   cd Agent-Scrapper
   ```

2. **Pasang Dependensi:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Jalankan Aplikasi GUI:**
   ```bash
   python run_app.py
   ```

---

## 🔍 Tata Cara Scraping per Platform

### 1. X / Twitter (Cookie Auth Token)
Karena X (Twitter) membatasi penjelajahan komentar bagi pengguna anonim, sistem menggunakan injeksi cookie sesi:
1. Buka browser Anda (Chrome/Edge), lalu masuk ke akun [x.com](https://x.com).
2. Tekan `F12` -> Buka tab **Application** / **Penyimpanan** -> Klik **Cookies** -> `https://x.com`.
3. Cari cookie bernama **`auth_token`**, lalu salin nilainya.
4. Di aplikasi Scraper, pilih platform **X / Twitter (Kedua)** di sidebar.
5. Klik tombol **`🔑 Set Cookie auth_token X`**, tempel token, lalu simpan.
6. Masukkan URL cuitan yang ingin diambil (cth: `https://x.com/username/status/1413544816357650447`).
7. Klik **`▶ Mulai Scraping`**.

### 2. Threads (Meta)
1. Pilih **Threads (Utama)** pada menu sidebar.
2. Anda dapat memanfaatkan fitur **`🔍 Cari & Pratinjau Threads`** untuk menemukan postingan relevan berdasarkan kata kunci secara langsung.
3. Masukkan daftar tautan Threads ke dalam kotak input target atau muat dari `targets_threads.txt`.
4. Klik **`▶ Mulai Scraping`**.

### 3. YouTube (Video & Shorts)
1. Pilih **YouTube (Ketiga)** pada menu sidebar.
2. Akses publik (tidak membutuhkan login/kuki).
3. Masukkan daftar tautan video YouTube (mendukung format `https://www.youtube.com/watch?v=...`, `https://youtu.be/...`, dan `https://www.youtube.com/shorts/...`) atau muat dari `targets_youtube.txt`.
4. Klik **`▶ Mulai Scraping`**. Sistem akan mengekstrak judul video dan deskripsi sebagai Postingan Utama (Root Post), dilanjutkan dengan seluruh rantai komentar dan jumlah suka (*likes*).

### 4. Reddit (Komunitas & Forum Diskusi)
1. Pilih **Reddit (Keempat)** pada menu sidebar.
2. Tidak memerlukan akun atau login (akses publik).
3. Masukkan URL thread Reddit (cth: `https://www.reddit.com/r/indonesia/comments/...`) atau muat dari `targets_reddit.txt`.
4. Klik **`▶ Mulai Scraping`**. Seluruh thread hierarki komentar otomatis diekstrak.

### 5. Instagram (Reels & Posts)
1. Pilih **Instagram (Kelima)** pada menu sidebar.
2. Akses publik dengan *Auto-Bypass Login Modal* (dialog login otomatis ditutup/dibersihkan).
3. Masukkan daftar URL Reel atau Postingan Instagram (cth: `https://www.instagram.com/reel/SHORTCODE/` atau `https://www.instagram.com/p/SHORTCODE/`) atau muat dari `targets_instagram.txt`.
4. Klik **`▶ Mulai Scraping`**. Sistem mengambil *caption* sebagai root post dan memperluas komentar secara berkala (*load more comments*) beserta stempel waktu ISO presisi.

---

## 🏷️ Aplikasi Anotasi (TagForge Labeling)

Untuk memudahkan pelabelan korpus teks penelitian (*Ground Truth Dataset*):
1. Masuk ke folder `Labelingapps/`.
2. Buka `index.html` langsung di peramban (Chrome, Edge, Firefox).
3. Muat file `dataset_mental_health.csv`.
4. Anotasi teks menggunakan tombol cepat keyboard (Hotkeys `1`, `2`, `3`, `4` untuk kategori *Normal*, *Stress*, *Cemas*, *Depresi*).
5. Klik **Export CSV** untuk mengunduh dataset yang sudah terlabeli rapi.

---

## 🔨 Build ke Executable (.exe)

Untuk mem-build ulang installer standalone dari source code:
```bash
python -m PyInstaller MentalHealthScraper.spec --noconfirm
```
Hasil build akan tersedia di folder `dist/MentalHealthScraper/`.

---

## ⚖️ Etika Penelitian & Kepatuhan UU PDP

Pengumpulan dataset ini tunduk pada etika penelitian ilmiah dan kepatuhan privasi data:
- **UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP):** Modul crawler menyediakan fungsi `anonymize_id` (hashing SHA-256) untuk mengenkripsi identitas username menjadi kode unik anonim.
- **Tujuan Akademis:** Dataset hanya digunakan untuk penelitian komputasi linguistik, deteksi dini krisis mental, dan analisis sentimen non-komersial.

