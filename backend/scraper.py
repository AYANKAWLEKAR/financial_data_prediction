import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin

def scrape_yahoo_finance_headlines(
    ticker: str, 
    days_back: int = 7,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    max_articles: int = 50
) -> List[Dict]:
    """
    Scrape Yahoo Finance article headlines for a given ticker within a time range.
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        days_back (int): Number of days to look back from today (default: 7)
        start_date (datetime, optional): Start date for scraping (overrides days_back)
        end_date (datetime, optional): End date for scraping (default: today)
        max_articles (int): Maximum number of articles to return (default: 50)
    
    Returns:
        List[Dict]: List of dictionaries containing headline info:
            - title: Article headline
            - url: Full article URL
            - published_time: Published time string
            - source: News source
            - summary: Brief summary if available
    """
    
    # Set up date range
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=days_back)
    
    # Yahoo Finance news URL for the ticker
    base_url = f"https://finance.yahoo.com/quote/{ticker.upper()}/news"
    
    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    articles = []
    
    try:
        print(f"Scraping Yahoo Finance news for {ticker.upper()}...")
        
        # Make the request
        response = requests.get(base_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find news articles - Yahoo Finance uses various selectors
        # Try multiple selectors as Yahoo may change their layout
        article_selectors = [
            'li[data-testid="story-item"]',
            '.js-stream-content li',
            '[data-module="StreamItem"]',
            '.stream-item',
            'li.js-stream-content'
        ]
        
        news_items = []
        for selector in article_selectors:
            news_items = soup.select(selector)
            if news_items:
                print(f"Found {len(news_items)} articles using selector: {selector}")
                break
        
        if not news_items:
            # Fallback: look for any article-like containers
            news_items = soup.find_all(['article', 'div'], class_=re.compile(r'(story|article|news|item)', re.I))
            print(f"Using fallback selector, found {len(news_items)} potential articles")
        
        for item in news_items[:max_articles]:
            try:
                article_data = extract_article_info(item, ticker)
                
                if article_data and is_within_date_range(article_data['published_time'], start_date, end_date):
                    articles.append(article_data)
                    
            except Exception as e:
                print(f"Error processing article: {e}")
                continue
        
        # Remove duplicates based on title
        seen_titles = set()
        unique_articles = []
        for article in articles:
            if article['title'] not in seen_titles:
                seen_titles.add(article['title'])
                unique_articles.append(article)
        
        print(f"Successfully scraped {len(unique_articles)} unique articles")
        return unique_articles
        
    except requests.RequestException as e:
        print(f"Error fetching Yahoo Finance page: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def extract_article_info(item, ticker: str) -> Optional[Dict]:
    """Extract article information from a news item element."""
    try:
        article_data = {
            'title': '',
            'url': '',
            'published_time': '',
            'source': '',
            'summary': ''
        }
        
        # Try to find the title/headline
        title_selectors = [
            'h3 a',
            'h2 a', 
            'a h3',
            'a h2',
            '.js-content-viewer a',
            'a[data-testid="story-title"]',
            '.story-title a'
        ]
        
        title_element = None
        for selector in title_selectors:
            title_element = item.select_one(selector)
            if title_element:
                break
        
        if not title_element:
            # Try to find any link that might be the title
            title_element = item.find('a')
        
        if title_element:
            article_data['title'] = title_element.get_text(strip=True)
            # Get the URL
            href = title_element.get('href', '')
            if href:
                if href.startswith('/'):
                    article_data['url'] = f"https://finance.yahoo.com{href}"
                elif href.startswith('http'):
                    article_data['url'] = href
        
        # Try to find publish time
        time_selectors = [
            'time',
            '.timestamp',
            '.time',
            '[data-testid="story-timestamp"]',
            '.publish-time'
        ]
        
        for selector in time_selectors:
            time_element = item.select_one(selector)
            if time_element:
                article_data['published_time'] = time_element.get_text(strip=True)
                break
        
        # Try to find source
        source_selectors = [
            '.source',
            '.provider',
            '[data-testid="story-provider"]',
            '.attribution'
        ]
        
        for selector in source_selectors:
            source_element = item.select_one(selector)
            if source_element:
                article_data['source'] = source_element.get_text(strip=True)
                break
        
        # Try to find summary/description
        summary_selectors = [
            '.summary',
            '.description',
            'p',
            '.excerpt'
        ]
        
        for selector in summary_selectors:
            summary_element = item.select_one(selector)
            if summary_element:
                summary_text = summary_element.get_text(strip=True)
                if len(summary_text) > 20:  # Only use if it's substantial
                    article_data['summary'] = summary_text[:200] + '...' if len(summary_text) > 200 else summary_text
                    break
        
        # Only return if we have at least a title
        if article_data['title']:
            return article_data
        
    except Exception as e:
        print(f"Error extracting article info: {e}")
    
    return None

def is_within_date_range(published_time: str, start_date: datetime, end_date: datetime) -> bool:
    """
    Check if the published time is within the specified date range.
    Note: Yahoo Finance time formats can vary, so this does basic parsing.
    """
    if not published_time:
        return True  # Include articles without timestamps
    
    try:
        # Common time formats on Yahoo Finance: sourceed by chatgpt
        time_patterns = [
            r'(\d+)\s*hour[s]?\s*ago',
            r'(\d+)\s*minute[s]?\s*ago',
            r'(\d+)\s*day[s]?\s*ago',
            r'(\d+)\s*week[s]?\s*ago'
        ]
        
        published_time_lower = published_time.lower()
        
        # Check for "X hours/minutes/days ago" format
        for pattern in time_patterns:
            match = re.search(pattern, published_time_lower)
            if match:
                value = int(match.group(1))
                if 'hour' in pattern or 'minute' in pattern:
                    article_date = datetime.now() - timedelta(hours=value if 'hour' in pattern else 0, 
                                                            minutes=value if 'minute' in pattern else 0)
                elif 'day' in pattern:
                    article_date = datetime.now() - timedelta(days=value)
                elif 'week' in pattern:
                    article_date = datetime.now() - timedelta(weeks=value)
                
                return start_date <= article_date <= end_date
        
        # If we can't parse the date, include the article
        return True
        
    except Exception:
        return True



if __name__ == "__main__":
    # Example 1: Get headlines from the last 3 days
    ticker = "AAPL"
    headlines = scrape_yahoo_finance_headlines(ticker, days_back=20)
    
    # Example 2: Get headlines within a specific date range
    # start = datetime(2024, 1, 1)
    # end = datetime(2024, 1, 31)
    # headlines = scrape_yahoo_finance_headlines("TSLA", start_date=start, end_date=end)
    # display_articles(headlines, "TSLA")
    
    # Example 3: Get more recent headlines
    # headlines = scrape_yahoo_finance_headlines("MSFT", days_back=1, max_articles=10)
    # display_articles(headlines, "MSFT")