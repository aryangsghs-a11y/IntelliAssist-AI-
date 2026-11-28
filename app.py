import streamlit as st
import time
from google import genai
from pypdf import PdfReader
from docx import Document
from datetime import datetime
from zoneinfo import ZoneInfo

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
            p.text for p in doc.paragraphs
        )
        pages.append({"text": text, "page": 1})

    return pages


def ask_gemini(question, pages, language):
    client = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )

    document_text = ""

    for page in pages:
        document_text += (
            f"\n[PAGE {page['page']}]\n"
            f"{page['text']}\n"
        )

    language_instruction = {
        "Hindi": "Answer completely in simple Hindi.",
        "English": "Answer completely in clear English.",
        "Auto": (
            "Answer in the same language used by the user "
            "in their question."
        )
    }

    prompt = f"""
You are IntelliAssist AI, an educational document assistant.

Read the document and answer the user's question.

Rules:
1. Understand the question properly.
2. Give an accurate and complete answer.
3. Explain concepts in easy language.
4. Explain step by step when useful.
5. Give examples when helpful.
6. Use headings and bullet points where useful.
7. If the user requests a short answer, keep it short.
8. If the answer is not in the document, say so clearly.
9. Do not invent information.
10. Mention the source page numbers.

LANGUAGE:
{language_instruction[language]}

DOCUMENT:
{document_text}

QUESTION:
{question}
"""

    delays = [2, 5, 10]

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )
            return response.text

        except Exception as e:
            error_text = str(e).upper()

            temporary_error = any(
                word in error_text
                for word in [
                    "503",
                    "UNAVAILABLE",
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "OVERLOADED"
                ]
            )

            if temporary_error and attempt < 2:
                time.sleep(delays[attempt])
                continue

            if temporary_error:
                raise RuntimeError(
                    "Gemini server abhi busy hai. "
                    "Kuch der baad dobara try karein."
                )

            raise


st.subheader("Upload Your Document")

uploaded_file = st.file_uploader(
    "Upload PDF, TXT or DOCX",
    type=["pdf", "txt", "docx"]
)

if uploaded_file:
    st.session_state.pages = read_document(
        uploaded_file
    )

    st.success("Document uploaded successfully!")

    st.subheader("Ask Your Document")

    language = st.selectbox(
        "Choose Answer Language",
        ["Auto", "Hindi", "English"]
    )

    question = st.text_area(
        "Enter your question",
        placeholder="Ask anything about your document..."
    )

    if st.button("Get Answer"):
        if question.strip():
            try:
                with st.spinner(
                    "IntelliAssist AI is preparing your answer..."
                ):
                    answer = ask_gemini(
                        question,
                        st.session_state.pages,
                        language
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

            except Exception as e:
                st.error(str(e))

        else:
            st.warning("Please enter a question.")

    st.divider()
    st.subheader("Relevant Information")

    search_query = st.text_input(
        "Search in document"
    )

    if st.button("Search Document"):
        if search_query.strip():
            full_text = "\n".join(
                p["text"] for p in st.session_state.pages
            )

            if search_query.lower() in full_text.lower():
                index = full_text.lower().find(
                    search_query.lower()
                )
                st.write(full_text[index:index + 1000])
            else:
                st.info("No matching information found.")

    st.divider()
    st.subheader("Summarize Document")

    if st.button("Summarize Document"):
        try:
            with st.spinner("Preparing summary..."):
                summary = ask_gemini(
                    "Summarize the complete document with important points.",
                    st.session_state.pages,
                    language
                )
            st.write(summary)

        except Exception as e:
            st.error(str(e))

    st.divider()
    st.subheader("Sentiment Analysis")

    if st.button("Analyze Sentiment"):
        text = "\n".join(
            p["text"] for p in st.session_state.pages
        ).lower()

        positive_words = [
            "good", "great", "excellent",
            "happy", "success", "best"
        ]

        negative_words = [
            "bad", "poor", "sad",
            "failure", "problem", "worst"
        ]

        positive = sum(
            text.count(w) for w in positive_words
        )

        negative = sum(
            text.count(w) for w in negative_words
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
        text = "\n".join(
            p["text"] for p in st.session_state.pages
        ).lower()

        if any(w in text for w in [
            "question", "ask", "query"
        ]):
            st.write("Intent: Information Seeking")
        elif any(w in text for w in [
            "buy", "purchase", "order"
        ]):
            st.write("Intent: Purchase")
        else:
            st.write("Intent: General Information")

    st.divider()
    st.subheader("Source Citations")
    st.write(
        "Source page references are included in AI answers."
    )

    st.divider()
    st.subheader("Chat History")

    if st.session_state.chat_history:
        for item in reversed(
            st.session_state.chat_history
        ):
            st.write("**Question:**", item["question"])
            st.write("**Answer:**", item["answer"])
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
