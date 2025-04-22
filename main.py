import yfinance as yf
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import datetime

# --- Config ---
NEWS_API_KEY = 'YOUR_NEWSAPI_KEY'
EMAIL_ADDRESS = 'your_email@gmail.com'
EMAIL_PASSWORD = 'your_app_password'
RECIPIENT_EMAIL = 'your_email@gmail.com'
STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
EMERGING_WATCHLIST = ['PLTR', 'UPST', 'SOFI', 'DNA', 'IONQ']
NUM_ARTICLES = 5

# --- Load FinBERT ---
tokenizer = AutoTokenizer.from_pretrained("yiyanghkust/finbert-tone")
model = AutoModelForSequenceClassification.from_pretrained("yiyanghkust/finbert-tone")
labels = ['neutral', 'positive', 'negative']

def get_sentiment(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    outputs = model(**inputs)
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1).detach().numpy()[0]
    return {label: round(float(prob), 2) for label, prob in zip(labels, probs)}

def get_news():
    url = f"https://newsapi.org/v2/top-headlines?category=business&language=en&pageSize={NUM_ARTICLES}&apiKey={NEWS_API_KEY}"
    response = requests.get(url)
    return response.json().get("articles", [])

def get_stock_data(tickers):
    results = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if len(hist) >= 2:
                change = round(((hist["Close"].iloc[-1] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2]) * 100, 2)
                results.append({"ticker": ticker, "change": change})
        except:
            continue
    return results

def get_emerging_stocks():
    return [s for s in get_stock_data(EMERGING_WATCHLIST) if s["change"] >= 5]

def compose_html_report(news, stocks, emerging):
    html = f"<h1 style='font-family:sans-serif;'>📊 Morning Brief - {datetime.date.today()}</h1>"

    html += "<h2>📰 Top Headlines</h2>"
    for article in news:
        sentiment = get_sentiment(article["title"])
        sentiment_str = " | ".join([f"{k.capitalize()}: {v:.2f}" for k, v in sentiment.items()])
        html += f"""
            <div style='margin-bottom:15px;'>
                <p style='margin:0; font-size:16px; color:#000; font-weight:500;'>{article['title']}</p>
                <small style='color:#666;'>{sentiment_str}</small>
            </div>
        """

    html += "<h2>📈 Stock Overview</h2><div style='display: flex; flex-wrap: wrap; gap: 10px;'>"
    for s in stocks:
        bg = "#2ecc71" if s["change"] > 0 else "#e74c3c" if s["change"] < 0 else "#f39c12"
        html += f"""
        <div style='background:{bg};color:white;padding:15px 10px;min-width:100px;
        text-align:center;font-weight:bold;font-family:monospace;border-radius:8px;
        box-shadow:0 1px 3px rgba(0,0,0,0.1);'>
            {s['ticker']}<br>{s['change']}%
        </div>
        """
    html += "</div>"

    html += "<h2>🚀 Emerging Stocks</h2>"
    if emerging:
        html += "<div style='display: flex; flex-wrap: wrap; gap: 10px;'>"
        for s in emerging:
            html += f"""
            <div style='background:#8e44ad;color:white;padding:15px 10px;min-width:100px;
            text-align:center;font-weight:bold;font-family:monospace;border-radius:8px;
            box-shadow:0 1px 3px rgba(0,0,0,0.1);'>
                {s['ticker']}<br>+{s['change']}%
            </div>
            """
        html += "</div>"
    else:
        html += "<p>No major emerging stock moves today.</p>"

    return html

def send_email(subject, html_content):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL

    msg.attach(MIMEText(html_content, 'html'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

# --- Main ---
if __name__ == "__main__":
    news = get_news()
    stocks = get_stock_data(STOCKS)
    emerging = get_emerging_stocks()
    html = compose_html_report(news, stocks, emerging)
    send_email("🗞️ Your Daily Market Brief", html)