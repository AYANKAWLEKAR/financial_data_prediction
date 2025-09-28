from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time


def scrape_yahoo_finance_news(ticker):
    """
    Scrapes news article headlines and published dates from Yahoo Finance
    for a given stock ticker using Selenium.

    Args:
        ticker (str): The stock ticker symbol (e.g., 'AAPL').

    Returns:
        list: A list of dictionaries, where each dictionary contains 'date' and 'headline'.
    """
    url = f"https://finance.yahoo.com/quote/{ticker.upper()}"
    news_data = []

    
    # Configure Chrome options to make the webdriver more reliable across environments
    options = webdriver.ChromeOptions()
    # Use the new headless mode when available; fallback will be handled by Chrome
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # A common user-agent to reduce automated-bot blocking
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    service = ChromeService(ChromeDriverManager().install())
    try:
        driver = webdriver.Chrome(service=service, options=options)
    except WebDriverException as e:
        # Provide a clearer error message if the driver fails to start
        print(f"Failed to start Chrome WebDriver: {e}")
        raise

    try:
        driver.get(url)

        # Wait for at least one of the common article containers to appear
        # We attempt multiple selectors to be robust to small layout changes.
        possible_article_selectors = [
            "li[data-testid='story-item']",
            "li.js-stream-content",
            "[data-module='StreamItem']",
            ".stream-item",
        ]

        # Wait until one of the selectors has at least one match (or timeout)
        found = False
        for sel in possible_article_selectors:
            try:
                WebDriverWait(driver, 12).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                found = True
                break
            except Exception:
                # try the next selector
                continue

        # If none of the specific selectors were found, continue — the fallback logic
        # below will attempt a broader search. We don't abort here because Yahoo
        # sometimes lazy-loads elements differently.

       
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2) # Wait for new content to load
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

      
        article_selectors = [
            'li[data-testid="story-item"]',
            '.js-stream-content li',
            '[data-module="StreamItem"]',
            '.stream-item',
            'li.js-stream-content'
        ]

        all_articles = []
        for selector in article_selectors:
            try:
                articles = driver.find_elements(By.CSS_SELECTOR, selector)
            except Exception:
                articles = []
            if articles:
                all_articles.extend(articles)
                break  # Use the first selector that finds articles

        if not all_articles:
            # Fallback: look for any article-like containers
            try:
                all_articles = driver.find_elements(
                    By.CSS_SELECTOR,
                    "[class*='story'], [class*='article'], [class*='news'], [class*='item']",
                )
            except Exception:
                all_articles = []


        print(f"Found {len(all_articles)} potential articles.")

        # Extract data from each article safely using XPath (prefer <time datetime>)
        for article in all_articles:
            try:
                # Try a set of headline selectors and take the first text we find
                headline_elements = article.find_elements(
                    By.CSS_SELECTOR,
                    "h3 a, h2 a, a h3, a h2, .js-content-viewer a, a[data-testid='story-title'], .story-title a, a",
                )
                date_elements = article.find_elements(
                    By.CSS_SELECTOR,
                    "time, .timestamp, .time, [data-testid='story-timestamp'], .publish-time",
                )

                headline = None
                date_text = None

                if headline_elements:
                    for elem in headline_elements:
                        text = elem.text.strip()
                        if text:
                            headline = text
                            break

                # Try a set of XPath expressions for date/time, ordered by preference
                date_xpaths = [
                    ".//time[@datetime]",
                    ".//time",
                    ".//*[contains(@data-testid,'story-timestamp')]",
                    ".//*[contains(@class,'timestamp')]",
                    ".//*[contains(@class,'time')]",
                    ".//span[contains(@aria-label,'ago') or contains(text(),'ago')]",
                ]

                for dx in date_xpaths:
                    try:
                        elems = article.find_elements(By.XPATH, dx)
                    except Exception:
                        elems = []
                    if not elems:
                        continue
                    # Prefer datetime attribute when present
                    found = False
                    for e in elems:
                        try:
                            dt = e.get_attribute("datetime")
                        except Exception:
                            dt = None
                        text = e.text.strip() if e.text else ""
                        if dt:
                            date_text = dt.strip()
                            found = True
                            break
                        if text:
                            date_text = text
                            found = True
                            break
                    if found:
                        break

                # As a final fallback, try to find a time element anywhere under the article
                if not date_text:
                    try:
                        t = article.find_element(By.XPATH, ".//time")
                        date_text = t.get_attribute("datetime") or t.text
                    except Exception:
                        date_text = None

                if headline:
                    date_text = date_text or "No Date"
                    news_data.append({"date": date_text, "headline": headline})

            except Exception:
                # Skip problematic articles
                continue

    except Exception as e:
        print(f"An error occurred during scraping: {e}")

    finally:
        driver.quit() 

    return news_data

# Example Usage:
# ticker_symbol = "AAPL"
# news_headlines = scrape_yahoo_finance_news(ticker_symbol)
#
# if news_headlines:
#     print(f"News Headlines for {ticker_symbol}:")
#     for item in news_headlines:
#         print(f"Date: {item['date']}, Headline: {item['headline']}")
# else:
#     print(f"Could not retrieve news headlines for {ticker_symbol}.")