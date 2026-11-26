import streamlit as st
from pypdf import PdfReader
from docx import Document
from io import BytesIO
import re

st.set_page_config(
    page_title="IntelliAssist AI",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 IntelliAssist AI")
st.write("Smart Document AI Assistant")

st.header("📄 Upload Your Document")

file = st.file_uploader(
    "Upload PDF, TXT or DOCX",
    type=["pdf", "txt", "docx"]
)

if file is not None:

    text = ""

    if file.name.endswith(".pdf"):
        pdf = PdfReader(BytesIO(file.getvalue()))
        for page in pdf.pages:
            text += page.extract_text() or ""

    elif file.name.endswith(".txt"):
        text = file.getvalue().decode("utf-8", errors="replace")

    elif file.name.endswith(".docx"):
        doc = Document(BytesIO(file.getvalue()))
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"

    st.success("Document uploaded successfully!")

    st.subheader("📖 Extracted Text")
    st.text_area("Document Text", text, height=250)

    st.write("Total characters:", len(text))

    st.divider()

    st.header("💬 Ask Questions")

    question = st.text_input(
        "Ask something about your document"
    )

    if st.button("Get Answer"):

        if not text.strip():
            st.warning("No readable text found in document.")

        elif not question.strip():
            st.warning("Please enter a question.")

        else:
            sentences = re.split(r'(?<=[.!?])\s+|\n+', text)

            stop_words = {
                "what", "when", "where", "who", "why",
                "how", "is", "are", "the", "a", "an",
                "of", "in", "to", "for", "and", "on",
                "tell", "me", "about", "please"
            }

            words = set(re.findall(r'\b\w+\b', question.lower()))
            keywords = words - stop_words

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
                st.subheader("📌 Relevant Information")

                for score, sentence in matches[:3]:
                    st.write("•", sentence)
            else:
                st.info(
                    "No matching information found in this document."
                )

st.divider()
st.caption("IntelliAssist AI | Smart Document AI Assistant")

st.divider()
    st.header("📝 Document Summarization")

    if st.button("Summarize Document"):
        if not text.strip():
            st.warning("Please upload a readable document.")
        else:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            summary = " ".join(sentences[:5])

            st.subheader("📌 Document Summary")
            st.write(summary)
