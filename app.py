import streamlit as st
from pypdf import PdfReader
from docx import Document
import io

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
        pdf = PdfReader(file)
        for page in pdf.pages:
            text += page.extract_text() or ""

    elif file.name.endswith(".txt"):
        text = file.getvalue().decode("utf-8")

    elif file.name.endswith(".docx"):
        doc = Document(file)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"

    st.success("Document uploaded successfully!")

    st.subheader("📖 Extracted Text")
    st.text_area(
        "Your document text",
        text,
        height=300
    )

    st.write("Total characters:", len(text))
