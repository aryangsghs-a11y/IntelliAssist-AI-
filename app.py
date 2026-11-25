import streamlit as st

st.set_page_config(
    page_title="IntelliAssist AI",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 IntelliAssist AI")
st.subheader("Smart Document AI Assistant")

st.write(
    "Upload your documents and interact with AI."
)

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Feature",
    [
        "Dashboard",
        "Ask Questions",
        "Semantic Search",
        "Summarization",
        "Sentiment Analysis",
        "Intent Analysis",
        "Chat History"
    ]
)

st.header("📄 Upload Document")

file = st.file_uploader(
    "Upload PDF, TXT or DOCX",
    type=["pdf", "txt", "docx"]
)

if file:
    st.success(f"{file.name} uploaded successfully!")

if page == "Dashboard":
    st.write("Welcome to IntelliAssist AI!")

elif page == "Ask Questions":
    question = st.text_input("Ask a question")
    st.button("Get Answer")

elif page == "Semantic Search":
    search = st.text_input("Search your document")
    st.button("Search")

elif page == "Summarization":
    st.button("Summarize Document")

elif page == "Sentiment Analysis":
    st.button("Analyze Sentiment")

elif page == "Intent Analysis":
    st.button("Analyze Intent")

elif page == "Chat History":
    st.write("Your conversation history will appear here.")
