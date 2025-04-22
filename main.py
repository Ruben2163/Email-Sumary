import requests
import yfinance as yf

# === SETTINGS ===
NEWS_API_KEY = 'YOUR_NEWSAPI_KEY'
STOCKS = ['AAPL', 'TSLA', '^GSPC']  # Apple, Tesla, S&P 500

# === 1. Get Finance News ===
def get_finance_news():
    url = f"https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey={NEWS_API_KEY}"
    res = requests.get(url)
    articles = res.json().get("articles", [])
    top_headlines = [f"- {a['title']}" for a in articles[:5]]
    return "\n".join(top_headlines)

# === 2. Get Stock Prices ===
def get_stock_summary():
    summaries = []
    for symbol in STOCKS:
        stock = yf.Ticker(symbol)
        data = stock.history(period='1d')
        if data.empty:
            continue
        last_price = data['Close'].iloc[-1]
        summaries.append(f"{symbol}: ${last_price:.2f}")
    return "\n".join(summaries)

# === 3. Combine All ===
def create_report():
    report = "Good morning! Here's your daily financial update:\n\n"
    report += "Top Headlines:\n"
    report += get_finance_news() + "\n\n"
    report += "Stock Prices:\n"
    report += get_stock_summary()
    return report

# For now, just print to check
if __name__ == '__main__':
    print(create_report())