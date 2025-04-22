import os
import requests
import smtplib
import yfinance as yf
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

# === ENVIRONMENT VARIABLES ===
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
TICKERS = os.getenv("TICKERS", "AAPL,MSFT,GOOG,TSLA,BTC-GBP,TSM,AMD,META,BRK-B").split(",")

# === LOAD FINBERT ===
tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
labels = ['negative', 'neutral', 'positive']

def analyze_sentiment(text):
    # Negative keywords for rule-based correction
    negative_keywords = ['drop', 'plunge', 'crash', 'fall', 'decline', 'slump', 'lose', 'loss']
    
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = F.softmax(outputs.logits, dim=-1)
    sentiment_idx = torch.argmax(probs)
    sentiment = labels[sentiment_idx]
    confidence = torch.max(probs).item()

    # Rule-based correction for negative headlines mislabeled as neutral
    if sentiment == 'neutral' and confidence > 0.9:
        for keyword in negative_keywords:
            if keyword in text.lower():
                sentiment = 'negative'
                confidence = 0.95  # Adjust confidence to reflect correction
                break

    return sentiment, confidence

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
            })
        return results
    except Exception as e:
        print("Error fetching news:", e)
        return []

# === FETCH STOCK PRICES AND GENERATE HEATMAP ===
def get_stock_prices():
    prices = []
    changes = []
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
            changes.append(change)
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")

    # Generate heatmap
    if prices:
        df = pd.DataFrame({'Ticker': [p['ticker'] for p in prices], 'Change (%)': [p['change'] for p in prices]})
        plt.figure(figsize=(4, len(TICKERS) * 0.5))
        sns.heatmap(
            df[['Change (%)']].set_index(df['Ticker']),
            annot=True, fmt='.2f', cmap='RdYlGn',
            cbar=False, center=0, linewidths=0.5,
            yticklabels=True
        )
        plt.title('Stock Performance Heatmap')
        plt.tight_layout()
        plt.savefig('heatmap.png', dpi=100)
        plt.close()

    return prices

# === BUILD EMAIL ===
def compose_html_report(news, stocks):
    styles = """
        <style>
            body {
                font-family: Helvetica, Arial, sans-serif;
                background-color: #f9fafb;
                padding: 20px;
                margin: 0;
                color: #1f2937;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 24px;
            }
            h2 {
                color: #111827;
                font-size: 24px;
                margin-bottom: 16px;
                text-align: center;
            }
            h3 {
                color: #374151;
                font-size: 18px;
                margin: 16px 0 8px;
            }
            ul {
                list-style: none;
                padding: 0;
            }
            li {
                margin-bottom: 12px;
                font-size: 16px;
                line-height: 1.5;
            }
            a {
                color: #2563eb;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
            .positive {
                color: #16a34a;
                font-weight: 600;
            }
            .negative {
                color: #dc2626;
                font-weight: 600;
            }
            .neutral {
                color: #d97706;
                font-weight: 600;
            }
            .confidence {
                font-size: 14px;
                color: #6b7280;
                margin-left: 8px;
            }
            .divider {
                border-top: 1px solid #e5e7eb;
                margin: 16px 0;
            }
            .heatmap-img {
                max-width: 100%;
                height: auto;
                margin-top: 16px;
                display: block;
            }
            @media only screen and (max-width: 600px) {
                .container {
                    padding: 16px;
                }
                h2 {
                    font-size: 20px;
                }
                h3 {
                    font-size: 16px;
                }
                li {
                    font-size: 14px;
                }
            }
        </style>
    """

    news_html = ""
    for n in news:
        emoji = {"positive": "📈", "neutral": "⚖️", "negative": "📉"}.get(n["sentiment"], "")
        confidence_pct = round(n["confidence"] * 100, 1)
        news_html += (
            f"<li>{emoji} <a href='{n['url']}'>{n['title']}</a> "
            f"<span class='{n['sentiment']}'>{n['sentiment'].capitalize()}</span>"
            f"<span class='confidence'>({confidence_pct}%)</span></li>"
        )

    stocks_html = ""
    for s in stocks:
        color = "positive" if s["change"] > 0 else "negative"
        emoji = "🔼" if s["change"] > 0 else "🔽"
        stocks_html += (
            f"<li>{s['ticker']}: ${s['price']} "
            f"<span class='{color}'>{emoji} {s['change']}%</span></li>"
        )

    now = datetime.now().strftime("%A, %d %B %Y")

    return f"""
    <html>
    <head>{styles}</head>
    <body>
        <div class="container">
            <h2>📬 Morning Market Brief – {now}</h2>
            <h3>📰 Top Finance Headlines</h3>
            <ul>{news_html}</ul>
            <div class="divider"></div>
            <h3>📊 Stock Price Snapshot</h3>
            <ul>{stocks_html}</ul>
            <h3>📈 Performance Heatmap</h3>
            <img src="cid:heatmap" class="heatmap-img" alt="Stock Performance Heatmap">
        </div>
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

        # Attach heatmap image
        if os.path.exists('heatmap.png'):
            with open('heatmap.png', 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', '<heatmap>')
                img.add_header('Content-Disposition', 'inline', filename='heatmap.png')
                msg.attach(img)

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