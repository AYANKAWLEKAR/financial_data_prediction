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
    # Demo: if you have article data from the scraper it should contain a column
    # named 'published_date' (or similar) and a 'headline' column. Below
    # we provide two helper functions:
    # - set_article_index_to_datetime: parses published_date and sets it as the index
    # - combine_headlines_with_financial: merges headlines into the financial df


def set_article_index_to_datetime(article_df: pd.DataFrame, date_col: str = "published_date") -> pd.DataFrame:
    """Parse an article DataFrame's date column and set it as a DatetimeIndex.

    Args:
        article_df: DataFrame with at least a date column or a datetime-like index.
        date_col: Name of the column containing the publish datetime (default 'published_date').

    Returns:
        A copy of article_df with a sorted DatetimeIndex.
    """
    if article_df is None or article_df.empty:
        return pd.DataFrame()

    df = article_df.copy()

    # If the date column exists, parse it and set as index. Otherwise try to
    # interpret the existing index as datetime.
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        # drop rows we couldn't parse
        df = df.loc[~df[date_col].isna()].copy()
        df = df.set_index(date_col)
    else:
        # try to coerce the index
        df.index = pd.to_datetime(df.index, errors="coerce")
        df = df.loc[~df.index.isna()].copy()

    # Normalize index to timezone-naive (keeping absolute moment) and sort
    try:
        df.index = df.index.tz_convert(None)
    except Exception:
        # index may already be tz-naive
        pass

    df = df.sort_index()
    return df


def combine_headlines_with_financial(financial_df: pd.DataFrame,
                                    article_df: pd.DataFrame,
                                    date_col: str = "published_date",
                                    headline_col: str = "headline",
                                    max_days_diff: int = 1) -> pd.DataFrame:
    """Combine headlines into financial_df by matching article publish dates
    to the financial dates (using nearest-date matching).

    Args:
        financial_df: Financial DataFrame with a DatetimeIndex (e.g., yfinance history).
        article_df: Article DataFrame with a publish datetime column or DatetimeIndex.
        date_col: Name of the publish datetime column in article_df (default 'published_date').
        headline_col: Name of the headline column in article_df (default 'headline').
        max_days_diff: Maximum days difference to allow when matching nearest article.

    Returns:
        A copy of financial_df with an added 'headlines' column containing the
        joined headlines for the matched article date (or NaN if none within tolerance).
    """
    if financial_df is None or financial_df.empty:
        return pd.DataFrame()

    fin = financial_df.copy()
    # Ensure financial index is DatetimeIndex and sorted ascending
    fin.index = pd.to_datetime(fin.index)
    fin = fin.sort_index()

    # Prepare articles
    art = set_article_index_to_datetime(article_df, date_col=date_col)
    if art.empty:
        # no articles -> add empty headlines column
        fin = fin.copy()
        fin["headlines"] = pd.NA
        return fin

    # Aggregate multiple headlines on the same calendar day into a single string
    art_daily = art.copy()
    art_daily["_date"] = art_daily.index.normalize()
    # keep the original headline column; if missing, create empty strings
    if headline_col not in art_daily.columns:
        art_daily[headline_col] = ""

    agg = (
        art_daily.groupby("_date")[headline_col]
        .apply(lambda s: " || " .join(s.dropna().astype(str)))
        .reset_index()
        .rename(columns={"_date": "date", headline_col: "headlines"})
    )

    # Make sure both sides are sorted and datetime
    agg["date"] = pd.to_datetime(agg["date"])
    agg = agg.sort_values("date")

    fin_reset = fin.reset_index()
    left_date_col = fin_reset.columns[0]
    fin_reset = fin_reset.sort_values(left_date_col)

    # merge_asof for nearest-match; tolerance controls how far we allow the match
    merged = pd.merge_asof(
        fin_reset,
        agg,
        left_on=left_date_col,
        right_on="date",
        direction="nearest",
        tolerance=pd.Timedelta(days=max_days_diff),
    )

    # Wherever no match was found merged['headlines'] will be NaN
    # restore index and return
    merged = merged.set_index(left_date_col)
    # If index had a name, keep it; otherwise ensure it's a DatetimeIndex
    merged.index = pd.to_datetime(merged.index)

    # If headlines column doesn't exist for any reason, create it
    if "headlines" not in merged.columns:
        merged["headlines"] = pd.NA

    return merged


if __name__ == "__main__":
    # quick self-test / demo using synthetic article rows (avoids calling the
    # scraper which may have a different signature in this repo)
    sample_data = fetch_financial_data("AAPL", period="7d", interval="1d")
    sample_data["RSI"] = calculate_rsi(sample_data)

    # create two sample articles
    now = pd.Timestamp.now().normalize()
    sample_articles = pd.DataFrame(
        {
            "published_date": [
                (now - pd.Timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                (now - pd.Timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
            ],
            "headline": ["Company reports strong earnings", "New product announced"],
        }
    )

    sample_articles = set_article_index_to_datetime(sample_articles)
    combined = combine_headlines_with_financial(sample_data, sample_articles, max_days_diff=2)
    print(combined[["Close", "RSI", "headlines"]].tail(10))


   
   