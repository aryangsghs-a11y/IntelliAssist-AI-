import streamlit as st
from pypdf import PdfReader
from docx import Document
from io import BytesIO
from datetime import datetime
import re

st.set_page_config(
    page_title="IntelliAssist AI",
    page_icon="🤖",
    layout="wide"
)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.title("🤖 IntelliAssist AI")
st.write("Smart Document AI Assistant")

# Document Upload
st.header("📄 Upload Your Document")

file = st.file_uploader(
    "Upload PDF, TXT or DOCX",
    type=["pdf", "txt", "docx"]
)

text = ""
page_texts = []

if file is not None:

    if file.name.endswith(".pdf"):
        pdf = PdfReader(BytesIO(file.getvalue()))

        for page_number, page in enumerate(pdf.pages, start=1):
            page_content = page.extract_text() or ""
            page_texts.append((page_number, page_content))
            text += page_content + "\n"

    elif file.name.endswith(".txt"):
        text = file.getvalue().decode("utf-8", errors="replace")
        page_texts = [(1, text)]

    elif file.name.endswith(".docx"):
        doc = Document(BytesIO(file.getvalue()))
        text = "\n".join(
            paragraph.text for paragraph in doc.paragraphs
        )
        page_texts = [(1, text)]

    st.success("Document uploaded successfully!")
    st.subheader("📖 Extracted Text")
    st.text_area("Document Text", text, height=250)
    st.write("Total characters:", len(text))

# Ask Questions
st.divider()
st.header("💬 Ask Questions")

question = st.text_input(
    "Ask something about your document"
)

if st.button("Get Answer"):

    if file is None or not text.strip():
        st.warning("Please upload a readable document first.")

    elif not question.strip():
        st.warning("Please enter a question.")

    else:
        stop_words = {
            "what", "when", "where", "who", "why",
            "how", "is", "are", "the", "a", "an",
            "of", "in", "to", "for", "and", "on",
            "tell", "me", "about", "please"
        }

        keywords = set(
            re.findall(r'\b\w+\b', question.lower())
        ) - stop_words

        matches = []

        for page_number, page_content in page_texts:
            sentences = re.split(
                r'(?<=[.!?])\s+|\n+', page_content
            )

            for sentence in sentences:
                sentence = sentence.strip()

                if not sentence:
                    continue

                sentence_words = set(
                    re.findall(r'\b\w+\b', sentence.lower())
                )

                score = len(keywords & sentence_words)

                if score > 0:
                    matches.append(
                        (score, sentence, page_number)
                    )

        matches.sort(key=lambda item: item[0], reverse=True)

        if matches:
            answer = "\n".join(
                sentence for score, sentence, page in matches[:3]
            )

            st.subheader("📌 Relevant Information")
            st.write(answer)

            st.subheader("📚 Source Citations")

            shown_pages = sorted({
                page for score, sentence, page in matches[:3]
            })

            for page in shown_pages:
                st.write("Source: Page", page)

        else:
            answer = "No matching information found in this document."
            st.info(answer)

        st.session_state.chat_history.append({
            "question": question,
            "answer": answer,
            "date_time": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        })

# Document Summarization
st.divider()
st.header("📝 Document Summarization")

if file is not None and st.button("Summarize Document"):

    if text.strip():
        sentences = re.split(r'(?<=[.!?])\s+', text)
        summary = " ".join(sentences[:5])

        st.subheader("📌 Document Summary")
        st.write(summary)

    else:
        st.warning("No readable text found.")

# Smart Document Search
st.divider()
st.header("🔎 Smart Document Search")

if file is not None and text.strip():

    search_query = st.text_input(
        "Search information in your document"
    )

    if st.button("Search Document"):

        if not search_query.strip():
            st.warning("Please enter something to search.")

        else:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            sentences = [
                s.strip()
                for s in re.split(r'(?<=[.!?])\s+|\n+', text)
                if s.strip()
            ]

            if sentences:
                try:
                    vectorizer = TfidfVectorizer()
                    vectors = vectorizer.fit_transform(
                        sentences + [search_query]
                    )

                    scores = cosine_similarity(
                        vectors[-1], vectors[:-1]
                    ).flatten()

                    best_matches = scores.argsort()[::-1][:3]

                    st.subheader("📌 Search Results")
                    found = False

                    for index in best_matches:
                        if scores[index] > 0:
                            st.write("•", sentences[index])
                            found = True

                    if not found:
                        st.info("No matching information found.")

                except ValueError:
                    st.info("No matching information found.")

# Sentiment Analysis
st.divider()
st.header("😊 Sentiment Analysis")

if file is not None and text.strip():

    if st.button("Analyze Sentiment"):

        positive_words = {
            "good", "great", "happy", "excellent",
            "love", "best", "wonderful", "success",
            "beautiful", "positive"
        }

        negative_words = {
            "bad", "sad", "poor", "hate",
            "worst", "terrible", "failure",
            "problem", "negative", "angry"
        }

        words = set(re.findall(r'\b\w+\b', text.lower()))

        positive_count = len(words & positive_words)
        negative_count = len(words & negative_words)

        if positive_count > negative_count:
            st.success("😊 Positive Sentiment")
        elif negative_count > positive_count:
            st.error("😟 Negative Sentiment")
        else:
            st.info("😐 Neutral Sentiment")

        st.write("Positive words:", positive_count)
        st.write("Negative words:", negative_count)

# Intent Analysis
st.divider()
st.header("🎯 Intent Analysis")

user_intent = st.text_input(
    "Enter your message to identify its intent"
)

if st.button("Analyze Intent"):

    if not user_intent.strip():
        st.warning("Please enter a message.")

    else:
        message = user_intent.lower()

        if any(word in message for word in [
            "summarize", "summary", "short notes"
        ]):
            intent = "Summarization"

        elif any(word in message for word in [
            "search", "find", "look for"
        ]):
            intent = "Search"

        elif any(word in message for word in [
            "explain", "describe", "meaning"
        ]):
            intent = "Explanation"

        elif any(word in message for word in [
            "what", "who", "when", "where", "why", "how"
        ]):
            intent = "Question"

        else:
            intent = "General Request"

        st.success("Detected Intent: " + intent)

        if file is not None and text.strip():

            sentences = re.split(
                r'(?<=[.!?])\s+|\n+', text
            )

            stop_words = {
                "please", "explain", "tell", "me",
                "about", "what", "is", "the", "a",
                "an", "of", "in", "to", "how"
            }

            keywords = set(
                re.findall(r'\b\w+\b', user_intent.lower())
            ) - stop_words

            matches = []

            for sentence in sentences:
                sentence_words = set(
                    re.findall(r'\b\w+\b', sentence.lower())
                )
                score = len(keywords & sentence_words)

                if score > 0:
                    matches.append((score, sentence.strip()))

            matches.sort(key=lambda item: item[0], reverse=True)

            if matches:
                st.subheader("📖 Answer from Your Document")

                for score, sentence in matches[:5]:
                    st.write("•", sentence)
            else:
                st.info("No relevant information found in document.")

# Chat History
st.divider()
st.header("💬 Chat History")

if st.session_state.chat_history:

    st.subheader("📚 Previous Conversations")

    for chat in reversed(st.session_state.chat_history):
        st.write("**Date & Time:**", chat["date_time"])
        st.write("**You:**", chat["question"])
        st.write("**Answer:**", chat["answer"])
        st.divider()

else:
    st.info("Your conversations will appear here.")

st.caption("IntelliAssist AI | Smart Document AI Assistant")
