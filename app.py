import streamlit as st
from pypdf import PdfReader
from docx import Document
from datetime import datetime
from zoneinfo import ZoneInfo
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

st.set_page_config(
    page_title="IntelliAssist AI",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 IntelliAssist AI")
st.write("Smart Document AI Assistant")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "pages" not in st.session_state:
    st.session_state.pages = []

uploaded_file = st.file_uploader(
    "Upload PDF, TXT or DOCX",
    type=["pdf", "txt", "docx"]
)


def read_document(file):
    pages = []

    if file.name.endswith(".pdf"):
        pdf = PdfReader(file)

        for i, page in enumerate(pdf.pages):
            pages.append({
                "text": page.extract_text() or "",
                "page": i + 1
            })

    elif file.name.endswith(".txt"):
        text = file.read().decode(
            "utf-8", errors="ignore"
        )
        pages.append({"text": text, "page": 1})

    elif file.name.endswith(".docx"):
        doc = Document(file)
        text = "\n".join(
            paragraph.text for paragraph in doc.paragraphs
        )
        pages.append({"text": text, "page": 1})

    return pages


def get_sentences(pages):
    sentences = []

    for page in pages:
        parts = re.split(
            r"(?<=[.!?])\s+|\n+",
            page["text"]
        )

        for part in parts:
            part = part.strip()

            if len(part.split()) >= 3:
                sentences.append({
                    "text": part,
                    "page": page["page"]
                })

    return sentences


def find_answer(question, sentences):
    if not sentences:
        return [], []

    texts = [item["text"] for item in sentences]

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2)
        )

        matrix = vectorizer.fit_transform(
            texts + [question]
        )

        scores = cosine_similarity(
            matrix[-1],
            matrix[:-1]
        ).flatten()

        best_indices = scores.argsort()[::-1][:5]

        results = []

        for index in best_indices:
            if scores[index] > 0.01:
                results.append({
                    "text": sentences[index]["text"],
                    "page": sentences[index]["page"],
                    "score": scores[index]
                })

        return results, scores

    except ValueError:
        return [], []


def answer_question(question, pages):
    sentences = get_sentences(pages)

    results, scores = find_answer(
        question,
        sentences
    )

    if not results:
        return (
            "Is question se related information "
            "PDF mein nahi mili."
        )

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    answer = "\n\n".join(
        item["text"] for item in results
    )

    source_pages = sorted(set(
        item["page"] for item in results
    ))

    answer += "\n\nSource Page: "
    answer += ", ".join(
        str(page) for page in source_pages
    )

    return answer


if uploaded_file:
    st.session_state.pages = read_document(
        uploaded_file
    )

    st.success("Document uploaded successfully!")

    full_text = "\n".join(
        page["text"]
        for page in st.session_state.pages
    )

    st.subheader("Ask Your Document")

    question = st.text_input(
        "Enter any question",
        placeholder="Ask anything about your PDF..."
    )

    if st.button("Get Answer"):
        if question.strip():
            answer = answer_question(
                question,
                st.session_state.pages
            )

            st.subheader("Answer")
            st.write(answer)

            st.session_state.chat_history.append({
                "question": question,
                "answer": answer,
                "date_time": datetime.now(
                    ZoneInfo("Asia/Kolkata")
                ).strftime("%d-%m-%Y %I:%M %p")
            })
        else:
            st.warning("Please enter a question.")

    st.divider()

    st.subheader("Relevant Information")

    search_query = st.text_input(
        "Search in document"
    )

    if st.button("Search Document"):
        if search_query.strip():
            sentences = get_sentences(
                st.session_state.pages
            )

            results, scores = find_answer(
                search_query,
                sentences
            )

            if results:
                for item in results:
                    st.write(item["text"])
                    st.caption(
                        f"Source Page: {item['page']}"
                    )
            else:
                st.info("No relevant information found.")

    st.divider()

    st.subheader("Summarize Document")

    if st.button("Summarize Document"):
        sentences = get_sentences(
            st.session_state.pages
        )

        summary = " ".join(
            item["text"] for item in sentences[:5]
        )

        st.write(
            summary if summary else "No text found."
        )

    st.divider()

    st.subheader("Sentiment Analysis")

    if st.button("Analyze Sentiment"):
        positive_words = [
            "good", "great", "excellent",
            "happy", "success", "best", "positive"
        ]

        negative_words = [
            "bad", "poor", "sad",
            "failure", "problem", "negative", "worst"
        ]

        text = full_text.lower()

        positive = sum(
            text.count(word) for word in positive_words
        )

        negative = sum(
            text.count(word) for word in negative_words
        )

        if positive > negative:
            st.write("Sentiment: Positive")
        elif negative > positive:
            st.write("Sentiment: Negative")
        else:
            st.write("Sentiment: Neutral")

    st.divider()

    st.subheader("Intent Analysis")

    if st.button("Analyze Intent"):
        text = full_text.lower()

        if any(word in text for word in [
            "question", "ask", "query"
        ]):
            st.write("Intent: Information Seeking")

        elif any(word in text for word in [
            "buy", "purchase", "order"
        ]):
            st.write("Intent: Purchase")

        else:
            st.write("Intent: General Information")

    st.divider()

    st.subheader("Source Citations")
    st.write(
        "Source page numbers are shown with answers "
        "and search results."
    )

    st.divider()

    st.subheader("Chat History")

    if st.session_state.chat_history:
        for item in reversed(
            st.session_state.chat_history
        ):
            st.write("Question:", item["question"])
            st.write("Answer:", item["answer"])

            st.caption(
                "Date & Time (India): "
                + item["date_time"]
            )

            st.divider()
    else:
        st.info("No chat history yet.")

else:
    st.info(
        "Please upload a PDF, TXT or DOCX file to begin."
    )
