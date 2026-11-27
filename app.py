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
        text = file.read().decode("utf-8", errors="ignore")
        pages.append({"text": text, "page": 1})

    elif file.name.endswith(".docx"):
        doc = Document(file)
        text = "\n".join(p.text for p in doc.paragraphs)
        pages.append({"text": text, "page": 1})

    return pages


def get_questions(text):
    pattern = r"(?m)^\s*(\d{1,2})[.)]\s*(.+?)(?=^\s*\d{1,2}[.)]\s*|\Z)"
    matches = re.findall(pattern, text, re.S)

    questions = {}
    for number, question in matches:
        questions[int(number)] = re.sub(r"\s+", " ", question).strip()

    return questions


def get_sentences(pages):
    sentences = []

    for page in pages:
        parts = re.split(r"(?<=[.!?])\s+|\n+", page["text"])

        for part in parts:
            part = part.strip()
            if len(part.split()) >= 4:
                sentences.append({
                    "text": part,
                    "page": page["page"]
                })

    return sentences


def find_answer(question, sentences):
    if not sentences:
        return [], []

    texts = [s["text"] for s in sentences]

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2)
        )
        matrix = vectorizer.fit_transform(texts + [question])
        scores = cosine_similarity(
            matrix[-1],
            matrix[:-1]
        ).flatten()

        best = scores.argsort()[::-1][:3]

        results = []
        for index in best:
            if scores[index] > 0:
                results.append(sentences[index])

        return results, scores

    except ValueError:
        return [], []


def solve_one(question, sentences):
    results, scores = find_answer(question, sentences)

    if not results:
        return "Is question ka answer PDF mein nahi mila."

    answer = " ".join(item["text"] for item in results)
    pages = sorted(set(item["page"] for item in results))

    return (
        answer
        + "\n\nSource Page: "
        + ", ".join(map(str, pages))
    )


def solve_instruction(instruction, pages):
    full_text = "\n".join(p["text"] for p in pages)
    questions = get_questions(full_text)
    sentences = get_sentences(pages)

    numbers = re.findall(
        r"(?:question|ques|q)\s*(?:number|no\.?)?\s*(\d+)|(\d+)\s*(?:number|no\.?)",
        instruction.lower()
    )

    selected = [
        int(a or b) for a, b in numbers
    ]

    all_requested = any(
        word in instruction.lower()
        for word in ["all", "all questions", "saare", "sabhi", "pura", "poore"]
    )

    if all_requested:
        selected = sorted(questions.keys())

    if selected:
        output = []

        for number in selected:
            if number not in questions:
                output.append(
                    f"Question {number}: PDF mein nahi mila."
                )
                continue

            question = questions[number]
            answer = solve_one(question, sentences)

            output.append(
                f"Question {number}: {question}\n\nAnswer: {answer}"
            )

        return "\n\n--------------------\n\n".join(output)

    return solve_one(instruction, sentences)


if uploaded_file:
    st.session_state.pages = read_document(uploaded_file)
    st.success("Document uploaded successfully!")

    full_text = "\n".join(
        p["text"] for p in st.session_state.pages
    )

    st.subheader("Ask Your Document")

    question = st.text_input(
        "Write your question or instruction",
        placeholder="Example: 5 number question ka answer do"
    )

    if st.button("Get Answer"):
        if question.strip():
            answer = solve_instruction(
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
    search_query = st.text_input("Search in document")

    if st.button("Search Document"):
        if search_query.strip():
            sentences = get_sentences(st.session_state.pages)
            results, scores = find_answer(search_query, sentences)

            for item in results:
                st.write(item["text"])
                st.caption(f"Page {item['page']}")

    st.divider()

    st.subheader("Summarize Document")

    if st.button("Summarize Document"):
        sentences = get_sentences(st.session_state.pages)
        summary = " ".join(
            item["text"] for item in sentences[:5]
        )
        st.write(summary if summary else "No text found.")

    st.divider()

    st.subheader("Sentiment Analysis")

    if st.button("Analyze Sentiment"):
        positive = [
            "good", "great", "excellent", "happy",
            "success", "best", "positive"
        ]
        negative = [
            "bad", "poor", "sad", "failure",
            "problem", "negative", "worst"
        ]

        text = full_text.lower()
        pos = sum(text.count(w) for w in positive)
        neg = sum(text.count(w) for w in negative)

        if pos > neg:
            st.write("Sentiment: Positive")
        elif neg > pos:
            st.write("Sentiment: Negative")
        else:
            st.write("Sentiment: Neutral")

    st.divider()

    st.subheader("Intent Analysis")

    if st.button("Analyze Intent"):
        text = full_text.lower()

        if any(w in text for w in ["question", "ask", "query"]):
            st.write("Intent: Information Seeking")
        elif any(w in text for w in ["buy", "purchase", "order"]):
            st.write("Intent: Purchase")
        else:
            st.write("Intent: General Information")

    st.divider()

    st.subheader("Source Citations")
    st.write(
        "Source pages are displayed with answers above."
    )

    st.divider()

    st.subheader("Chat History")

    if st.session_state.chat_history:
        for item in reversed(st.session_state.chat_history):
            st.write("**Question:**", item["question"])
            st.write("**Answer:**", item["answer"])
            st.caption(
                "Date & Time (India): " + item["date_time"]
            )
            st.divider()
    else:
        st.info("No chat history yet.")

else:
    st.info("Please upload a PDF, TXT or DOCX file to begin.")
