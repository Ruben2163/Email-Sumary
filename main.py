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

# === FETCH STOCK PRICES ===
def get_stock_prices():
    result = []
    for symbol in STOCKS:
        stock = yf.Ticker(symbol)
        data = stock.history(period='1d')
        if not data.empty:
            price = data['Close'].iloc[-1]
            result.append((symbol, price))
    return result

# === COMPOSE PLAIN TEXT VERSION ===
def compose_plain_report(news, stocks):
    news_section = "\n".join(f"- {n['title']}" for n in news)
    stock_section = "\n".join(f"{s[0]}: ${s[1]:.2f}" for s in stocks)
    return f"""Good morning!

Here is your daily financial briefing:

--- Headlines ---
{news_section}

--- Stock Prices ---
{stock_section}
"""

# === COMPOSE HTML EMAIL VERSION ===
def compose_html_report(news, stocks):
    news_html = "".join(
        f"<li><a href='{n['url']}' target='_blank'>{n['title']}</a></li>"
        for n in news
    )
    stock_html = "".join(f"<li><b>{s[0]}</b>: ${s[1]:.2f}</li>" for s in stocks)

    html = f"""
    <html>
      <body style="font-family:Arial, sans-serif; color:#333;">
        <h2>Good Morning!</h2>
        <p>Here’s your <b>daily finance briefing</b>:</p>

        <h3 style="color:#2c3e50;">Top Headlines</h3>
        <ul>{news_html}</ul>

        <h3 style="color:#2c3e50;">Stock Prices</h3>
        <ul>{stock_html}</ul>

        <p style="font-size:12px; color:#888;">Sent by your finance bot. Powered by NewsAPI and Yahoo Finance.</p>
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