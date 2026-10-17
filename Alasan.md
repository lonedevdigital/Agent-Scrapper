# Justifikasi & Analisis Pemilihan Platform untuk Dataset Kesehatan Mental (*Mental Health*)

Dokumen ini disusun sebagai landasan metodologis (*Bab Metodologi Penelitian*) dalam menentukan platform pengumpulan data komentar terkait isu kesehatan mental, dengan urutan prioritas:
1. **Sumber Utama:** Threads (Meta)
2. **Sumber Kedua:** X (Twitter)
3. **Sumber Ketiga:** YouTube

---

## 1. Mengapa Threads Menjadi Sumber Utama? (Fenomena di Indonesia)

Platform **Threads** (Meta) saat ini telah bertransformasi menjadi **"pusat curhat publik" (curhatverse) nomor satu di Indonesia**, terutama bagi kalangan Gen-Z dan Milenial. 

### Alasan Ilmiah & Keunggulan Threads:
1. **Budaya *Open-Diary* & Curhat Tanpa Beban Relasi Nyata:**
   * Berbeda dengan Instagram yang menuntut estetika visual dan menampilkan teman dekat/keluarga, pengguna Threads di Indonesia memperlakukan Threads seperti buku harian terbuka.
   * Topik yang paling dominan di Threads Indonesia adalah isu **kehidupan nyata**: *quarter-life crisis*, *burnout* dunia kerja, dinamika keluarga beracun (*toxic family*), tekanan ekonomi, hingga pengalaman terapi ke psikolog/psikiater.
2. **Algoritma Berbasis Minat (*Interest-based Discovery*):**
   * Feed Threads menyebarkan postingan berdasarkan relevansi tema, bukan sekadar jumlah pengikut. Satu curhatan seorang anonim bisa tiba-tiba menjangkau ribuan orang dan memicu ratusan komentar empati atau sindiran.
3. **Format Teks Panjang (*Micro-blogging* dengan Batas Karakter Memadai):**
   * Batas 500 karakter per postingan (dan fitur *carousel/thread*) memungkinkan pengguna menguraikan pemicu stres secara utuh dan mendalam, berbeda dengan komentar video pendek yang sering kali sangat dangkal.
4. **Kedalaman Kolom Balasan (*Replies & Peer Support*):**
   * Di Threads, interaksi di kolom balasan sangat aktif. Ketika seseorang mengunggah keluhan, komentar yang masuk terbagi menjadi dua kelompok menarik untuk diteliti:
     * Kelompok dukungan moral (*validation & peer support*).
     * Kelompok sarkasme, perdebatan, atau cemoohan (*invalidasi/sarkasme*).
5. **Ketersediaan Konteks:**
   * Di Threads, komentar selalu menempel erat pada postingan utama (*root post*). Hubungan antara *"Apa yang diceritakan di postingan utama"* dan *"Bagaimana respons komentarnya"* sangat mudah dipetakan.

---

## 2. Mengapa X (Twitter) Menjadi Sumber Kedua?

X (Twitter) diposisikan sebagai sumber sekunder untuk melengkapi data dari Threads:
* **Pusat Bahasa Slang & Sarkasme:** Gaya bahasa sindiran getir (*"mental healthku aman banget"* di saat kondisi hancur) paling banyak lahir dan berkembang di ekosistem Twitter.
* **Perbandingan Kultur Komunitas:** Karakter warganet X cenderung lebih kritis, skeptis, dan cepat merespons isu dibandingkan Threads yang cenderung lebih bercerita secara naratif personal.
* **Tantangan Teknis:** Akses API X berbayar mahal, sehingga penggunaannya sebagai sumber sekunder sangat tepat (mengambil sampel representatif dengan volume terukur tanpa membebani proses pengumpulan data).

---

## 3. Mengapa YouTube Menjadi Sumber Ketiga?

YouTube berperan sebagai sumber data pembanding berbasis edukasi:
* **Konteks Terstruktur di Kanal Edukasi Psikologi:** Menjaring komentar yang berada di bawah video bertema spesifik (misal video tentang *depresi klinis*, *bipolar*, *overthinking* di kanal Satu Persen, Menjadi Manusia, dll.).
* **Karakteristik Curhat Panjang & Reflektif:** Penonton video edukasi biasanya menulis komentar yang sangat panjang (sering kali berbentuk cerita kehidupan masa lalu) setelah terpicu oleh isi video.
* **Kemudahan Teknis:** YouTube memiliki API resmi yang stabil dan gratis untuk melengkapi kuota dataset jika data dari Threads dan X memerlukan verifikasi tambahan.

---

## 4. Matriks Perbandingan Tiga Platform Pilihan

| Kriteria Evaluasi | **1. Threads (Utama)** | **2. X / Twitter (Kedua)** | **3. YouTube (Ketiga)** |
| :--- | :--- | :--- | :--- |
| **Fokus Karakteristik Teks** | Curhat naratif personal, relasi keluarga/kerja, validasi emosi | Singkat, sarkastik, ceplas-ceplos, bahasa slang pekat | Reflektif panjang, cerita pengalaman masa lalu |
| **Kekayaan Data Sarkasme** | Tinggi (Terutama di kolom balasan/komentar) | Sangat Tinggi (Bentuk cuitan langsung maupun reply) | Sedang (Didominasi curhat serius) |
| **Konteks Induk (*Root Context*)** | Sangat Jelas (Teks postingan utama hingga 500 karakter) | Jelas (Cuitan utama / Quote Tweet) | Sangat Jelas (Judul video edukasi) |
| **Kedalaman Respon (*Replies*)** | Sangat Aktif (*peer support* dan debat) | Cepat & Spontan | Terfokus pada video |
| **Peran dalam Penelitian** | **Basis Data Inti (Mayoritas Dataset)** | **Pengaya Ragam Slang & Sarkasme** | **Pembanding Naratif Panjang & Validasi** |

---

## 5. Rekomendasi Pembagian Proporsi Dataset

Untuk menjaga keseimbangan dan objektivitas dataset pada Tugas Akhir / Jurnal:
* **Threads:** 50% – 60% dari total data (Fokus pada curhatan organik harian & balasan empati/sarkasme).
* **X (Twitter):** 25% – 30% dari total data (Fokus pada variasi sarkasme, humor getir, dan slang Gen-Z).
* **YouTube:** 15% – 20% dari total data (Fokus pada curhatan mendalam berbasis topik psikologi klinis).
