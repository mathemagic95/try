"""
Stock Sentiment Trend Monitor
Fetches recent news for a stock ticker, analyzes sentiment,
and recommends trend vs benchmark index.
"""

import html
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import nltk
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Download VADER lexicon on startup
nltk.download("vader_lexicon", quiet=True)

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# --- Ticker to Country/Benchmark Mapping ---

SUFFIX_BENCHMARK = {
    ".NS": {"country": "IN", "index": "^NSEI", "index_name": "NIFTY 50"},
    ".BO": {"country": "IN", "index": "^BSESN", "index_name": "BSE SENSEX"},
    ".L": {"country": "GB", "index": "^FTSE", "index_name": "FTSE 100"},
    ".TO": {"country": "CA", "index": "^GSPTSE", "index_name": "S&P/TSX"},
    ".AX": {"country": "AU", "index": "^AXJO", "index_name": "S&P/ASX 200"},
    ".PA": {"country": "FR", "index": "^FCHI", "index_name": "CAC 40"},
    ".DE": {"country": "DE", "index": "^GDAXI", "index_name": "DAX"},
    ".T": {"country": "JP", "index": "^N225", "index_name": "Nikkei 225"},
    ".HK": {"country": "HK", "index": "^HSI", "index_name": "Hang Seng"},
    ".SS": {"country": "CN", "index": "000001.SS", "index_name": "SSE Composite"},
    ".SZ": {"country": "CN", "index": "399001.SZ", "index_name": "SZSE Component"},
    ".KS": {"country": "KR", "index": "^KS11", "index_name": "KOSPI"},
    ".SA": {"country": "BR", "index": "^BVSP", "index_name": "Bovespa"},
    ".SW": {"country": "CH", "index": "^SSMI", "index_name": "SMI"},
}

DEFAULT_BENCHMARK = {"country": "US", "index": "^GSPC", "index_name": "S&P 500"}


def get_benchmark_for_ticker(ticker_symbol):
    """Determine the appropriate benchmark index for a given ticker."""
    upper = ticker_symbol.upper()
    for suffix, bench in SUFFIX_BENCHMARK.items():
        if upper.endswith(suffix.upper()):
            return bench
    return DEFAULT_BENCHMARK


def yahoo_chart_api(symbol, days=25):
    """Fetch historical price data from Yahoo Finance chart API."""
    end_ts = int(time.time())
    start_ts = end_ts - (days * 86400)
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?period1={start_ts}&period2={end_ts}&interval=1d"
    )
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    chart = data.get("chart", {}).get("result", [])
    if not chart:
        return None, None

    result = chart[0]
    timestamps = result.get("timestamp", [])
    closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
    meta = result.get("meta", {})
    name = meta.get("shortName") or meta.get("longName") or meta.get("symbol", symbol)

    dates = []
    prices = []
    for ts, price in zip(timestamps, closes):
        if price is not None:
            dates.append(datetime.fromtimestamp(ts).strftime("%Y-%m-%d"))
            prices.append(round(float(price), 2))

    return {"dates": dates, "prices": prices, "name": name}, meta


def fetch_google_news(query, days=15):
    """Fetch news articles from Google News RSS for the given query."""
    url = f"https://news.google.com/rss/search?q={query}+stock&hl=en&gl=US&ceid=US:en"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"Failed to fetch news: {e}", "articles": []}

    cutoff = datetime.now() - timedelta(days=days)
    articles = []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return {"error": "Failed to parse news feed", "articles": []}

    for item in root.iter("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")
        source_el = item.find("source")
        desc_el = item.find("description")

        title = html.unescape(title_el.text or "") if title_el is not None else ""
        link = link_el.text or "" if link_el is not None else ""
        source = source_el.text or "Unknown" if source_el is not None else "Unknown"

        # Parse published date
        try:
            published = parsedate_to_datetime(pub_el.text)
            published = published.replace(tzinfo=None)
        except Exception:
            published = datetime.now()

        if published < cutoff:
            continue

        # Clean description HTML
        desc_raw = desc_el.text or "" if desc_el is not None else ""
        desc_text = BeautifulSoup(desc_raw, "html.parser").get_text()

        articles.append(
            {
                "title": title,
                "summary": desc_text[:500],
                "link": link,
                "published": published.strftime("%Y-%m-%d %H:%M"),
                "source": source,
            }
        )

    articles.sort(key=lambda a: a["published"], reverse=True)
    return {"articles": articles[:50], "error": None}


