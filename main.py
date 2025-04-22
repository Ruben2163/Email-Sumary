import smtplib
import ssl
import yfinance as yf
import requests
from email.message import EmailMessage

# === CONFIG ===
NEWS_API_KEY = 'YOUR_NEWSAPI_KEY'
STOCKS = ['AAPL', 'TSLA', '^GSPC']
EMAIL_ADDRESS = 'your_email@gmail.com'
EMAIL_PASSWORD = 'your_app_password'
RECIPIENT_EMAIL = 'your_email@gmail.com'

# === FETCH NEWS ===
def get_finance_news():
    url = f'https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey={NEWS_API_KEY}'
    res = requests.get(url)
    articles = res.json().get("articles", [])
    headlines = [f"- {a['title']}" for a in articles[:5]]
    return "\n".join(headlines)

# === FETCH STOCK DATA ===
def get_stock_prices():
    prices = []
    for symbol in STOCKS:
        stock = yf.Ticker(symbol)
        data = stock.history(period='1d')
        if not data.empty:
            price = data['Close'].iloc[-1]
            prices.append(f"{symbol}: ${price:.2f}")
    return "\n".join(prices)

# === COMPOSE REPORT ===
def compose_report():
    news = get_finance_news()
    stocks = get_stock_prices()
    return f"""Good morning!

Here is your daily finance briefing:

--- Headlines ---
{news}

--- Stock Prices ---
{stocks}
"""

# === SEND EMAIL ===
def send_email(body):
    msg = EmailMessage()
    msg['Subject'] = 'Your Daily Finance Briefing'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    email_body = compose_report()
    send_email(email_body)