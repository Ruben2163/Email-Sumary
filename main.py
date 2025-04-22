import os
import requests
import smtplib
import yfinance as yf
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

# === ENVIRONMENT VARIABLES ===
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
TICKERS = os.getenv("TICKERS", "AAPL,MSFT,GOOG,TSLA").split(",")

# === FINBERT SETUP ===
tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
labels = ['negative', 'neutral', 'positive']

def analyze_sentiment(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = F.softmax(outputs.logits, dim=-1).squeeze().tolist()
    result = {label: round(prob * 100, 2) for label, prob in zip(labels, probs)}
    top_sentiment = max(result, key=result.get)
    return top_sentiment, result

# === GET FINANCE NEWS ===
def get_finance_news():
    try:
        url = f'https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey={NEWS_API_KEY}'
        res = requests.get(url)
        res.raise_for_status()
        articles = res.json().get("articles", [])[:5]

        results = []
        for a in articles:
            title = a['title']
            sentiment, probs = analyze_sentiment(title)
            results.append({
                "title": title,
                "url": a['url'],
                "sentiment": sentiment,
                "probabilities": probs
            })
        return results
    except Exception as e:
        print("Error fetching news:", e)
        return []

# === GET STOCK PRICES ===
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

# === FORMAT EMAIL HTML ===
def compose_html_report(news, stocks):
    styles = """
    body { font-family: Arial, sans-serif; background-color: #ffffff; padding: 20px; color: #333; }
    h2, h3 { margin-top: 30px; color: #111; }
    .section { margin-bottom: 40px; }
    .headline { color: #000000; font-size: 16px; font-weight: bold; }
    .sentiment-bar { font-size: 14px; margin-top: 4px; color: #666; }
    .positive { color: #27ae60; }
    .negative { color: #c0392b; }
    .neutral { color: #f39c12; }
    .stock-item { margin-bottom: 8px; font-size: 15px; }
    .divider { border-top: 1px solid #ccc; margin: 20px 0; }
    a { text-decoration: none; color: #000000; }
    """

    news_html = ""
    for n in news:
        p = n['probabilities']
        news_html += f"""
        <div class="section">
            <div class="headline"><a href="{n['url']}">{n['title']}</a></div>
            <div class="sentiment-bar">
                📉 <span class='negative'>Negative: {p['negative']}%</span> |
                ⚖️ <span class='neutral'>Neutral: {p['neutral']}%</span> |
                📈 <span class='positive'>Positive: {p['positive']}%</span>
            </div>
            <div class="divider"></div>
        </div>
        """
    stocks_html = "<div style='display: flex; flex-wrap: wrap; gap: 10px;'>"

    for s in stocks:
        change = s["change"]
        bg_color = "#27ae60" if change > 0 else "#c0392b" if change < 0 else "#f39c12"
        change_str = f"+{change}%" if change > 0 else f"{change}%"
        stocks_html += f"""
        <div style="
            background-color: {bg_color};
            color: white;
            padding: 15px 10px;
            min-width: 100px;
            text-align: center;
            font-weight: bold;
            font-family: monospace;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        ">
            {s['ticker']}<br>{change_str}
        </div>
        """
    
    stocks_html += "</div>"




    now = datetime.now().strftime("%A, %d %B %Y")
    html = f"""
    <html>
    <head><style>{styles}</style></head>
    <body>
        <h2>📬 Morning Market Brief – {now}</h2>
        <h3>📰 Top Finance Headlines</h3>
        {news_html}
        <h3>📊 Stock Price Summary</h3>
        {stocks_html}
    </body>
    </html>
    """
    return html

# === SEND EMAIL ===
def send_email(subject, html_body):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = RECIPIENT_EMAIL

        part = MIMEText(html_body, "html")
        msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())

        print("✅ Email sent successfully!")
    except Exception as e:
        print("Error sending email:", e)

# === MAIN RUN ===
if __name__ == "__main__":
    news = get_finance_news()
    stocks = get_stock_prices()
    html = compose_html_report(news, stocks)
    send_email("📈 Your Morning Market Brief", html)
