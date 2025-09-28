import yfinance
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import finhub_scraper as scraper

import transformers

#recreate this paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC9955765/

def fetch_financial_data(ticker: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch historical financial data for a given ticker."""
    try:
        stock = yfinance.Ticker(ticker)
        hist = stock.history(period=period, interval=interval)
        return hist
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()
def plot_financial_data(data: pd.DataFrame, ticker: str):
    """Plot closing prices of the financial data."""
    if data.empty:
        print("No data to plot.")
        return
    
    plt.figure(figsize=(10, 5))
    sns.lineplot(data=data, x=data.index, y='Close')
    plt.title(f"{ticker} Closing Prices")
    plt.xlabel("Date")
    plt.ylabel("Closing Price (USD)")
    plt.grid(True)
    plt.show()

def calculate_rsi(data: pd.DataFrame, rsi_period: int =14)-> pd.Series:
    """Calculate the RSI for each day in the data"""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    avg_gain = gain.rolling(window=rsi_period, min_periods=1).mean()
    avg_loss = loss.rolling(window=rsi_period, min_periods=1).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

SAMPLE_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
sample_data=fetch_financial_data("AAPL", period="1mo", interval="1d")

sample_data['RSI'] = calculate_rsi(sample_data)

#sample_article_data=scraper.scrape_yahoo_finance_headlines("AAPL", days_back=30)

article_data=scraper.fetch_company_news_finhub("AAPL",days_back=30)


#goal is to merge two datasets so stock price at each date has sentiment score for that date or whichever is closest
#





if __name__ == "__main__":
    sample_data=fetch_financial_data("AAPL", period="1mo", interval="1d")
    sample_data['RSI'] = calculate_rsi(sample_data)
    sample_article_data=scraper.fetch_company_news_finhub("AAPL",days_back=30)


   
   