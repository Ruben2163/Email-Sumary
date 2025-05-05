import os
import requests
import smtplib
import yfinance as yf
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from groq import Groq

# === ENVIRONMENT VARIABLES ===
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
)

def ai(news):
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": (
                    f"return just one word for this output for finantial sentiment analysis "
                    f"don't say anything else only positive neutral or negative. "
                    f"this is the news to do sentiment analysis on: {news}"
                ),
            }
        ],
        model="llama-3.3-70b-versatile",
        stream=False,
    )
    result = chat_completion.choices[0].message.content.strip().lower()
    confidence = 1.0  # Placeholder confidence
    return result, confidence


print(chat_completion.choices[0].message.content)
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
TICKERS = os.getenv("TICKERS", "AAPL,MSFT,GOOG,TSLA,BTC-GBP,TSM,AMD,META,BRK-B").split(",")


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
            sentiment, confidence = ai(title)
            results.append({
                "title": title,
                "url": a['url'],
                "sentiment": sentiment,
                "confidence": confidence
            })
        print("retrived news")
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
    print("get_stock_prices done")
    return prices

# === BUILD EMAIL ===
def compose_html_report(news, stocks):
    # Format today's date
    now = datetime.now().strftime("%A, %d %B %Y")

    # Return the full HTML email
    return f"""
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background-color: #f3f4f6;
                margin: 0;
                padding: 0;
                color: #1f2937;
            }}
            .container {{
                max-width: 640px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 10px 15px rgba(0,0,0,0.05);
            }}
            .header {{
                background-color: #1e40af;
                color: white;
                padding: 24px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 600;
            }}
            .section {{
                padding: 20px 24px;
            }}
            h2 {{
                font-size: 18px;
                color: #111827;
                margin: 0 0 12px;
                border-bottom: 1px solid #e5e7eb;
                padding-bottom: 6px;
            }}
            ul {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            li {{
                margin-bottom: 14px;
                font-size: 15px;
                line-height: 1.6;
            }}
            a {{
                color: #2563eb;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .positive {{
                color: #16a34a;
                font-weight: 600;
            }}
            .negative {{
                color: #dc2626;
                font-weight: 600;
            }}
            .neutral {{
                color: #d97706;
                font-weight: 600;
            }}
            .confidence {{
                font-size: 13px;
                color: #6b7280;
                margin-left: 6px;
            }}
            .divider {{
                border-top: 1px solid #e5e7eb;
                margin: 24px 0;
            }}
            .footer {{
                text-align: center;
                font-size: 14px;
                color: #6b7280;
                padding: 16px 24px;
            }}
            .cta-link {{
                color: #2563eb;
                font-weight: 500;
                text-decoration: none;
            }}
            .cta-link:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <h1>📬 Morning Market Brief – {now}</h1>
            </div>

            <!-- Top Headlines -->
            <div class="section">
                <h2>📰 Top Finance Headlines</h2>
                <ul>
                    {''.join(
                        f"<li>{'📈' if n['sentiment']=='positive' else '📉' if n['sentiment']=='negative' else '⚖️'} "
                        f"<a href='{n['url']}'>{n['title']}</a> "
                        f"<span class='{n['sentiment']}'>{n['sentiment'].capitalize()}</span>"
                        f"<span class='confidence'>({round(n['confidence']*100, 1)}%)</span></li>"
                        for n in news
                    )}
                </ul>
            </div>

            <!-- Stock Snapshot -->
            <div class="section">
                <h2>📊 Stock Price Snapshot</h2>
                <ul>
                    {''.join(
                        f"<li>{s['ticker']}: ${s['price']} "
                        f"<span class='{'positive' if s['change'] > 0 else 'negative'}'>"
                        f"{'🔼' if s['change'] > 0 else '🔽'} {s['change']}%</span></li>"
                        for s in stocks
                    )}
                </ul>
            </div>

            <!-- Divider + CTA -->
            <div class="divider"></div>
            <div class="footer">
                🔒 For an in-depth market analysis, visit our 
                <a href="https://rubenphagura-dash.streamlit.app" 
                   class="cta-link" target="_blank">
                   full dashboard
                </a> (Password: <strong>yourpass</strong>)
            </div>
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
