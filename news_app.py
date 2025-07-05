import streamlit as st
import feedparser
import requests
import json
import os
from fpdf import FPDF
from datetime import datetime
import smtplib
from email.message import EmailMessage
import pandas as pd
import plotly.express as px

# === LOGIN ===
AUTHORIZED_USERS = {
    "majorashwanisingh": st.secrets.get("APP_LOGIN_PASSWORD", "1234")
}
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

# === SECRETS ===
NEWSAPI_KEY = st.secrets["NEWSAPI_KEY"]
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
APP_PASSWORD = st.secrets["APP_PASSWORD"]
RECEIVER_EMAIL = st.secrets["RECEIVER_EMAIL"]
AUTO_MODE = os.getenv("SCHEDULE_RUN", "false").lower() == "true"

# === RSS Sources ===
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
hindi_sources = {
    "Aaj Tak": "https://aajtak.intoday.in/rssfeed/hindi-news.xml",
    "Amar Ujala": "https://www.amarujala.com/rss/india-news.xml",
    "Dainik Bhaskar": "https://www.bhaskar.com/rss-feed/2328/",
    "Zee News (Hindi)": "https://zeenews.india.com/hindi/rss/india.xml"
}

# === Fetching News ===
def fetch_rss_news(name, url):
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries[:15]:
        articles.append({
            "title": entry.title,
            "summary": entry.get("summary", ""),
            "url": entry.link,
            "source": name
        })
    return articles

def fetch_newsapi_news():
    url = f"https://newsapi.org/v2/top-headlines?language=en&pageSize=30&apiKey={NEWSAPI_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return []
    articles = response.json().get("articles", [])
    return [{
        "title": a.get("title"),
        "summary": a.get("description", ""),
        "url": a.get("url"),
        "source": a.get("source", {}).get("name", "NewsAPI"),
        "urlToImage": a.get("urlToImage") or "https://via.placeholder.com/150"
    } for a in articles if a.get("title")]

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
                        "url": t["url"],
                        "source": acc
                    })
        except Exception as e:
            st.warning(f"⚠️ Error fetching from @{acc}: {e}")
    return news

