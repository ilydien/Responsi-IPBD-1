"""
Prefect DAG for Wired Articles Pipeline
Fetches data from API and loads to PostgreSQL
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import psycopg2
import requests
from prefect import flow, task


API_URL = "http://api:8001"
FALLBACK_API_URL = "http://localhost:8001"

DATA_DIR = Path("data")

DB_PARAMS = {
    "host": "postgres",
    "port": 5432,
    "database": "wired_db",
    "user": "postgres",
    "password": "postgres",
}


@task
def fetch_from_json() -> List[Dict[str, Any]]:
    print("Fetching articles from JSON...")

    json_files = list(Path("/app/data").glob("wired_articles.json"))
    if not json_files:
        raise FileNotFoundError("No JSON file found")

    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)

    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])

    print(f"Fetched {len(articles)} articles from JSON")

    if articles:
        print("Sample data:", articles[0])

    return articles


@task
def transform_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    print("Transforming article data...")

    transformed = []

    for article in articles:
        scraped_at = article.get("scraped_at")

        if isinstance(scraped_at, str) and "T" in scraped_at:
            dt = datetime.fromisoformat(scraped_at.replace("Z", "+00:00"))
            article["scraped_at"] = dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            article["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        transformed.append(article)

    print(f"Transformed {len(transformed)} articles")
    return transformed


@task
def load_to_database(articles: List[Dict[str, Any]]) -> int:
    print(f"Loading {len(articles)} articles to database...")

    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wired_articles (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT UNIQUE,
            description TEXT,
            author TEXT,
            scraped_at TIMESTAMP,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    inserted_count = 0

    for i, article in enumerate(articles):
        try:
            if i == 0:
                print("DEBUG SAMPLE:", article)
                print("KEYS:", list(article.keys()))

            title = (article["title"] or "").strip()
            url = (article["url"] or "").strip()

            description = (article.get("description") or "").strip()
            author = (article.get("author") or "").replace("By ", "").strip()

            scraped_at = article.get("scraped_at")
            if isinstance(scraped_at, str) and "T" in scraped_at:
                scraped_at = datetime.fromisoformat(
                    scraped_at.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d %H:%M:%S")

            source = (article.get("source") or "Wired.com").strip()

            if i == 0:
                print("INSERTING:", description[:50], "|", author)

            cursor.execute(
                """
                INSERT INTO wired_articles (title, url, description, author, scraped_at, source)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
                """,
                (title, url, description, author, scraped_at, source),
            )

            inserted_count += 1

        except Exception as e:
            print("ERROR INSERT:", e)
            raise  # biar Prefect kasih error asli

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Inserted {inserted_count} articles to database")
    return inserted_count


@flow(name="wired-pipeline", log_prints=True)
def wired_pipeline():
    """
    Prefect Pipeline DAG:
    1. Fetch articles from API
    2. Transform article dates
    3. Load to PostgreSQL
    """
    print("=" * 60)
    print("Starting Wired Articles Pipeline (Prefect)")
    print("=" * 60)

    articles = fetch_from_json()
    transformed_articles = transform_articles(articles)
    inserted_count = load_to_database(transformed_articles)

    print("=" * 60)
    print(f"Pipeline completed! Inserted {inserted_count} articles.")
    print("=" * 60)

    return {
        "status": "success",
        "articles_fetched": len(articles),
        "articles_inserted": inserted_count,
    }


if __name__ == "__main__":
    wired_pipeline()

