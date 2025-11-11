# 🎥 YouTube Comment Scraper

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**Scraper komentar YouTube yang powerful dengan dukungan AI, multi-format export, dan API internal YouTube**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Output](#-output-formats) • [FAQ](#-faq)

</div>

---

## 🌟 Highlights

- ✅ **Menggunakan API Internal YouTube** - Lebih cepat dan reliable dibanding scraping HTML
- 🤖 **AI-Powered Selector Detection** - Otomatis detect selector menggunakan Google Gemini AI
- 📊 **Multi-Format Export** - JSON, TXT, CSV dalam satu eksekusi
- 🎯 **Flexible Scraping** - Ambil semua komentar atau jumlah spesifik (100, 500, 1000+)
- 🔄 **Auto-Continuation** - Otomatis handle pagination untuk ribuan komentar
- 💾 **Organized Output** - File tersimpan rapi dalam folder terpisah per video
- 🛡️ **Error Handling** - Robust error handling untuk scraping yang stabil
- 📱 **User-Friendly Interface** - Menu interaktif yang mudah digunakan

---

## 🚀 Features

### Core Features

#### 1. **Internal YouTube API Integration**

- Menggunakan endpoint `/youtubei/v1/next` untuk fetching komentar
- Lebih cepat dan stabil dibanding parsing HTML
- Support pagination otomatis dengan continuation tokens
- Dapat mengambil ribuan komentar tanpa masalah

#### 2. **AI-Powered Selector Detection (Optional)**

- Integrasi dengan Google Gemini AI
- Otomatis menganalisis struktur HTML YouTube
- Menemukan selector CSS yang tepat secara dinamis
- Berguna jika struktur YouTube berubah

#### 3. **Flexible Scraping Modes**

- **Mode ALL**: Ambil semua komentar yang tersedia
- **Mode SPECIFIC**: Tentukan jumlah komentar (contoh: 100, 500, 1000)
- Auto-stop saat target tercapai
- Smart pagination dengan consecutive empty detection

#### 4. **Multi-Format Export**

Setiap scraping menghasilkan 4 file:

| Format     | Deskripsi                | Use Case                      |
| ---------- | ------------------------ | ----------------------------- |
| **JSON**   | Data lengkap terstruktur | Analisis programmatic, backup |
| **TXT**    | Format human-readable    | Quick review, dokumentasi     |
| **CSV**    | Excel-compatible         | Data analysis, spreadsheet    |
| **README** | Summary info             | Quick reference               |

#### 5. **Rich Metadata Extraction**

- ✅ Video title & channel name
- ✅ Comment author & text
- ✅ Publish time
- ✅ Likes count (normalized dari 1.2K → 1200)
- ✅ Replies count
- ✅ Comment ID untuk deduplication

#### 6. **Smart Data Processing**

- **Deduplication**: Cegah komentar duplikat
- **Normalization**: Konversi "1.2K" → "1200"
- **Sanitization**: Filename aman untuk semua OS
- **Organized Storage**: Folder terpisah per video

---

## 📋 Prerequisites

- Python 3.8+
- Edge browser
- (Optional) Google Gemini API key untuk AI detection

---

## 🔧 Installation

### 1. Clone Repository

```bash
git clone https://github.com/Zulkifli1409/YouTube-Comment-Scraper.git
cd YouTube-Comment-Scraper
```

### 2. Install Dependencies

```bash
pip install botasaurus
pip install google-generativeai
pip install requests
pip install beautifulsoup4
```

### 3. (Optional) Setup AI Detection

```bash
# Set environment variable untuk Gemini API
export GEMINI_API_KEY="your_api_key_here"  # Linux/Mac
set GEMINI_API_KEY=your_api_key_here      # Windows
```

Dapatkan API key gratis di: https://makersuite.google.com/app/apikey

### 4. Configure Edge (browser) path

Jika script tidak menemukan Microsoft Edge otomatis, tentukan lokasi executable di `main.py`.

Cara cepat menemukan path Edge di PowerShell:

```powershell
(Get-Command msedge).Source
```

Lalu edit `main.py` dan pastikan dekorator `@browser(...)` menyertakan:

```python
chrome_executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
```

---

## 💻 Usage

### Basic Usage

```bash
python main.py
```

### Interactive Menu Flow

```
═══════════════════════════════════════════════════════════════════
🎥 YOUTUBE COMMENT SCRAPER - ENHANCED VERSION
═══════════════════════════════════════════════════════════════════

🤖 AI Selector Detection: ✅ AKTIF

📺 Masukkan URL YouTube video: https://youtube.com/watch?v=xxxxx

──────────────────────────────────────────────────────────────────
💬 PILIHAN JUMLAH KOMENTAR:
──────────────────────────────────────────────────────────────────
  1. Ambil SEMUA komentar (recommended)
  2. Ambil jumlah komentar tertentu (contoh: 100, 500, 1000)
──────────────────────────────────────────────────────────────────

📌 Pilihan Anda (1/2): 1
```

### Example Use Cases

#### Case 1: Scrape All Comments

```python
# Input in menu:
URL: https://youtube.com/watch?v=dQw4w9WgXcQ
Mode: 1 (All comments)

# Output:
✅ 2,547 comments scraped
📁 output/Never_Gonna_Give_You_Up_dQw4w9WgXcQ/
```

#### Case 2: Scrape First 500 Comments

```python
# Input in menu:
URL: https://youtube.com/watch?v=dQw4w9WgXcQ
Mode: 2 (Specific count)
Count: 500

# Output:
✅ 500 comments scraped
📁 output/Never_Gonna_Give_You_Up_dQw4w9WgXcQ/
```

---

## 📂 Output Formats

### Folder Structure

```
output/
└── Video_Title_videoID/
    ├── comments_20241111_143022.json
    ├── comments_20241111_143022.txt
    ├── comments_20241111_143022.csv
    └── README.txt
```

### 1. JSON Format

```json
{
  "video_id": "dQw4w9WgXcQ",
  "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "video_title": "Never Gonna Give You Up",
  "channel_name": "Rick Astley",
  "total_comments": 2547,
  "scraped_at": "2024-11-11T14:30:22",
  "comments": [
    {
      "index": 1,
      "comment_id": "UgxXXXXXXX",
      "author": "Zoel",
      "text": "Great song!",
      "published": "2 weeks ago",
      "likes": "1200",
      "replies_count": "45"
    }
  ]
}
```

### 2. TXT Format (Human-Readable)

```
═══════════════════════════════════════════════════════════════════
🎥 YOUTUBE COMMENT EXPORT
═══════════════════════════════════════════════════════════════════

📹 Video Title: Never Gonna Give You Up
👤 Channel: Rick Astley
🔗 URL: https://youtube.com/watch?v=dQw4w9WgXcQ
💬 Total Comments: 2,547
📅 Scraped At: 2024-11-11T14:30:22

[1] ─────────────────────────────────────────────────────────────
👤 Zoel
📅 2 weeks ago | 👍 1200 likes | 💬 45 replies
💭 Great song! Never gets old...
```

### 3. CSV Format (Excel-Compatible)

| No  | Author | Comment     | Published   | Likes | Replies |
| --- | ------ | ----------- | ----------- | ----- | ------- |
| 1   | Zoel   | Great song! | 2 weeks ago | 1200  | 45      |
| 2   | Zul    | Love it!    | 3 days ago  | 850   | 12      |

### 4. README.txt (Summary)

```
YouTube Comment Export Summary
==================================================

Video: Never Gonna Give You Up
Channel: Rick Astley
Total Comments: 2,547
Scraped: 2024-11-11T14:30:22

Files:
  - comments_20241111_143022.json (Full data)
  - comments_20241111_143022.txt (Readable text)
  - comments_20241111_143022.csv (Excel format)
```

---

## 🎯 Advanced Features

### Deduplication System

```python
# Otomatis deteksi & skip komentar duplikat
dedupe_key = comment_id or f"{author}::{text}"
if dedupe_key in seen_ids:
    continue  # Skip duplikat
seen_ids.add(dedupe_key)
```

### Number Normalization

```python
# Input: "1.2K likes", "3M views", "500B"
# Output: "1200", "3000000", "500000000000"
normalize_count_value("1.2K")  # → "1200"
normalize_count_value("3M")    # → "3000000"
```

### Smart Continuation

```python
# Auto-detect & follow pagination
consecutive_empty = 0
max_consecutive_empty = 5

# Stop jika 5x berturut-turut tidak ada data baru
if consecutive_empty >= max_consecutive_empty:
    break
```

---

## 🛠️ Technical Architecture

### API Workflow

```
1. Load YouTube page → Extract ytInitialData
2. Get API key & context from ytcfg
3. Extract initial continuation token
4. POST to /youtubei/v1/next endpoint
5. Parse comment data + entities
6. Get next continuation token
7. Repeat until: target reached OR no more tokens
```

### Data Structures

#### Legacy Format (Old YouTube)

```python
commentRenderer = {
    "commentId": "xxx",
    "authorText": {"simpleText": "Zoel"},
    "contentText": {"runs": [{"text": "..."}]},
    "publishedTimeText": {"simpleText": "2 days ago"},
    "voteCount": {"simpleText": "123"},
    "likeCount": 123
}
```

#### ViewModel Format (New YouTube)

```python
commentViewModel = {
    "commentKey": "xxx",
    "entity": {
        "properties": {
            "commentId": "xxx",
            "content": {"content": "..."},
            "publishedTime": "2 days ago",
            "authorButtonA11y": "Zoel"
        },
        "toolbar": {
            "likeCountA11y": "123 likes"
        }
    }
}
```

---

## ❓ FAQ

### Q: Apakah legal untuk scrape YouTube comments?

**A:** Scraping untuk tujuan pribadi/riset umumnya OK, tapi perhatikan:

- ✅ Jangan overload server (rate limiting built-in)
- ✅ Jangan scrape data pribadi sensitif
- ✅ Patuhi YouTube Terms of Service
- ⚠️ Jangan untuk spam atau harassment

### Q: Berapa lama waktu scraping?

**A:** Tergantung jumlah komentar:

- 100 comments: ~30 detik
- 1,000 comments: ~2-3 menit
- 10,000 comments: ~15-20 menit

### Q: Kenapa tidak semua komentar terambil?

**A:** Kemungkinan:

- Video memiliki komentar yang di-hide/delete
- Rate limiting dari YouTube
- Komentar hanya visible untuk subscriber
- Koneksi internet tidak stabil

### Q: Apakah perlu API key YouTube?

**A:** TIDAK. Tool ini menggunakan internal API yang tidak memerlukan official API key. Gemini API key hanya untuk fitur AI selector (optional).

### Q: Bisa scrape replies (balasan komentar)?

**A:** Saat ini hanya top-level comments. Replies count ditampilkan tapi tidak di-fetch. Akan ditambahkan di versi mendatang.

### Q: Error "Cannot find browser"?

**A:** Edit path browser di line 355:

```python
chrome_executable_path=r"C:\path\to\your\msedge.exe"
```

### Q: Support untuk YouTube Shorts?

**A:** Belum. Shorts menggunakan API endpoint berbeda. Coming soon!

---

## 🚧 Known Limitations

- ❌ Tidak support scraping replies (balasan komentar)
- ❌ Tidak support live chat
- ❌ Tidak support YouTube Shorts (untuk sekarang)
- ⚠️ Rate limiting bisa terjadi jika scraping terlalu agresif
- ⚠️ Struktur API YouTube bisa berubah sewaktu-waktu

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

This tool is for educational and research purposes only. Users are responsible for complying with YouTube's Terms of Service and applicable laws. The developers are not responsible for any misuse of this tool.

---

## 👨‍💻 Author

**Your Name**

- GitHub: [@zulkifli1409](https://github.com/zulkifli1409)
- Email: zul140904@gmail.com

---

## 🙏 Acknowledgments

- [Botasaurus](https://github.com/omkarcloud/botasaurus) - Browser automation
- [Google Gemini AI](https://ai.google.dev/) - AI selector detection
- YouTube Internal API - Data source
- BeautifulSoup4 - HTML parsing

---

## 📊 Stats

![GitHub stars](https://img.shields.io/github/stars/zulkifli1409/YouTube-Comment-Scraper?style=social)
![GitHub forks](https://img.shields.io/github/forks/zulkifli1409/YouTube-Comment-Scraper?style=social)
![GitHub issues](https://img.shields.io/github/issues/zulkifli1409/YouTube-Comment-Scraper)
![GitHub pull requests](https://img.shields.io/github/issues-pr/zulkifli1409/YouTube-Comment-Scraper)

---

<div align="center">

**⭐ Star this repo if you find it useful!**

Made with ❤️ and ☕

</div>
