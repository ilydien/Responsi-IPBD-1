import csv
import json
import random
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
]


def get_random_user_agent():
    return random.choice(USER_AGENTS)


def create_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(f"user-agent={get_random_user_agent()}")
    
    driver = webdriver.Chrome(options=options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
        """
    })
    
    return driver


def human_scroll(driver, min_scrolls=2, max_scrolls=4):
    """Human-like scrolling with random delays"""
    for _ in range(random.randint(min_scrolls, max_scrolls)):
        scroll_amount = random.randint(300, 700)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
        time.sleep(random.uniform(0.8, 1.5))


def random_mouse_move(driver):
    """Random mouse movement to simulate human"""
    try:
        action = ActionChains(driver)
        x = random.randint(100, 500)
        y = random.randint(100, 500)
        action.move_by_offset(x, y)
        action.perform()
    except:
        pass


def safe_delay(min_sec=1, max_sec=3):
    """Random safe delay between actions"""
    time.sleep(random.uniform(min_sec, max_sec))


def get_description(driver):
    selectors = [
        "//meta[@name='description']",
        "//meta[@property='og:description']",
        "//*[contains(@class, 'dek')]",
        "//*[contains(@class, 'summary')]",
    ]
    
    for selector in selectors:
        try:
            elem = driver.find_element(By.XPATH, selector)
            if selector.startswith("//meta"):
                desc = elem.get_attribute("content")
            else:
                desc = elem.text
            if desc and desc.strip():
                return desc.strip()
        except:
            continue
    
    try:
        paragraphs = driver.find_elements(By.CSS_SELECTOR, "article p, .body-content p")
        if paragraphs:
            return paragraphs[0].text.strip()[:300]
    except:
        pass
    
    return ""


def get_author(driver):
    selectors = [
        "//a[contains(@href, '/author/')]",
        "//*[@rel='author']",
        "//*[contains(@class, 'author')]",
        "//*[contains(text(), 'By ')]",
    ]
    
    for selector in selectors:
        try:
            elem = driver.find_element(By.XPATH, selector)
            text = elem.text.strip()
            if text:
                if not text.startswith("By "):
                    text = "By " + text
                return text
        except:
            continue
    
    return ""


CATEGORY_URLS = [
    "https://www.wired.com/category/security/",
    "https://www.wired.com/category/science/",
    "https://www.wired.com/category/business/",
    "https://www.wired.com/category/culture/",
    "https://www.wired.com/category/gear/",
]


def collect_article_links(driver):
    all_urls = []
    
    for cat_url in CATEGORY_URLS:
        print(f"\n[COLLECT] Getting links from: {cat_url}")
        driver.get(cat_url)
        safe_delay(3, 5)
        
        human_scroll(driver, 3, 5)
        safe_delay(1, 2)
        
        random_mouse_move(driver)
        
        link_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/story/')]")
        count_before = len(all_urls)
        
        for elem in link_elements:
            try:
                url = elem.get_attribute("href")
                if url and "/story/" in url and url not in all_urls and url.startswith("http"):
                    all_urls.append(url)
            except:
                continue
        
        print(f"   +{len(all_urls) - count_before} links (total: {len(all_urls)})")
        
        if len(all_urls) >= 80:
            break
        
        safe_delay(2, 4)
    
    return all_urls[:80]


def scrape_articles(driver, urls):
    articles_data = []
    
    print(f"\n[SCRAPE] Processing {len(urls)} articles...\n")
    
    for i, url in enumerate(urls, start=1):
        try:
            driver.get(url)
            safe_delay(2, 4)
            
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            
            random_mouse_move(driver)
            safe_delay(0.5, 1)
            
            try:
                title = driver.find_element(By.TAG_NAME, "h1").text.strip()
            except:
                title = ""
            
            description = get_description(driver)
            author = get_author(driver)
            
            articles_data.append({
                "title": title,
                "url": url,
                "description": description if description else "",
                "author": author if author else "By Wired Staff",
                "scraped_at": datetime.now().isoformat(),
                "source": "Wired.com",
            })
            
            has_desc = "[OK]" if description else "[NO]"
            has_auth = "[OK]" if author else "[NO]"
            print(f"[{i:02d}/{len(urls)}] {has_desc} {has_auth} | {title[:50]}")
            
            if i % 10 == 0:
                new_ua = get_random_user_agent()
                driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": new_ua})
                print(f"    [INFO] Rotated User-Agent")
            
        except Exception as e:
            print(f"[{i:02d}] [ERR] {str(e)[:50]}")
            continue
    
    return articles_data


def save_results(articles_data):
    session_id = f"wired_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    output = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "articles_count": len(articles_data),
        "articles": articles_data,
    }
    
    Path("data").mkdir(exist_ok=True)
    
    with open("data/wired_articles.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print("[SAVE] JSON -> data/wired_articles.json")
    
    with open("data/wired_articles.csv", "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["title", "url", "description", "author", "scraped_at", "source"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for article in articles_data:
            writer.writerow(article)
    print("[SAVE] CSV -> data/wired_articles.csv")
    
    has_desc = sum(1 for a in articles_data if a["description"])
    has_auth = sum(1 for a in articles_data if a["author"])
    
    print(f"""
=======================================
        SCRAPE SUMMARY        
=======================================
  Total articles  : {len(articles_data)}
  With desc     : {has_desc}
  With author   : {has_auth}
=======================================
""")


def main():
    print("[START] Initializing Chrome...")
    driver = create_driver()
    
    try:
        urls = collect_article_links(driver)
        print(f"\n[OK] Collected {len(urls)} unique article URLs")
        
        articles = scrape_articles(driver, urls)
        save_results(articles)
        
    finally:
        driver.quit()
        print("[END] Done!")


if __name__ == "__main__":
    main()