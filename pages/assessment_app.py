
import streamlit as st
import random

st.set_page_config(page_title="📝 Assessment", page_icon="📝", layout="wide")
st.set_page_config(page_title="📝 News Quiz - Daily Current Affairs", layout="wide")

st.title("🧠 Daily Current Affairs Assessment (40 MCQs)")
st.info("10 questions each from Local, National, Global, and Hindi news — great for UPSC/SSC/Defence/etc.")

# Get stored news from session_state
local_news = st.session_state.get("local_news", [])
national_news = st.session_state.get("national_news", [])
global_news = st.session_state.get("global_news", [])
hindi_news = st.session_state.get("hindi_news", [])

# Generate MCQs (1 question per news)
def generate_mcqs(news_list, category):
    questions = []
    for item in news_list[:10]:
        title = item.get("title", "No title")
        base_question = f"What is the main subject of this {category} news?\n\n📰 '{title}'"
        options = ["Politics", "Economy", "Crime", "International", "Environment", "Technology"]
        correct = random.choice(options)  # Simulated answer for now
        random.shuffle(options)
        questions.append({
            "question": base_question,
            "options": options,
            "answer": correct
        })
    return questions

# Build full quiz
quiz_data = (
    generate_mcqs(local_news, "Local") +
    generate_mcqs(national_news, "National") +
    generate_mcqs(global_news, "Global") +
    generate_mcqs(hindi_news, "Hindi")
)

# Display quiz
user_answers = {}
score = 0

st.subheader("📋 Answer the following:")

if st.button("✅ Submit Quiz"):
    st.subheader("📊 Results")
    score = 0
    for i, q in enumerate(quiz_data, 1):
        if user_answers[i] == q["answer"]:
            st.success(f"✅ Q{i} is Correct!")
            score += 1
        else:
            st.error(f"❌ Q{i} is Wrong. Correct Answer: {q['answer']}")
    st.info(f"🎯 Your Score: {score} / {len(quiz_data)}")

# Submit button
if st.button("✅ Submit Quiz"):
    st.subheader("📊 Results")
    for i, q in enumerate(quiz_data, 1):
        if user_answers[i] == q["answer"]:
            st.success(f"✅ Q{i} is Correct!")
            score += 1
        else:
            st.error(f"❌ Q{i} is Wrong. Correct Answer: {q['answer']}")
    st.info(f"🎯 Your Score: {score} / {len(quiz_data)}")