def analyze_sentiment(articles):
    """Run VADER sentiment analysis on news articles."""
    sia = SentimentIntensityAnalyzer()
    results = []
    daily_scores = {}

    for article in articles:
        text = f"{article['title']}. {article['summary']}"
        scores = sia.polarity_scores(text)
        compound = scores["compound"]

        if compound >= 0.05:
            label = "Positive"
        elif compound <= -0.05:
            label = "Negative"
        else:
            label = "Neutral"

        date_str = article["published"][:10]

        if date_str not in daily_scores:
            daily_scores[date_str] = []
        daily_scores[date_str].append(compound)

        results.append(
            {
                **article,
                "sentiment_score": round(compound, 3),
                "sentiment_label": label,
            }
        )

    # Aggregate daily sentiment
    daily_avg = {}
    for date, scores in sorted(daily_scores.items()):
        daily_avg[date] = round(sum(scores) / len(scores), 3)

    # Overall metrics
    all_scores = [r["sentiment_score"] for r in results]
    if all_scores:
        avg_sentiment = round(sum(all_scores) / len(all_scores), 3)
        positive_pct = round(
            len([s for s in all_scores if s >= 0.05]) / len(all_scores) * 100, 1
        )
        negative_pct = round(
            len([s for s in all_scores if s <= -0.05]) / len(all_scores) * 100, 1
        )
        neutral_pct = round(100 - positive_pct - negative_pct, 1)
    else:
        avg_sentiment = 0
        positive_pct = negative_pct = neutral_pct = 0

    return {
        "articles": results,
        "daily_sentiment": daily_avg,
        "summary": {
            "avg_sentiment": avg_sentiment,
            "positive_pct": positive_pct,
            "negative_pct": negative_pct,
            "neutral_pct": neutral_pct,
            "total_articles": len(results),
        },
    }


def get_price_data(ticker_symbol, benchmark_symbol, days=15):
    """Fetch recent price data for the stock and its benchmark index."""
    try:
        stock_data, stock_meta = yahoo_chart_api(ticker_symbol, days=days + 10)
        bench_data, bench_meta = yahoo_chart_api(benchmark_symbol, days=days + 10)

        if not stock_data or not bench_data:
            return {"error": "Could not fetch price data"}

        # Build date-indexed lookups
        stock_by_date = dict(zip(stock_data["dates"], stock_data["prices"]))
        bench_by_date = dict(zip(bench_data["dates"], bench_data["prices"]))

        # Find common dates
        common = sorted(set(stock_by_date.keys()) & set(bench_by_date.keys()))
        common = common[-days:]  # Take last N days

        if len(common) < 2:
            return {"error": "Not enough overlapping trading days"}

        dates = common
        stock_prices = [stock_by_date[d] for d in dates]
        bench_prices = [bench_by_date[d] for d in dates]

        stock_return = (
            (stock_prices[-1] - stock_prices[0]) / stock_prices[0] * 100
            if stock_prices[0] != 0
            else 0
        )
        bench_return = (
            (bench_prices[-1] - bench_prices[0]) / bench_prices[0] * 100
            if bench_prices[0] != 0
            else 0
        )
        excess_return = stock_return - bench_return

        # Normalize for charting (base = 100)
        stock_norm = [round(p / stock_prices[0] * 100, 2) for p in stock_prices]
        bench_norm = [round(p / bench_prices[0] * 100, 2) for p in bench_prices]

        return {
            "error": None,
            "dates": dates,
            "stock_prices": stock_prices,
            "bench_prices": bench_prices,
            "stock_normalized": stock_norm,
            "bench_normalized": bench_norm,
            "stock_return_pct": round(float(stock_return), 2),
            "bench_return_pct": round(float(bench_return), 2),
            "excess_return_pct": round(float(excess_return), 2),
        }
    except Exception as e:
        return {"error": str(e)}


