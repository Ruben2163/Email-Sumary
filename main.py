import os
import smtplib
import ssl
import yfinance as yf
import requests
from email.message import EmailMessage

# === CONFIG ===
NEWS_API_KEY = os.environ['NEWS_API_KEY']
STOCKS = ['AAPL', 'TSLA', '^GSPC']
EMAIL_ADDRESS = os.environ['EMAIL_ADDRESS']
EMAIL_PASSWORD = os.environ['EMAIL_PASSWORD']
RECIPIENT_EMAIL = os.environ['RECIPIENT_EMAIL']

# === FETCH NEWS ===
def get_finance_news():
    url = f'https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey={NEWS_API_KEY}'
    res = requests.get(url)
    articles = res.json().get("articles", [])
    return [{"title": a['title'], "url": a['url']} for a in articles[:5]]

# === FETCH STOCK PRICES + CHANGES ===
def get_stock_prices():
    results = []
    for symbol in STOCKS:
        stock = yf.Ticker(symbol)
        data = stock.history(period='2d')  # Need 2 days to calculate change
        if len(data) >= 2:
            latest = data['Close'].iloc[-1]
            previous = data['Close'].iloc[-2]
            change = latest - previous
            percent = (change / previous) * 100
            results.append({
                "symbol": symbol,
                "price": latest,
                "change": change,
                "percent": percent
            })
    return results

# === COMPOSE PLAIN TEXT REPORT (fallback) ===
def compose_plain_report(news, stocks):
    news_section = "\n".join(f"- {n['title']}" for n in news)
    stock_section = "\n".join(
        f"{s['symbol']}: ${s['price']:.2f} ({s['percent']:+.2f}%)"
        for s in stocks
    )
    return f"""Good morning!

Here is your daily financial briefing:

--- Headlines ---
{news_section}

--- Stock Prices ---
{stock_section}
"""

# === COMPOSE HTML REPORT (styled) ===
def compose_html_report(news, stocks):
    news_html = "".join(
        f"<li><a href='{n['url']}' target='_blank'>{n['title']}</a></li>"
        for n in news
    )

    stock_html = ""
    for s in stocks:
        color = "#2ecc71" if s["change"] >= 0 else "#e74c3c"
        emoji = "📈" if s["change"] >= 0 else "📉"
        stock_html += (
            f"<li><span class='symbol'>{emoji} {s['symbol']}</span>: "
            f"<span class='price'>${s['price']:.2f}</span> "
            f"<span class='percent' style='color:{color};'>({s['percent']:+.2f}%)</span></li>"
        )

    html = f"""
    <html>
      <head>
        <style>
          body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #ffffff;
            color: #333;
            margin: 0;
            padding: 20px;
          }}

          @media (prefers-color-scheme: dark) {{
            body {{
              background-color: #1e1e1e;
              color: #ccc;
            }}
            a {{ color: #4ea3ff; }}
          }}

          h2 {{
            font-size: 24px;
            margin-bottom: 10px;
            color: #111;
          }}

          h3 {{
            font-size: 18px;
            margin-top: 30px;
            margin-bottom: 10px;
            color: #222;
            border-bottom: 1px solid #eee;
            padding-bottom: 4px;
          }}

          ul {{
            padding-left: 20px;
            line-height: 1.6;
          }}

          a {{
            color: #1a73e8;
            text-decoration: none;
          }}

          a:hover {{
            text-decoration: underline;
          }}

          .symbol {{
            font-weight: bold;
          }}

          .price {{
            color: #333;
          }}

          .footer {{
            font-size: 12px;
            color: #999;
            margin-top: 30px;
            border-top: 1px solid #eee;
            padding-top: 10px;
          }}
        </style>
      </head>
      <body>
        <h2>Good Morning!</h2>
        <p>Here’s your <strong>daily finance briefing</strong>:</p>

        <h3>Top Headlines</h3>
        <ul>{news_html}</ul>

        <h3>Stock Prices</h3>
        <ul>{stock_html}</ul>

        <div class="footer">
          Sent by your finance bot. Powered by NewsAPI & Yahoo Finance.
        </div>
      </body>
    </html>
    """
    return html

# === SEND EMAIL ===
def send_email(body_text, body_html):
    msg = EmailMessage()
    msg['Subject'] = 'Your Daily Finance Briefing'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL
    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype='html')

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

# === MAIN ===
if __name__ == "__main__":
    news = get_finance_news()
    stocks = get_stock_prices()

    plain = compose_plain_report(news, stocks)
    html = compose_html_report(news, stocks)

    send_email(plain, html)