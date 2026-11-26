import streamlit as st

st.set_page_config(
    page_title="IntelliAssist AI",
    page_icon="🤖",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background-color: #f5f7fb;
}
.main-title {
    font-size: 36px;
    font-weight: 800;
    color: #172554;
}
.subtitle {
    color: #64748b;
    font-size: 16px;
}
.feature-card {
    background: white;
    padding: 22px;
    border-radius: 14px;
    border: 1px solid #e2e8f0;
    min-height: 135px;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.title("🤖 IntelliAssist AI")
st.sidebar.caption("Smart Document AI Assistant")

page = st.sidebar.radio(
    "NAVIGATION",
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

st.markdown(
    '<div class="main-title">IntelliAssist AI</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="subtitle">Your smart document assistant</div>',
    unsafe_allow_html=True
)

st.divider()

if page == "Dashboard":

    st.subheader("Welcome to your Dashboard 👋")
    st.write("Manage your documents and AI tools in one place.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="feature-card">
        <h3>📄 Upload Documents</h3>
        <p>Upload PDF, TXT and DOCX files.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
        <h3>💬 Ask Questions</h3>
        <p>Interact with your documents.</p>
        </div>
        """, unsafe_allow_html=True)

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("""
        <div class="feature-card">
        <h3>🔍 Semantic Search</h3>
        <p>Find relevant document information.</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="feature-card">
        <h3>📝 Summarization</h3>
        <p>Get short document summaries.</p>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("Upload Your Document")

    file = st.file_uploader(
        "Choose a PDF, TXT or DOCX file",
        type=["pdf", "txt", "docx"]
    )

    if file:
        st.success(f"{file.name} uploaded successfully!")

elif page == "Ask Questions":
    st.subheader("💬 Ask Questions")
    st.text_input("Enter your question")
    st.button("Get Answer")

elif page == "Semantic Search":
    st.subheader("🔍 Semantic Search")
    st.text_input("Search your document")
    st.button("Search")

elif page == "Summarization":
    st.subheader("📝 Document Summarization")
    st.button("Summarize Document")

elif page == "Sentiment Analysis":
    st.subheader("😊 Sentiment Analysis")
    st.button("Analyze Sentiment")

elif page == "Intent Analysis":
    st.subheader("🎯 Intent Analysis")
    st.button("Analyze Intent")

elif page == "Chat History":
    st.subheader("🕘 Chat History")
    st.info("Your conversation history will appear here.")

st.divider()
st.caption("IntelliAssist AI | Smart Document AI Assistant")