def generate_recommendation(sentiment_summary, excess_return, benchmark_name):
    """Generate a trend recommendation based on sentiment and excess returns."""
    avg = sentiment_summary["avg_sentiment"]
    pos = sentiment_summary["positive_pct"]
    neg = sentiment_summary["negative_pct"]

    # Sentiment signal
    if avg > 0.15 and pos > 50:
        sentiment_signal = "Strong Positive"
        sentiment_strength = 2
    elif avg > 0.05 and pos > 35:
        sentiment_signal = "Mildly Positive"
        sentiment_strength = 1
    elif avg < -0.15 and neg > 50:
        sentiment_signal = "Strong Negative"
        sentiment_strength = -2
    elif avg < -0.05 and neg > 35:
        sentiment_signal = "Mildly Negative"
        sentiment_strength = -1
    else:
        sentiment_signal = "Neutral"
        sentiment_strength = 0

    # Excess return signal
    if excess_return > 3:
        momentum_signal = "Strong Outperformance"
        momentum_strength = 2
    elif excess_return > 1:
        momentum_signal = "Mild Outperformance"
        momentum_strength = 1
    elif excess_return < -3:
        momentum_signal = "Strong Underperformance"
        momentum_strength = -2
    elif excess_return < -1:
        momentum_signal = "Mild Underperformance"
        momentum_strength = -1
    else:
        momentum_signal = "In-line with Market"
        momentum_strength = 0

    # Combined score
    combined = sentiment_strength + momentum_strength

    if combined >= 3:
        recommendation = "Bullish"
        color = "#22c55e"
        description = (
            f"Strong positive sentiment combined with outperformance vs {benchmark_name}. "
            "News flow and price momentum both favor continued upside."
        )
    elif combined >= 1:
        recommendation = "Mildly Bullish"
        color = "#86efac"
        description = (
            f"Moderately positive outlook with sentiment/momentum leaning favorable vs {benchmark_name}."
        )
    elif combined <= -3:
        recommendation = "Bearish"
        color = "#ef4444"
        description = (
            f"Negative sentiment combined with underperformance vs {benchmark_name}. "
            "Both news flow and price action suggest caution."
        )
    elif combined <= -1:
        recommendation = "Mildly Bearish"
        color = "#fca5a5"
        description = (
            f"Moderately negative outlook with sentiment/momentum leaning unfavorable vs {benchmark_name}."
        )
    else:
        recommendation = "Neutral"
        color = "#fbbf24"
        description = (
            f"Mixed signals — sentiment and performance roughly in line with {benchmark_name}. "
            "No strong directional bias."
        )

    return {
        "recommendation": recommendation,
        "color": color,
        "description": description,
        "sentiment_signal": sentiment_signal,
        "momentum_signal": momentum_signal,
        "combined_score": combined,
    }


# --- Routes ---


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()

    if not ticker:
        return jsonify({"error": "No ticker provided"}), 400

    # Validate ticker by fetching price data
    try:
        stock_data, stock_meta = yahoo_chart_api(ticker, days=5)
        if not stock_data or not stock_meta:
            return jsonify({"error": f"Could not find ticker: {ticker}"}), 400
        company_name = (
            stock_meta.get("shortName")
            or stock_meta.get("longName")
            or stock_meta.get("symbol", ticker)
        )
    except Exception:
        return jsonify({"error": f"Could not find ticker: {ticker}"}), 400

    # Get benchmark info
    benchmark = get_benchmark_for_ticker(ticker)

    # Fetch news
    news_result = fetch_google_news(f"{ticker} {company_name}", days=15)
    if news_result.get("error"):
        return jsonify({"error": news_result["error"]}), 500

    if not news_result["articles"]:
        return jsonify({"error": f"No recent news found for {ticker}"}), 404

    # Sentiment analysis
    sentiment = analyze_sentiment(news_result["articles"])

    # Price data
    prices = get_price_data(ticker, benchmark["index"], days=15)

    # Generate recommendation
    excess = prices.get("excess_return_pct", 0) if not prices.get("error") else 0
    rec = generate_recommendation(
        sentiment["summary"], excess, benchmark["index_name"]
    )

    return jsonify(
        {
            "ticker": ticker,
            "company_name": company_name,
            "benchmark": benchmark,
            "sentiment": sentiment,
            "prices": prices,
            "recommendation": rec,
        }
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
