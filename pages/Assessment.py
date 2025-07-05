import streamlit as st
import random

import streamlit as st

# 🔐 Login and sidebar visibility
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "show_sidebar" not in st.session_state:
    st.session_state.show_sidebar = False
if "trigger_rerun" not in st.session_state:
    st.session_state.trigger_rerun = False

# Hide sidebar unless logged in and toggle is ON
if not st.session_state.logged_in or not st.session_state.show_sidebar:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

# Show toggle only after login
if st.session_state.logged_in:
    if st.button("☰"):
        st.session_state.show_sidebar = not st.session_state.show_sidebar
        st.session_state.trigger_rerun = True

# Rerun on next frame
if st.session_state.trigger_rerun:
    st.session_state.trigger_rerun = False
    st.rerun()  # ✅ use this, NOT experimental_rerun()

st.set_page_config(page_title="📝 Assessment", page_icon="📝", layout="wide")

st.title("🧠 Daily Current Affairs Assessment (40 MCQs)")
st.info("10 questions each from Local, National, Global, and Hindi news — great for UPSC/SSC/Defence/etc.")

local_news = st.session_state.get("local_news", [])
national_news = st.session_state.get("national_news", [])
global_news = st.session_state.get("global_news", [])
hindi_news = st.session_state.get("hindi_news", [])

def generate_mcqs(news_list, category):
    questions = []
    for idx, item in enumerate(news_list[:10]):
        title = item.get("title", "No title")
        base_question = f"What is the main subject of this {category} news?\n\n📰 '{title}'"
        options = random.sample(["Politics", "Economy", "Crime", "Technology", "Environment", "International"], 4)
        correct = random.choice(options)
        explanation = f"This headline relates to **{correct}**."
        questions.append({
            "id": f"{category}_{idx}",
            "question": base_question,
            "options": options,
            "answer": correct,
            "explanation": explanation
        })
    return questions

quiz_data = (
    generate_mcqs(local_news, "Local") +
    generate_mcqs(national_news, "National") +
    generate_mcqs(global_news, "Global") +
    generate_mcqs(hindi_news, "Hindi")
)

user_answers = {}
st.subheader("📋 Answer the following:")

for i, q in enumerate(quiz_data, 1):
    st.markdown(f"**Q{i}: {q['question']}**")
    user_answers[i] = st.radio("Choose one:", q["options"], key=q["id"], index=None)
    st.markdown("---")

if st.button("✅ Submit Quiz"):
    score = 0
    st.subheader("📊 Results")
    for i, q in enumerate(quiz_data, 1):
        if user_answers[i] == q["answer"]:
            st.success(f"✅ Q{i} Correct!")
            score += 1
        else:
            st.error(f"❌ Q{i} Wrong. Correct: {q['answer']}")
            st.info(f"🧠 Explanation: {q['explanation']}")
    st.info(f"🎯 Final Score: {score} / {len(quiz_data)}")
