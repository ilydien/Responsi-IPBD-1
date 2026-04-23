"""
Prefect DAG for Wired Articles Pipeline
"""
import json
from datetime import datetime
from typing import List, Dict, Any

import psycopg2
from prefect import flow, task
from sqlalchemy import create_engine, text
import requests


DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/wired_db"
API_URL = "http://localhost:8001"


@task(name="Get articles from API", retries=2)
def fetch_articles_from_api() -> List[Dict[str, Any]]:
    response = requests.get(f"{API_URL}/articles", timeout=30)
    response.raise_for_status()
    return response.json()


@task(name="Transform article dates", retries=1)
def transform_article_dates(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    transformed = []
    
    for article in articles:
        try:
            scraped_at = datetime.fromisoformat(article['scraped_at'].replace('Z', '+00:00'))
            article['scraped_at'] = scraped_at.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, KeyError):
            article['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        transformed.append(article)
    
    return transformed


@task(name="Create table if not exists", retries=3)
def create_table():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="wired_db",
        user="postgres",
        password="postgres"
    )
    
    cursor = conn.cursor()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS wired_articles (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        url TEXT,
        description TEXT,
        author TEXT,
        scraped_at TIMESTAMP,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    cursor.execute(create_table_sql)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_wired_articles_title ON wired_articles(title);
        CREATE INDEX IF NOT EXISTS idx_wired_articles_author ON wired_articles(author);
        CREATE INDEX IF NOT EXISTS idx_wired_articles_scraped_at ON wired_articles(scraped_at);
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return "Table created successfully"


@task(name="Insert articles to database", retries=3)
def insert_articles_to_db(articles: List[Dict[str, Any]]) -> int:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="wired_db",
        user="postgres",
        password="postgres"
    )
    
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for article in articles:
        try:
            cursor.execute("""
                INSERT INTO wired_articles (title, url, description, author, scraped_at, source)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                article.get('title', ''),
                article.get('url', ''),
                article.get('description', ''),
                article.get('author', ''),
                article.get('scraped_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                article.get('source', 'Wired.com')
            ))
            inserted_count += 1
        except Exception as e:
            print(f"Error inserting article: {e}")
            continue
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return inserted_count


@flow(name="Wired Articles Pipeline", log_prints=True)
def wired_articles_pipeline():
    print("Starting Wired Articles Pipeline...")
    
    articles = fetch_articles_from_api()
    print(f"Fetched {len(articles)} articles from API")
    
    transformed_articles = transform_article_dates(articles)
    print("Transformed article dates")
    
    create_table()
    print("Ensured table exists")
    
    inserted_count = insert_articles_to_db(transformed_articles)
    print(f"Inserted {inserted_count} articles to database")
    
    return {
        "status": "success",
        "articles_fetched": len(articles),
        "articles_inserted": inserted_count
    }


if __name__ == "__main__":
    from prefect import serve
    from prefect.server.schedules import Schedule
    
    wired_articles_pipeline()


from prefect import flow, task, run_deployment


@flow(name="Manual Wired Pipeline Run")
def run_pipeline():
    return wired_articles_pipeline()


if __name__ == "__main__":
    run_pipeline()