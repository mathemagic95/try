# StockSentiment — Stock Sentiment Trend Monitor

A webapp that analyzes recent news sentiment for any stock ticker and recommends a weekly trend, benchmarked against the major index of that country.

## Features

- **Ticker Search** — Enter any stock ticker (US, India, UK, Japan, etc.)
- **News Fetching** — Pulls last 15 days of news from Google News RSS
- **Sentiment Analysis** — VADER (NLTK) scores each article as Positive / Neutral / Negative
- **Benchmark Comparison** — Auto-detects country and compares returns against the major index (S&P 500, NIFTY 50, FTSE 100, etc.)
- **Excess Alpha** — Shows stock return minus benchmark return
- **Trend Recommendation** — Combined sentiment + momentum score yields Bullish / Mildly Bullish / Neutral / Mildly Bearish / Bearish
- **PWA** — Installable on iOS/Android home screen as a standalone app

## Requirements

- Python 3.9+

## Installation & Setup

```bash
# Clone the repository
git clone <repo-url>
cd try

# Install dependencies
pip install -r requirements.txt

# Download NLTK data (happens automatically on first run)
python -c "import nltk; nltk.download('vader_lexicon')"
```

## Running the App

```bash
python app.py
```

The server starts at **http://localhost:5000**. Open this URL in your browser.

## Usage

1. Open http://localhost:5000 in your browser
2. Type a stock ticker in the search box (e.g. `AAPL`, `TSLA`, `RELIANCE.NS`)
3. Click **Analyze** or press Enter
4. View the dashboard: trend recommendation, price chart vs benchmark, daily sentiment, and news feed

## Installing as a Mobile App (PWA)

### iOS (Safari)
1. Open the app URL in Safari
2. Tap the **Share** button (square with arrow)
3. Scroll down and tap **Add to Home Screen**
4. Tap **Add** — the app now launches in standalone mode

### Android (Chrome)
1. Open the app URL in Chrome
2. Tap the install banner that appears, or tap the three-dot menu
3. Tap **Install app** or **Add to Home Screen**

## Supported Markets

| Ticker Suffix | Country | Benchmark Index |
|---|---|---|
| *(none)* | US | S&P 500 |
| `.NS` | India | NIFTY 50 |
| `.BO` | India | BSE SENSEX |
| `.L` | UK | FTSE 100 |
| `.TO` | Canada | S&P/TSX |
| `.AX` | Australia | S&P/ASX 200 |
| `.PA` | France | CAC 40 |
| `.DE` | Germany | DAX |
| `.T` | Japan | Nikkei 225 |
| `.HK` | Hong Kong | Hang Seng |
| `.SS` | China | SSE Composite |
| `.SZ` | China | SZSE Component |
| `.KS` | South Korea | KOSPI |
| `.SA` | Brazil | Bovespa |
| `.SW` | Switzerland | SMI |

## Deploying for Others

The app needs HTTPS for PWA features (service worker, install prompt). Options:

- **Render.com** — Connect your repo, set build command `pip install -r requirements.txt`, start command `python app.py`
- **Railway.app** — `railway init && railway up`
- **Fly.io** — `fly launch`
- **PythonAnywhere** — Free Flask hosting tier
- **ngrok** (temporary) — `ngrok http 5000` to get a public HTTPS URL

## Disclaimer

This tool is for informational purposes only and does not constitute financial advice. Sentiment analysis is based on automated NLP processing of news headlines and may not reflect actual market conditions. Always do your own research before making investment decisions.
