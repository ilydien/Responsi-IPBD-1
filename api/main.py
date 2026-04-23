import json
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime


app = FastAPI(title="Wired Articles API", version="1.0.0")

DATA_DIR = Path("data")


class Article(BaseModel):
    title: str
    url: str
    description: Optional[str] = ""
    author: Optional[str] = ""
    scraped_at: str
    source: str = "Wired.com"


class SessionData(BaseModel):
    session_id: str
    timestamp: str
    articles_count: int
    articles: List[Article]


def find_latest_json_file() -> Optional[Path]:
    if not DATA_DIR.exists():
        return None
    
    json_files = list(DATA_DIR.glob("wired_articles_*.json"))
    if not json_files:
        return None
    
    return max(json_files, key=lambda p: p.stat().st_mtime)


def load_articles_from_json() -> List[Article]:
    json_file = find_latest_json_file()
    
    if not json_file:
        raise HTTPException(status_code=404, detail="No scraped data found. Please run scraper first.")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = []
    for article_data in data.get('articles', []):
        articles.append(Article(**article_data))
    
    return articles


@app.get("/")
def root():
    return {
        "message": "Wired Articles API",
        "version": "1.0.0",
        "endpoints": {
            "articles": "/articles",
            "articles_count": "/articles/count",
            "latest_file": "/latest"
        }
    }


@app.get("/articles", response_model=List[Article])
def get_articles():
    return load_articles_from_json()


@app.get("/articles/count")
def get_articles_count():
    articles = load_articles_from_json()
    return {"count": len(articles)}


@app.get("/latest")
def get_latest_session():
    json_file = find_latest_json_file()
    
    if not json_file:
        raise HTTPException(status_code=404, detail="No scraped data found.")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)