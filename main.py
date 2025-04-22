import os
import requests
import smtplib
import yfinance as yf
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

# === ENVIRONMENT VARIABLES ===
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
TICKERS = os.getenv("TICKERS", "AAPL,MSFT,GOOG,TSLA").split(",")

# === LOAD FINBERT ===
tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
labels = ['negative', 'neutral', 'positive']

def analyze_sentiment(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = F.softmax(outputs.logits, dim=-1)
    sentiment = labels[torch.argmax(probs)]
    confidence = torch.max(probs).item()
    return sentiment, confidence, probs

# === FETCH NEWS ===
def get_finance_news():
    try:
        url = f'https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey={NEWS_API_KEY}'
        res = requests.get(url)
        res.raise_for_status()
        articles = res.json().get("articles", [])[:5]

        results = []
        for a in articles:
            title = a['title']
            sentiment, confidence = analyze_sentiment(title)
            results.append({
                "title": title,
                "url": a['url'],
                "sentiment": sentiment,
                "confidence": confidence
                "probs": probs
            })
        return results
    except Exception as e:
        print("Error fetching news:", e)
        return []

# === FETCH STOCK PRICES ===
def get_stock_prices():
    prices = []
    for ticker in TICKERS:
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period='2d')
            if len(data) < 2:
                continue
            latest = data.iloc[-1]['Close']
            previous = data.iloc[-2]['Close']
            change = ((latest - previous) / previous) * 100
            prices.append({
                "ticker": ticker,
                "price": round(latest, 2),
                "change": round(change, 2)
            })
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
    return prices

# === BUILD EMAIL ===
def compose_html_report(news, stocks):
    styles = """
        body { font-family: Arial, sans-serif; background: #f8f9fa; padding: 20px; }
        h2 { color: #333; }
        li { margin-bottom: 10px; }
        .positive { color: #2ecc71; font-weight: bold; }
        .negative { color: #e74c3c; font-weight: bold; }
        .neutral { color: #f39c12; font-weight: bold; }
    """

    news_html = ""
    for n in news:
        emoji = {"positive": "📈", "neutral": "⚖️", "negative": "📉"}.get(n["sentiment"], "")
        news_html += (
            f"<li>{emoji} <a href='{n['url']}'>{n['title']}</a> "
            f"<span class='{n['sentiment']}'>{n['sentiment'].capitalize()}</span></li>"
        )

    stocks_html = ""
    for s in stocks:
        color = "positive" if s["change"] > 0 else "negative"
        emoji = "🔼" if s["change"] > 0 else "🔽"
        stocks_html += f"<li>{s['ticker']}: ${s['price']} <span class='{color}'>{emoji} {s['change']}%</span></li>"

    now = datetime.now().strftime("%A, %d %B %Y")

    return f"""
    <html>
    <head><style>{styles}</style></head>
    <body>
        <h2>📬 Morning Market Brief – {now}</h2>
        <h3>📰 Top Finance Headlines</h3>
        <ul>{news_html}</ul>
        <h3>📊 Stock Price Snapshot</h3>
        <ul>{stocks_html}</ul>
    </body>
    </html>
    """

# === SEND EMAIL ===
def send_email(subject, html_body):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = RECIPIENT_EMAIL

        part = MIMEText(html_body, "html")
        msg.attach(part)

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        print("✅ Email sent successfully!")
    except Exception as e:
        print("Error sending email:", e)

# === MAIN ===
if __name__ == "__main__":
    news = get_finance_news()
    stocks = get_stock_prices()
    html = compose_html_report(news, stocks)
    send_email("📈 Your Morning Market Brief", html)
