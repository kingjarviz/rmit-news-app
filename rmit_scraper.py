# rmit_scraper.py - Enhanced with Real Date Scraping
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import time
import re
import os

class RMITLiveScraper:
    def __init__(self):
        self.base_url = "https://www.rmit.edu.au"
        self.news_urls = {
            "all_news": "https://www.rmit.edu.au/news/all-news",
            "technology": "https://www.rmit.edu.au/news/technology", 
            "science": "https://www.rmit.edu.au/news/science"
        }
    
    def scrape_rmit_news(self, category="all_news"):
        """Scrape real news from RMIT website with real dates"""
        try:
            url = self.news_urls.get(category, self.news_urls["all_news"])
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            print(f"📡 Fetching {category} news from: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = []
            
            # Try multiple scraping strategies
            articles = self.scrape_with_multiple_strategies(soup, category)
            
            print(f"🎯 Found {len(articles)} articles for {category}")
            return articles[:15]
            
        except Exception as e:
            print(f"❌ Error scraping {category}: {e}")
            return []
    
    def scrape_with_multiple_strategies(self, soup, category):
        """Use multiple strategies to find news articles"""
        articles = []
        strategies = [
            self.scrape_modern_news_layout,
            self.scrape_news_cards,
            self.scrape_article_tags,
            self.scrape_news_links,
        ]
        
        for strategy in strategies:
            try:
                found_articles = strategy(soup, category)
                if found_articles:
                    # Add new articles, avoiding duplicates
                    existing_links = {a.get('link', '').strip().lower() for a in articles}
                    for article in found_articles:
                        if article.get('link', '').strip().lower() not in existing_links:
                            articles.append(article)
                            existing_links.add(article.get('link', '').strip().lower())
                    if len(articles) >= 8:
                        break
            except Exception as e:
                print(f"Strategy failed: {e}")
                continue
        
        return articles
    
    def scrape_modern_news_layout(self, soup, category):
        """Scrape modern RMIT news layout"""
        articles = []
        
        # Look for news items in modern layout
        news_items = soup.find_all('div', class_=re.compile(r'news|card|item', re.I))
        
        for item in news_items[:12]:
            try:
                # Extract title
                title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'h5']) or item.find('a')
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                if not title or len(title) < 10:
                    continue
                
                # Extract link
                link = "#"
                link_elem = item.find('a')
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    if href.startswith('/'):
                        link = f"{self.base_url}{href}"
                    elif href.startswith('http'):
                        link = href
                
                # Extract summary
                summary = ""
                desc_elem = item.find(['p', 'div'], class_=re.compile(r'description|summary|excerpt', re.I))
                if desc_elem:
                    summary = desc_elem.get_text(strip=True)
                
                if not summary:
                    # Try to get first paragraph
                    first_p = item.find('p')
                    if first_p:
                        summary = first_p.get_text(strip=True)
                
                if not summary:
                    summary = f"Latest news from RMIT University"
                
                # Clean up summary
                summary = re.sub(r'\s+', ' ', summary)
                if len(summary) > 200:
                    summary = summary[:197] + "..."
                
                # Extract date - this is the key fix
                date_text = self.extract_date_from_element(item)
                days_ago = self.calculate_days_ago(date_text)
                
                # Detect category
                detected_category = self.detect_category(title, summary, category)
                
                article_data = {
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": (datetime.now() - timedelta(days=days_ago)).strftime("%a, %d %b %Y %H:%M:%S GMT"),
                    "days_ago": days_ago,
                    "category": detected_category,
                    "source": "live_rmit"
                }
                
                articles.append(article_data)
                
            except Exception as e:
                continue
        
        return articles
    
    def extract_date_from_element(self, element):
        """Extract date text from HTML element using CSS selectors + regex fallbacks."""
        # Prefer CSS selectors; BeautifulSoup supports these via .select_one()
        selectors = [
            'time[datetime]', 'time', '.date', '.published',
            '.timestamp', '.news-date', '.card-date', '[datetime]'
        ]
        for sel in selectors:
            node = element.select_one(sel)
            if node:
                # Prefer machine-readable datetime
                dt = node.get('datetime') or node.get_text(strip=True)
                if dt:
                    return dt

        # Regex fallback on all visible text
        text = element.get_text(" ", strip=True)

        patterns = [
            r'\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',   # 5 Feb 2025
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b', # Feb 5, 2025
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',                                                     # 05/02/2025
            r'\b\d{4}-\d{2}-\d{2}\b'                                                          # 2025-02-05
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m: 
                return m.group(0)

        return None

    
    def calculate_days_ago(self, date_text):
        """Calculate how many days ago a date is; robust to multiple formats."""
        if not date_text:
            return 0

        s = date_text.strip()
        # Remove ordinal suffixes (1st, 2nd, 3rd, 4th …)
        s = re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', s, flags=re.IGNORECASE)
        s = s.replace('\xa0', ' ').replace('–', '-').strip()

        fmts = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d %b %Y',
            '%d %B %Y',
            '%b %d, %Y',
            '%B %d, %Y',
        ]
        for fmt in fmts:
            try:
                parsed = datetime.strptime(s, fmt)
                return max(0, (datetime.now() - parsed).days)
            except ValueError:
                pass

        # Try ISO-like substring if present
        m = re.search(r'(\d{4}-\d{2}-\d{2})', s)
        if m:
            try:
                parsed = datetime.strptime(m.group(1), '%Y-%m-%d')
                return max(0, (datetime.now() - parsed).days)
            except Exception:
                pass

        return 0

    
    def scrape_news_cards(self, soup, category):
        """Look for news cards"""
        articles = []
        card_selectors = [
            '[data-component="card"]',
            '.card',
            '.news-card',
            '.news-item',
            '.listing-item'
        ]
        
        for selector in card_selectors:
            cards = soup.select(selector)
            for card in cards[:8]:
                article = self.extract_from_card(card, category)
                if article:
                    articles.append(article)
            if articles:
                break
        return articles
    
    def scrape_article_tags(self, soup, category):
        """Look for article tags"""
        articles = []
        articles_html = soup.find_all('article')
        for article_html in articles_html[:8]:
            article = self.extract_from_card(article_html, category)
            if article:
                articles.append(article)
        return articles
    
    def scrape_news_links(self, soup, category):
        """Look for news links"""
        articles = []
        news_links = soup.find_all('a', href=re.compile(r'/news/'))
        for link in news_links[:12]:
            article = self.extract_from_link(link, category)
            if article:
                articles.append(article)
        return articles
    
    def extract_from_card(self, card, category):
        """Extract article data from a card element"""
        try:
            # Title extraction
            title = None
            title_elements = card.find_all(['h1', 'h2', 'h3', 'h4'])
            for elem in title_elements:
                if elem.get_text(strip=True):
                    title = elem.get_text(strip=True)
                    break
            
            if not title:
                link_elem = card.find('a')
                if link_elem and link_elem.get_text(strip=True):
                    title = link_elem.get_text(strip=True)
            
            if not title or len(title) < 10:
                return None
            
            title = re.sub(r'\s+', ' ', title).strip()
            
            # Link extraction
            link = "#"
            link_elem = card.find('a')
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                if href.startswith('/'):
                    link = f"{self.base_url}{href}"
                elif href.startswith('http'):
                    link = href
            
            # Summary extraction
            summary = ""
            paragraphs = card.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 30:
                    summary = text
                    break
            
            if not summary:
                all_text = card.get_text(strip=True)
                if title in all_text:
                    all_text = all_text.replace(title, '').strip()
                if len(all_text) > 50:
                    summary = all_text[:150] + "..." if len(all_text) > 150 else all_text
            
            if not summary:
                summary = f"Latest {category} news from RMIT University"
            else:
                summary = re.sub(r'\s+', ' ', summary)
                if len(summary) > 200:
                    summary = summary[:197] + "..."
            
            # Extract date
            date_text = self.extract_date_from_element(card)
            days_ago = self.calculate_days_ago(date_text)
            
            # Detect category
            detected_category = self.detect_category(title, summary, category)
            
            return {
                "title": title,
                "link": link,
                "summary": summary,
                "published": (datetime.now() - timedelta(days=days_ago)).strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "days_ago": days_ago,
                "category": detected_category,
                "source": "live_rmit"
            }
            
        except Exception as e:
            return None
    
    def extract_from_link(self, link_elem, category):
        """Extract article data from a link element"""
        try:
            title = link_elem.get_text(strip=True)
            if not title or len(title) < 10:
                return None
            
            title = re.sub(r'\s+', ' ', title).strip()
            
            href = link_elem.get('href', '#')
            if href.startswith('/'):
                link = f"{self.base_url}{href}"
            elif href.startswith('http'):
                link = href
            
            summary = f"Recent {category} news from RMIT University"
            
            # Try to extract date from parent element
            date_text = self.extract_date_from_element(link_elem.parent)
            days_ago = self.calculate_days_ago(date_text)
            
            detected_category = self.detect_category(title, summary, category)
            
            return {
                "title": title,
                "link": link,
                "summary": summary,
                "published": (datetime.now() - timedelta(days=days_ago)).strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "days_ago": days_ago,
                "category": detected_category,
                "source": "live_rmit"
            }
            
        except Exception as e:
            return None
    
    def detect_category(self, title, summary, original_category):
        """Smart category detection with UI-friendly fallback."""
        text = (title + " " + summary).lower()

        tech_keywords = [
            'ai', 'computer', 'software', 'tech', 'cyber', 'data', 'digital',
            'programming', 'algorithm', 'machine learning', 'robot', 'engineering'
        ]
        science_keywords = [
            'science', 'research', 'lab', 'study', 'physics', 'chemistry',
            'biology', 'astronomy', 'environment', 'publication', 'experiment'
        ]

        if any(k in text for k in tech_keywords):
            return "Technology"
        if any(k in text for k in science_keywords):
            return "Science"

        # Fallback: map original category slug to UI label
        map_ui = {
            'all_news': 'All News',
            'technology': 'Technology',
            'science': 'Science',
        }
        return map_ui.get(str(original_category).lower(), 'All News')

    
    def fetch_all_news(self):
        """Fetch news from both categories"""
        all_articles = []
        categories = ["all_news", "technology", "science"]
        
        for category in categories:
            try:
                print(f"🔄 Fetching {category} news...")
                articles = self.scrape_rmit_news(category)
                all_articles.extend(articles)
                time.sleep(2)  # Be respectful to the server
            except Exception as e:
                print(f"❌ Failed to fetch {category}: {e}")
                continue
        
        # Remove duplicates (use title + link as a stable key)
        seen = set()
        unique_articles = []

        for article in all_articles:
            link = article.get('link', '').strip().lower()
            if link and link not in seen:
                seen.add(link)
                unique_articles.append(article)

        print(f"📊 Total unique articles collected: {len(unique_articles)}")

        # If we have very few articles, try one more strategy
        # Fallback: scrape /news for extra links if we found very few
        if len(unique_articles) < 3:
            try:
                resp = requests.get("https://www.rmit.edu.au/news", timeout=15)
                soup = BeautifulSoup(resp.content, "html.parser")
                news_links = soup.find_all('a', href=re.compile(r'/news/'))
                for link in news_links[:10]:
                    extra = self.extract_from_link(link, "all_news")
                    if not extra:
                        continue
                    key = (extra.get('title','').strip().lower(), extra.get('link','').strip().lower())
                    if key not in seen:
                        seen.add(key)
                        unique_articles.append(extra)
            except Exception as e:
                print(f"Alternative approach failed: {e}")

        return unique_articles[:15]

# Cache functions
def save_news_cache(articles):
    try:
        with open("news_cache.json", "w", encoding="utf-8") as f:
            json.dump({
                "articles": articles,
                "last_updated": datetime.now().isoformat(),
                "source": "enhanced_rmit_scraper",
                "total_articles": len(articles)
            }, f, indent=2, ensure_ascii=False)
        print("💾 News cache saved successfully")
    except Exception as e:
        print(f"❌ Error saving cache: {e}")

def load_news_cache():
    try:
        if os.path.exists("news_cache.json"):
            with open("news_cache.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                last_updated = datetime.fromisoformat(data["last_updated"])
                if (datetime.now() - last_updated).seconds < 3600:
                    print("📁 Using cached news data")
                    return data["articles"]
    except Exception as e:
        print(f"❌ Error loading cache: {e}")
    return None

def get_live_news():
    cached_articles = load_news_cache()
    if cached_articles and len(cached_articles) >= 3:
        return cached_articles
    else:
        print("🌐 Fetching LIVE news from RMIT website")
        scraper = RMITLiveScraper()
        live_articles = scraper.fetch_all_news()
        if live_articles:
            save_news_cache(live_articles)
        return live_articles