# Wired Articles Data Pipeline

## Project Overview

Project ini merupakan implementasi pipeline data otomatis untuk mata kuliah Infrastruktur dan Platform Big Data (IPBD). Pipeline ini mengambil data berita dari Wired.com, menyajikannya melalui API, mengorkestrasinya menggunakan Prefect DAG, dan menyimpannya ke dalam PostgreSQL database untuk analisis lebih lanjut.

## Arsitektur Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Scraping    │────▶│   Storage    │────▶│     API      │
│   (Selenium) │     │  (JSON/CSV)  │     │  (FastAPI)   │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
                    ┌──────────────┐     ┌──────────────┐
                    │   Reporting  │◀────│     DAG      │
                    │ (SQL Query)  │     │  (Prefect)   │
                    └──────────────┘     └──────────────┘
                           ▲
                           │
                    ┌──────────────┐
                    │  Database    │
                    │ (PostgreSQL) │
                    └──────────────┘
```

## Komponen

| Komponen | Tool | Keterangan |
|----------|------|------------|
| Scraping | Selenium | Mengambil 75+ berita dari Wired.com |
| API | FastAPI | Menyediakan data hasil scrape |
| DAG | Prefect | Orchestration pipeline |
| Database | PostgreSQL | Penyimpanan data terstruktur |

## Tech Stack

- **Python 3.10+**
- **Selenium** - Web scraping dengan anti-detection
- **FastAPI** - REST API framework
- **Prefect** - Workflow orchestration
- **PostgreSQL** - Database
- **Docker & Docker Compose** - Containerization

## Installation

### Prerequisites

- Python 3.10 atau lebih tinggi
- Docker dan Docker Compose
- Google Chrome (untuk Selenium)

### Install Dependencies

```bash
# Install dependencies untuk scraper
pip install -r scripts/requirements.txt

# Install dependencies untuk DAG
pip install -r dags/requirements.txt

# Install dependencies untuk API
pip install -r api/requirements.txt
```

## Cara Menjalankan Pipeline

### 1. Start Database

```bash
docker-compose up -d postgres
```

PostgreSQL akan running di port 5436 dengan:
- Database: wired_db
- User: postgres
- Password: postgres

### 2. Run Scraper

```bash
cd scripts
python scraper.py
```

Scraper akan:
- Mengakses 5 kategori Wired.com (Security, Science, Business, Culture, Gear)
- Scraping minimal 50 artikel
- Menyimpan hasil ke JSON dan CSV
- Author dan description sudah include

Output:
- `data/wired_articles.json`
- `data/wired_articles.csv`

### 3. Start API

```bash
cd api
uvicorn main:app --host 0.0.0.0 --port 8001
```

Atau menggunakan Docker:

```bash
docker-compose up -d api
```

API akan running di http://localhost:8001

### 4. Run Prefect DAG

```bash
cd dags
python wired_pipeline.py
```

Pipeline akan:
1. Fetch data dari API endpoint `/articles`
2. Transformasi format tanggal
3. Insert ke PostgreSQL database

### 5. Run SQL Queries

```bash
python scripts/queries.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Root endpoint dengan info |
| GET | /articles | Get semua artikel dari JSON |
| GET | /articles/count | Count jumlah artikel |
| GET | /latest | Get latest session data |

Akses API Documentation (Swagger UI):
```
http://localhost:8001/docs
```

## Required Queries (Query Wajib UTS)

### Query 1: Judul Artikel dan Author (tanpa "By")

Menampilkan judul artikel dan nama author yang sudah dibersihkan dari kata "By" di depannya.

```sql
SELECT 
    title,
    REPLACE(author, 'By', '') AS clean_author
FROM wired_articles
WHERE author IS NOT NULL AND author != '';
```

### Query 2: Top 3 Penulis Paling Sering Muncul

Menampilkan 3 nama penulis yang paling sering muncul dalam database hasil scrape.

```sql
SELECT 
    REPLACE(author, 'By', '') AS author_name,
    COUNT(*) AS article_count
FROM wired_articles
WHERE author IS NOT NULL AND author != ''
GROUP BY author
ORDER BY article_count DESC
LIMIT 3;
```

### Query 3: Cari Artikel dengan Keyword

Mencari artikel yang mengandung kata kunci "AI", "Climate", atau "Security" pada judul atau deskripsi.

```sql
SELECT title, description, author
FROM wired_articles
WHERE 
    title ILIKE '%AI%'
    OR title ILIKE '%Climate%'
    OR title ILIKE '%Security%'
    OR description ILIKE '%AI%'
    OR description ILIKE '%Climate%'
    OR description ILIKE '%Security%'
ORDER BY id;
```

## Project Structure

```
Responsi-IPBD-1/
├── api/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt    # API dependencies
│   └── Dockerfile.api      # Docker configuration
├── dags/
│   ├── wired_pipeline.py   # Prefect DAG
│   └── requirements.txt   # DAG dependencies
├── scripts/
│   ├── scraper.py         # Selenium scraper
│   └── queries.py         # SQL queries
├── data/
│   ├── wired_articles.json    # Scraped data (JSON)
│   └── wired_articles.csv    # Scraped data (CSV)
├── docker-compose.yml       # Docker Compose config
└── README.md               # This file
```

## Scraper Features

Scraper menggunakan beberapa teknik anti-detection:

1. **User-Agent Rotation** - Mengubah user-agent secara acak
2. **Human-like Scrolling** - Simulasi scroll seperti manusia
3. **Random Mouse Movement** - Simulasi pergerakan mouse
4. **Random Delays** - Jeda acak antar request
5. **CDP Command Override** - Menyembunyikan webdriver property

## Prefect DAG Flow

```
┌─────────────────┐
│ fetch_from_api  │  (Task 1: GET /articles dari API)
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ transform_articles │  (Task 2: Transformasi format tanggal)
└────────┬────────────┘
         │
         ▼
┌───────────────────┐
│ load_to_database  │  (Task 3: Insert ke PostgreSQL)
└───────────────────┘
```

## Data Schema

### Tabel: wired_articles

| Column | Type | Description |
|-------|------|-------------|
| id | SERIAL | Primary key |
| title | TEXT | Judul artikel |
| url | TEXT | Link artikel |
| description | TEXT | Deskripsi singkat |
| author | TEXT | Nama penulis (dengan "By ") |
| scraped_at | TIMESTAMP | Timestamp pengambilan data |
| source | TEXT | Sumber (Wired.com) |
| created_at | TIMESTAMP | Waktu insert ke DB |

## Troubleshooting

### Masalah: Chrome tidak terdetek

Pastikan Chrome sudah terinstall di sistem.

### Masalah: SSL Error

Tambahkan argument `--ignore-certificate-errors` pada Chrome options.

### Masalah: Prefect module not found

```bash
pip install prefect
```

### Masalah: Database connection failed

Pastikan PostgreSQL sudah running:
```bash
docker-compose up -d postgres
```

## Screenshots untuk Dokumentasi UTS

1. **Scraping**: Screenshot saat Selenium berjalan (browser terbuka visible mode)
2. **DAG**: Screenshot Prefect Tree/Graph View dengan status Success
3. **Query Results**: Screenshot hasil eksekusi 3 query wajib

## Credit

- Source: Wired.com (https://www.wired.com)
- Built for: Responsi UTS Infrastruktur dan Platform Big Data
- Semester: 4
- Tahun: 2026