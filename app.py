import streamlit as st
from pypdf import PdfReader
from docx import Document
import re
from collections import Counter

st.set_page_config(
    page_title="IntelliAssist AI",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 IntelliAssist AI")
st.write("Smart Document AI Assistant")

if "document_text" not in st.session_state:
    st.session_state.document_text = ""

if "summary" not in st.session_state:
    st.session_state.summary = ""

st.header("📄 Upload Your Document")

file = st.file_uploader(
    "Upload PDF, TXT or DOCX",
    type=["pdf", "txt", "docx"]
)

if file is not None:
    text = ""

    if file.name.endswith(".pdf"):
        pdf = PdfReader(file)
        for page in pdf.pages:
            text += page.extract_text() or ""

    elif file.name.endswith(".txt"):
        text = file.getvalue().decode("utf-8")

    elif file.name.endswith(".docx"):
        doc = Document(file)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"

    st.session_state.document_text = text
    st.session_state.summary = ""

    st.success("Document uploaded successfully!")

if st.session_state.document_text:
    st.subheader("📖 Extracted Text")

    st.text_area(
        "Your document text",
        st.session_state.document_text,
        height=200
    )

    st.write(
        "Total characters:",
        len(st.session_state.document_text)
    )

    st.divider()
    st.header("📝 Document Summarization")

    if st.button("Generate Summary"):
        text = st.session_state.document_text

        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

        stop_words = {
            "the", "is", "are", "a", "an", "and", "or",
            "of", "to", "in", "for", "with", "on", "by",
            "this", "that", "it", "as", "be", "was", "were"
        }

        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        words = [w for w in words if w not in stop_words]

        frequencies = Counter(words)

        scored = []

        for index, sentence in enumerate(sentences):
            sentence_words = re.findall(
                r'\b[a-zA-Z]+\b',
                sentence.lower()
            )

            score = sum(
                frequencies[word]
                for word in sentence_words
            )

            scored.append((score, index, sentence))

        count = min(5, len(scored))

        best = sorted(
            sorted(scored, reverse=True)[:count],
            key=lambda x: x[1]
        )

        summary = " ".join(item[2] for item in best)

        if summary:
            st.session_state.summary = summary
        else:
            st.session_state.summary = (
                "Summary could not be generated. "
                "Please upload a text-based document."
            )

    if st.session_state.summary:
        st.success("Summary Generated!")
        st.subheader("📌 Your Document Summary")
        st.write(st.session_state.summary)

st.divider()
st.caption("IntelliAssist AI | Smart Document AI Assistant")
