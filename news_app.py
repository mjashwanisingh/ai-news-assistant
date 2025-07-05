import streamlit as st
import feedparser
import requests
import json
import os
from fpdf import FPDF
from datetime import datetime
import smtplib
from email.message import EmailMessage

import streamlit as st

AUTO_MODE = os.getenv("SCHEDULE_RUN", "false").lower() == "true"

# Hardcoded credentials (or use st.secrets)
AUTHORIZED_USERS = {
    "admin": st.secrets.get("APP_LOGIN_PASSWORD", "1234")
}

# Simple login form
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login Required")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if AUTHORIZED_USERS.get(username) == password:
            st.session_state.logged_in = True
            st.success("✅ Logged in successfully!")
        else:
            st.error("❌ Invalid credentials")
    st.stop()


# === SETTINGS ===
NEWSAPI_KEY = st.secrets["NEWSAPI_KEY"]
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
APP_PASSWORD = st.secrets["APP_PASSWORD"]
RECEIVER_EMAIL = st.secrets["RECEIVER_EMAIL"]

# === FETCH FROM RSS ===
def fetch_rss_news(name, url):
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries[:5]:
        articles.append({
            "title": entry.title,
            "summary": entry.get("summary", ""),
            "url": entry.link
        })
    return articles

rss_sources = {
    "NDTV": "https://feeds.feedburner.com/ndtvnews-top-stories",
    "ANI": "https://www.aninews.in/rss/national-news.xml",
    "PIB": "https://pib.gov.in/rssfeed/rss.xml",
    "Indian Express": "https://indianexpress.com/section/india/feed/",
    "The Hindu": "https://www.thehindu.com/news/national/feeder/default.rss",
    "TOI": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "BBC": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml"
}

# === FETCH FROM NEWSAPI ===
def fetch_newsapi_news():
    url = f"https://newsapi.org/v2/top-headlines?language=en&pageSize=30&apiKey={NEWSAPI_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return []
    articles = response.json().get("articles", [])
    return [{
        "title": a['title'],
        "summary": a.get('description', ''),
        "url": a['url']
    } for a in articles if a['title']]

# === FETCH FROM TWITTER ===
def fetch_tweets(accounts):
    os.makedirs("tweets", exist_ok=True)
    news = []
    for acc in accounts:
        file = f"tweets/{acc}.json"
        os.system(f"snscrape --jsonl --max-results 2 twitter-user {acc} > {file}")
        try:
            with open(file, "r") as f:
                tweets = [json.loads(line) for line in f.readlines()]
                for t in tweets:
                    news.append({
                        "title": t["content"][:100],
                        "summary": t["content"],
                        "url": t["url"]
                    })
        except Exception as e:
            st.warning(f"⚠️ Error fetching from @{acc}: {e}")
    return news

# === PDF CREATOR ===
def create_pdf(local, national, global_):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Daily News Summary", ln=True, align='C')
    pdf.cell(200, 10, f"Date: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align='C')
    pdf.ln(10)

    def section(title, news_list):
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, title, ln=True)
        pdf.set_font("Arial", size=12)
        for item in news_list[:5]:
            t = item["title"].encode('ascii', errors='ignore').decode()
            s = item["summary"].encode('ascii', errors='ignore').decode()
            url = item.get("url", "")
            pdf.multi_cell(0, 10, f"{t}\n{s}\n{url}\n")
        pdf.ln(5)

    section("Local News", local)
    section("National News", national)
    section("Global News", global_)
    filename = f"news_summary_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf.output(filename)
    return filename

# === EMAIL FUNCTION ===
def send_email(receiver_email, attachment_path, sender_email, app_password):
    msg = EmailMessage()
    msg["Subject"] = "📄 Your Daily News Summary"
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content("Attached is your AI-powered news summary for today.")

    with open(attachment_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=attachment_path)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender_email, app_password)
        smtp.send_message(msg)

# === STREAMLIT UI ===
st.set_page_config(page_title="🧠 AI News Assistant", layout="wide")
st.title("🗞️ AI News Assistant - Daily News PDF Generator")

if st.button("📰 Fetch News Now"):
    local_news, national_news, global_news = [], [], []

    for source, url in rss_sources.items():
        rss = fetch_rss_news(source, url)
        if source in ["NDTV", "ANI"]:
            local_news += rss
        elif source in ["PIB", "Indian Express", "The Hindu"]:
            national_news += rss
        else:
            global_news += rss

    global_news += fetch_newsapi_news()

    tweets = fetch_tweets([
        "ndtv", "ANI", "PMOIndia", "BBCWorld", "ArvindKejriwal",
        "RahulGandhi", "narendramodi", "POTUS"
    ])
    local_news += tweets[:5]
    national_news += tweets[5:10]
    global_news += tweets[10:]

    st.success("✅ News fetched successfully!")

    st.subheader("Local News")
    for item in local_news[:5]:
        st.write(f"🔹 **{item['title']}**")
        st.write(item["summary"])
        st.write(f"[Read more]({item['url']})")

    st.subheader("National News")
    for item in national_news[:5]:
        st.write(f"🔸 **{item['title']}**")
        st.write(item["summary"])
        st.write(f"[Read more]({item['url']})")

    st.subheader("Global News")
    for item in global_news[:5]:
        st.write(f"🌍 **{item['title']}**")
        st.write(item["summary"])
        st.write(f"[Read more]({item['url']})")

    if st.button("📄 Generate PDF"):
        pdf_file = create_pdf(local_news, national_news, global_news)
        st.success(f"✅ PDF created: {pdf_file}")
        with open(pdf_file, "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name=pdf_file)

    if st.button("✉️ Send Email"):
        pdf_file = f"news_summary_{datetime.now().strftime('%Y%m%d')}.pdf"
        send_email(RECEIVER_EMAIL, pdf_file, SENDER_EMAIL, APP_PASSWORD)
        st.success("📧 Email sent successfully!")

if AUTO_MODE:
    local_news, national_news, global_news = [], [], []

    for source, url in rss_sources.items():
        rss = fetch_rss_news(source, url)
        if source in ["NDTV", "ANI"]:
            local_news += rss
        elif source in ["PIB", "Indian Express", "The Hindu"]:
            national_news += rss
        else:
            global_news += rss

    global_news += fetch_newsapi_news()

    tweets = fetch_tweets([
        "ndtv", "ANI", "PMOIndia", "BBCWorld", "ArvindKejriwal",
        "RahulGandhi", "narendramodi", "POTUS"
    ])
    local_news += tweets[:5]
    national_news += tweets[5:10]
    global_news += tweets[10:]

    pdf_file = create_pdf(local_news, national_news, global_news)
    send_email(RECEIVER_EMAIL, pdf_file, SENDER_EMAIL, APP_PASSWORD)

