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

def display_news_card(item):
    title = item.get("title", "No title")
    summary = item.get("summary", "No summary")
    url = item.get("url", "#")
    image = item.get("urlToImage", "") or "https://via.placeholder.com/150"

    st.markdown(f"""
        <div style="border:1px solid #ddd; border-radius:10px; padding:15px; margin-bottom:15px; background-color:#fff;">
            <div style="display:flex; gap:15px;">
                <img src="{image}" width="150" style="border-radius:8px;" />
                <div style="flex:1;">
                    <h4 style="margin:0;">{title}</h4>
                    <p style="margin-top:5px; font-size:14px; color:#444;">{summary}</p>
                    <a href="{url}" target="_blank" style="font-weight:bold; font-size:13px;">🔗 Read Full Story</a>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# 🔐 Login
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

# === Functions ===
def fetch_rss_news(name, url):
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries[:5]:
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
        "title": a['title'],
        "summary": a.get('description', ''),
        "url": a['url'],
        "source": a.get('source', {}).get('name', 'NewsAPI')
    } for a in articles if a['title']]

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

# === UI ===
st.set_page_config(page_title="🧠 AI News Assistant", layout="wide")
tab1, tab2, tab3 = st.tabs(["📰 News", "📊 Dashboard", "🔍 Search"])

with tab1:
    if st.button("Fetch News"):
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

        st.session_state.local_news = local_news
        st.session_state.national_news = national_news
        st.session_state.global_news = global_news
        st.success("✅ News fetched successfully!")

    if "local_news" in st.session_state:
        for category, data in zip(["Local", "National", "Global"],
                                  [st.session_state.local_news, st.session_state.national_news, st.session_state.global_news]):
            st.subheader(f"{category} News")
            for item in data[:10]:  # or for item in results
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
        st.subheader("News Count by Category")
        st.bar_chart(df["Category"].value_counts())

        st.subheader("Sources Distribution")
        fig = px.pie(df, names="Source", title="News Source Share")
        st.plotly_chart(fig)
    else:
        st.info("ℹ️ No data to show. Fetch news first.")

with tab3:
    st.header("🔍 Search News by Keyword")
    query = st.text_input("Enter keyword")
    if query:
        results = []
        for item in st.session_state.get("local_news", []) + st.session_state.get("national_news", []) + st.session_state.get("global_news", []):
            title = str(item.get("title", "") or "")
            summary = str(item.get("summary", "") or "")
            if query.lower() in title.lower() or query.lower() in summary.lower():
                results.append(item)
        if results:
            for r in results:
                st.markdown(f"**{r['title']}**")
                st.write(r["summary"])
                st.markdown(f"[Link]({r['url']})")
        else:
            st.warning("No news found for that keyword.")

# === Auto Mode (Scheduler)
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
