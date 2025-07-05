
import streamlit as st
import random
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="📝 Assessment", page_icon="📝", layout="wide")

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
    for idx, item in enumerate(news_list[:10]):
        title = item.get("title", "No title")
        base_question = f"What is the main subject of this {category} news?\n\n📰 '{title}'"
        options = ["Politics", "Economy", "Crime", "International", "Environment", "Technology"]
        correct = random.choice(options)  # Simulated answer
        explanation = f"This headline is mostly related to **{correct}** topics in competitive exams."
        random.shuffle(options)
        questions.append({
            "id": f"{category}_{idx}",
            "question": base_question,
            "options": options,
            "answer": correct,
            "explanation": explanation
        })
    return questions

# Build full quiz
quiz_data = (
    generate_mcqs(local_news, "Local") +
    generate_mcqs(national_news, "National") +
    generate_mcqs(global_news, "Global") +
    generate_mcqs(hindi_news, "Hindi")
)

# Display questions
user_answers = {}
score = 0

st.subheader("📋 Answer the following:")

for i, q in enumerate(quiz_data, 1):
    st.markdown(f"**Q{i}: {q['question']}**")
    user_answers[i] = st.radio("Choose one:", q["options"], key=q["id"])
    st.markdown("---")

# Session state to track history
if "quiz_history" not in st.session_state:
    st.session_state.quiz_history = []

# ✅ Submit Button and Result
if st.button("✅ Submit Quiz"):
    st.subheader("📊 Results")
    for i, q in enumerate(quiz_data, 1):
        if user_answers[i] == q["answer"]:
            st.success(f"✅ Q{i} is Correct!")
            score += 1
        else:
            st.error(f"❌ Q{i} is Wrong. Correct Answer: {q['answer']}")
            st.info(f"📘 Explanation: {q['explanation']}")
    st.info(f"🎯 Your Score: {score} / {len(quiz_data)}")

    # ✅ Save to session history
    st.session_state.quiz_history.append({"score": score, "total": len(quiz_data)})

    # ✅ Show chart
    if len(st.session_state.quiz_history) > 1:
        st.subheader("📈 Score Progress")
        df = pd.DataFrame(st.session_state.quiz_history)
        df["Attempt"] = df.index + 1
        fig = px.line(df, x="Attempt", y="score", markers=True, title="Your Quiz Score Over Time")
        st.plotly_chart(fig)
