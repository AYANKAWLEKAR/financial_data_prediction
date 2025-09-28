import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import finnhub


EXAMPLE_TICKER = "AAPL"
os.environ['FINHUB_API_KEY'] = "d3c9651r01qu125a70cgd3c9651r01qu125a70d0"

def fetch_company_news_finhub(ticker: str, _from_date: str, _end_date:str, days_back:Optional[int]=7 ) -> pd.DataFrame:
    """Fetch company news from Finnhub for the given ticker and days back.

    Args:
        ticker: Stock ticker (e.g., 'AAPL').
        days_back: Number of days in the past to include (default 7).
        api_key: Finnhub API key. If not provided, will read from environment variable
                 FINNHUB_API_KEY.
        timeout: Request timeout in seconds.

    Returns:
        pandas.DataFrame with columns: ['published_date', 'headline', 'url', 'summary', 'source', 'related', 'image']

    Raises:
        ValueError: if API key is not provided.
        requests.RequestException: if the HTTP request fails.
    """

    api_key =  os.getenv("FINNHUB_API_KEY")
    

    symbol = ticker.upper()
    today = datetime.today()
    if days_back is None:
        start_date=_from_date
        end_date=_end_date
    start_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    

    url = "https://finnhub.io/api/v1/company-news"
    params = {"symbol": symbol, "from": from_date, "to": to_date, "token": api_key}
    client=finnhub.Client(api_key)
    rows={"published_date": [],
                "headline":[],
                "url":[],
                "summary": [],
                "source":[],
                "related": [],
    }
    
    try:
        result=client.company_news(symbol, _from=from_date, to=to_date)
        for item in result:
            published = datetime.fromtimestamp(item.get("datetime")).strftime("%Y-%m-%d %H:%M:%S") if item.get("datetime") else None
            rows["published_date"].append(published)
            rows["headline"].append(item["headline"] or "")
            rows["url"].append(item["url"] or "")
            rows["summary"].append(item["summary"] or "")
            rows["source"].append(item["source"] or "")
            rows["related"].append(item["related"] or "")
            rows["image"].append(item["image"] or "")

        
    except Exception as e:
        print(f"Error fetching Finnhub news for {ticker}: {e}")
        raise

    df = pd.DataFrame(rows)
    # Sort newest first and return
    if "published_date" in df.columns:
        df = df.sort_values(by="published_date", ascending=False).reset_index(drop=True)

    return df




