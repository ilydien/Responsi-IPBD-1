import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class WiredScraper:
    def __init__(self):
        self.base_url = "https://www.wired.com"
        self.session_id = f"wired_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.articles = []
        self.output_dir = Path("data")
        self.output_dir.mkdir(exist_ok=True)

    def setup_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        return driver

    def scrape_wired(self):
        driver = None
        try:
            print("Setting up Chrome driver...")
            driver = self.setup_driver()
            
            print(f"Navigating to {self.base_url}...")
            driver.get(self.base_url)
            
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            print("Waiting for articles to load...")
            driver.implicitly_wait(10)
            
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            article_elements = self._find_articles(soup)
            
            print(f"Found {len(article_elements)} article elements")
            
            for article_elem in article_elements[:55]:
                article_data = self._extract_article_data(article_elem, soup)
                if article_data and article_data.get('title'):
                    self.articles.append(article_data)
                    print(f"Extracted: {article_data['title'][:50]}...")
            
            if len(self.articles) < 50:
                print(f"Only found {len(self.articles)} articles, trying alternative method...")
                self._scrape_alternative(driver, soup)
            
            print(f"Total articles scraped: {len(self.articles)}")
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if driver:
                driver.quit()
    
    def _find_articles(self, soup):
        selectors = [
            'article',
            '[data-testid="SummaryItemResource"]',
            '.summary-item',
            '.post-preview',
            '.BaseCard',
            'a.summary-item__link',
            '[class*="summary-item"]',
            '[class*="SummaryItem"]',
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                print(f"Found {len(elements)} elements with selector: {selector}")
                return elements
        
        return soup.find_all('article')[:60]

    def _extract_article_data(self, article_elem, soup):
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
        
        title = ""
        url = ""
        description = ""
        author = ""
        
        try:
            link_elem = article_elem.find('a') or article_elem
            if link_elem:
                url = link_elem.get('href', '')
                if url and not url.startswith('http'):
                    url = self.base_url + url
                
                title_elem = article_elem.find(['h2', 'h3', 'h4']) or article_elem.find(['span', 'p'], class_=lambda x: x and ('title' in x.lower() or 'headline' in x.lower()))
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    title = link_elem.get_text(strip=True) if link_elem else ""
            
            if not title:
                title_elem = article_elem.select_one('[class*="title"], [class*="headline"], span')
                if title_elem:
                    title = title_elem.get_text(strip=True)
            
            desc_elem = article_elem.select_one('[class*="description"], [class*="dek"], [class*="summary"], p')
            if desc_elem:
                description = desc_elem.get_text(strip=True)
            
            author_elem = article_elem.select_one('[class*="author"], [class*="byline"], [class*="creator"]')
            if author_elem:
                author_text = author_elem.get_text(strip=True)
                if author_text and not author_text.lower().startswith('by'):
                    author = f"By{author_text}"
                else:
                    author = author_text
        except Exception as e:
            print(f"Error extracting article data: {e}")
        
        if not title:
            return None
        
        return {
            "title": title[:500] if title else "",
            "url": url[:2000] if url else "",
            "description": description[:1000] if description else "",
            "author": author[:200] if author else "",
            "scraped_at": timestamp,
            "source": "Wired.com"
        }

    def _scrape_alternative(self, driver, soup):
        print("Trying alternative scraping with page scrolling...")
        
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            import time
            time.sleep(2)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        links = soup.select('a[href*="/story/"], a[href*="/article/"]')
        
        for link in links[:60]:
            try:
                title = link.get_text(strip=True)
                if title and len(title) > 10:
                    url = link.get('href', '')
                    if url and not url.startswith('http'):
                        url = self.base_url + url
                    
                    parent = link.find_parent(['article', 'div', 'li'])
                    description = ""
                    author = ""
                    
                    if parent:
                        desc_elem = parent.select_one('p, [class*="description"], [class*="dek"]')
                        if desc_elem:
                            description = desc_elem.get_text(strip=True)
                        
                        author_elem = parent.select_one('[class*="author"], [class*="byline"]')
                        if author_elem:
                            author = author_elem.get_text(strip=True)
                    
                    if parent and not any(a['url'] == url for a in self.articles):
                        self.articles.append({
                            "title": title[:500],
                            "url": url[:2000],
                            "description": description[:1000],
                            "author": author[:200] if author else "",
                            "scraped_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f'),
                            "source": "Wired.com"
                        })
            except Exception as e:
                continue

    def save_to_json(self):
        if not self.articles:
            print("No articles to save!")
            return None
        
        output_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "articles_count": len(self.articles),
            "articles": self.articles[:50]
        }
        
        filename = f"wired_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(self.articles)} articles to {filepath}")
        return str(filepath)


def main():
    scraper = WiredScraper()
    scraper.scrape_wired()
    output_file = scraper.save_to_json()
    
    if output_file:
        print(f"Scraping completed! Output: {output_file}")
        return 0
    else:
        print("Scraping failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())