# === News Card UI ===
def display_news_card(item):
    title = item.get("title", "No title")
    summary = item.get("summary", "No summary")
    url = item.get("url", "#")
    image = item.get("urlToImage", "") or "https://via.placeholder.com/150"
    st.markdown(f"""
        <div style="border:1px solid #333; border-radius:10px; padding:15px; margin-bottom:15px; background-color:#1e1e1e;">
            <div style="display:flex; gap:15px;">
                <img src="{image}" width="150" style="border-radius:8px;" />
                <div style="flex:1;">
                    <h4 style="margin:0; color:#f2f2f2;">{title}</h4>
                    <p style="margin-top:5px; font-size:14px; color:#ccc;">{summary}</p>
                    <a href="{url}" target="_blank" style="font-weight:bold; font-size:13px; color:#58a6ff;">📎 Read Full Story</a>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# === PDF Generator ===
def create_pdf(local, national, global_):
    import re

    def clean(text):
        if not text:
            return ""
        return re.sub(r'[^\x00-\xFF]+', '', str(text))

    pdf = FPDF()
    pdf.add_page()

    # Header Title
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(200, 10, clean("📰 Daily News Summary"), ln=True, align='C')

    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, clean(f"Date: {datetime.now().strftime('%d-%m-%Y')}"), ln=True, align='C')
    pdf.ln(5)

    def section(title, news_list):
        # Section Header (colored background)
        pdf.set_fill_color(50, 50, 50)   # Dark gray
        pdf.set_text_color(255, 255, 255)  # White text
        pdf.set_font("Arial", 'B', 13)
        pdf.cell(0, 10, clean(title), ln=True, fill=True)
        pdf.ln(2)

        for i, item in enumerate(news_list[:15], start=1):
            title = clean(item.get("title", "No title"))
            summary = clean(item.get("summary", ""))
            url = clean(item.get("url", ""))

            # Draw border box
            x = pdf.get_x()
            y = pdf.get_y()
            box_width = 190
            box_height = 25 + (summary.count('\n') + 1) * 7
            pdf.set_draw_color(180, 180, 180)
            pdf.rect(x, y, box_width, box_height + 15)

            # News Title
            pdf.set_xy(x + 2, y + 2)
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 8, f"{i}. {title}")

            # Summary
            pdf.set_font("Arial", '', 11)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 7, summary)

            # Link
            pdf.set_font("Arial", 'I', 10)
            pdf.set_text_color(0, 0, 200)
            pdf.multi_cell(0, 7, url)

            pdf.ln(5)

    section("Local News", local)
    section("National News", national)
    section("Global News", global_)

    filename = f"news_summary_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf.output(filename)
    return filename

# === EMAIL ===
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

# === Streamlit Tabs ===
st.set_page_config(page_title="🧠 AI News Assistant", layout="wide")
tab1, tab2, tab3 = st.tabs(["📰 News", "📊 Dashboard", "🔍 Search"])

with tab1:
   if st.button("Fetch News"):
    local_news, national_news, global_news, hindi_news = [], [], [], []

    # Extended RSS sources
    rss_sources.update({
        "Hindustan Times": "https://www.hindustantimes.com/feeds/rss/topnews/rssfeed.xml",
        "Economic Times": "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
        "Deccan Herald": "https://www.deccanherald.com/rss-feed/10551",
    })

    hindi_sources = {
        "Aaj Tak": "https://aajtak.intoday.in/rssfeed/hindi-news.xml",
        "Amar Ujala": "https://www.amarujala.com/rss/india-news.xml",
        "Dainik Bhaskar": "https://www.bhaskar.com/rss-feed/2328/",
        "Zee News (Hindi)": "https://zeenews.india.com/hindi/rss/india.xml"
    }

    # ✅ Fetch English & Categorize
    for source, url in rss_sources.items():
        rss = fetch_rss_news(source, url)
        if source in ["NDTV", "ANI"]:
            local_news += rss
        elif source in ["PIB", "Indian Express", "The Hindu"]:
            national_news += rss
        else:
            global_news += rss

    # ✅ Fetch Hindi News
    for source, url in hindi_sources.items():
        hindi_news += fetch_rss_news(source, url)

    # ✅ NewsAPI + X Handles
    global_news += fetch_newsapi_news()

    tweets = fetch_tweets([
        "ndtv", "ANI", "PMOIndia", "BBCWorld", "RahulGandhi", "narendramodi",
        "POTUS", "PTI_News", "aajtak", "ZeeNews", "timesofindia", "IndiaToday", "EconomicTimes"
    ])
    local_news += tweets[20:50]
    national_news += tweets[20:50]
    global_news += tweets[20:50]
    hindi_news += tweets[20:50]

    # ✅ Store in session
    st.session_state.local_news = local_news
    st.session_state.national_news = national_news
    st.session_state.global_news = global_news
    st.session_state.hindi_news = hindi_news

    st.success("✅ News fetched successfully!")

# === Display UI Cards
if "local_news" in st.session_state:
    for category, data in zip(
        ["Local", "National", "Global"],
        [st.session_state.local_news, st.session_state.national_news, st.session_state.global_news]
    ):
        st.subheader(f"{category} News")
        for item in data[:15]:
            display_news_card(item)

    # ✅ Hindi News shown separately
    if "hindi_news" in st.session_state:
        st.subheader("🗞️ Hindi News")
        for item in st.session_state.hindi_news[:15]:
            display_news_card(item)


        if st.button("Generate PDF"):
            pdf_file = create_pdf(st.session_state.local_news, st.session_state.national_news, st.session_state.global_news)
            with open(pdf_file, "rb") as f:
                st.download_button("⬇️ Download PDF", f, file_name=pdf_file)

        if st.button("Send Email"):
            pdf_file = f"news_summary_{datetime.now().strftime('%Y%m%d')}.pdf"
            if os.path.exists(pdf_file):
                send_email(RECEIVER_EMAIL, pdf_file, SENDER_EMAIL, APP_PASSWORD)
                st.success("📧 Email sent!")
            else:
                st.error("❌ PDF not found. Please click 'Generate PDF' first.")

with tab2:
    st.header("📊 News Dashboard")
    all_news = []
    for cat, group in [("Local", st.session_state.get("local_news", [])),
                       ("National", st.session_state.get("national_news", [])),
                       ("Global", st.session_state.get("global_news", []))]:
        for item in group:
            all_news.append({
                "Category": cat,
                "Source": item.get("source", "Unknown"),
                "Title": item["title"]
            })

    if all_news:
        df = pd.DataFrame(all_news)

        st.subheader("🟦 News Count by Category")
        st.bar_chart(df["Category"].value_counts())

        st.subheader("📊 Source Distribution")
        fig = px.pie(df, names="Source", title="News Source Share")
        st.plotly_chart(fig)
    else:
        st.info("ℹ️ No data to show. Fetch news first.")

with tab3:
    st.header("🔍 Search News by Keyword")
    query = st.text_input("Enter keyword")
    if query:
        results = []
        for item in st.session_state.get("local_news", []) + \
                    st.session_state.get("national_news", []) + \
                    st.session_state.get("global_news", []):
            title = str(item.get("title", "") or "")
            summary = str(item.get("summary", "") or "")
            if query.lower() in title.lower() or query.lower() in summary.lower():
                results.append(item)
        if results:
            for r in results:
                display_news_card(r)
        else:
            st.warning("No news found for that keyword.")

# === Auto Mode (Scheduled Mode e.g. for CRON or deployment)
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
    tweets = fetch_tweets(["ndtv", "ANI", "PMOIndia", "BBCWorld", "RahulGandhi", "narendramodi", "POTUS"])
    local_news += tweets[:5]
    national_news += tweets[5:10]
    global_news += tweets[10:]
    pdf_file = create_pdf(local_news, national_news, global_news)
    send_email(RECEIVER_EMAIL, pdf_file, SENDER_EMAIL, APP_PASSWORD)

    # === Auto Mode (For Scheduled Runs)
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
    tweets = fetch_tweets(["ndtv", "ANI", "PMOIndia", "BBCWorld", "RahulGandhi", "narendramodi", "POTUS"])
    local_news += tweets[20:50]
    national_news += tweets[20:50]
    global_news += tweets[20:50]

    pdf_file = create_pdf(local_news, national_news, global_news)
    send_email(RECEIVER_EMAIL, pdf_file, SENDER_EMAIL, APP_PASSWORD)

