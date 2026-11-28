import streamlit as st
import time
from google import genai
from supabase import create_client
from pypdf import PdfReader
from docx import Document
from io import BytesIO

st.set_page_config(
    page_title="IntelliAssist AI",
    page_icon="🤖",
    layout="wide"
)

# SUPABASE CONNECTION
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# GEMINI CONNECTION
gemini = genai.Client(
    api_key=st.secrets["GEMINI_API_KEY"]
)

MODEL = "gemini-3.5-flash-lite"

# SESSION STATE
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "document_text" not in st.session_state:
    st.session_state.document_text = ""

if "pages" not in st.session_state:
    st.session_state.pages = []


# LOGIN
def login():
    st.title("🤖 IntelliAssist AI")
    st.subheader("Login to your account")

    email = st.text_input("Email Address")
    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button("Login", use_container_width=True):
        try:
            result = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            st.session_state.logged_in = True
            st.session_state.access_token = result.session.access_token
            st.session_state.refresh_token = result.session.refresh_token
            st.session_state.user_id = result.user.id

            st.rerun()

        except Exception as e:
            st.error(f"Login failed:{e}")


if not st.session_state.logged_in:
    login()
    st.stop()


# RESTORE AUTH SESSION
try:
    supabase.auth.set_session(
        st.session_state.access_token,
        st.session_state.refresh_token
    )
except Exception:
    st.session_state.logged_in = False
    st.rerun()


# DOCUMENT READER
def read_document(file):
    text = ""
    pages = []

    if file.name.lower().endswith(".pdf"):
        reader = PdfReader(BytesIO(file.read()))

        for number, page in enumerate(reader.pages, 1):
            content = page.extract_text() or ""
            pages.append(content)
            text += f"\n[PAGE {number}]\n{content}"

    elif file.name.lower().endswith(".txt"):
        text = file.read().decode(
            "utf-8",
            errors="ignore"
        )
        pages = [text]

    elif file.name.lower().endswith(".docx"):
        doc = Document(BytesIO(file.read()))

        text = "\n".join(
            paragraph.text for paragraph in doc.paragraphs
        )
        pages = [text]

    return text, pages


# GEMINI ANSWER
def ask_gemini(prompt):
    for delay in [2, 5, 10]:
        try:
            response = gemini.models.generate_content(
                model=MODEL,
                contents=prompt
            )
            return response.text

        except Exception as error:
            message = str(error)

            if any(code in message for code in [
                "503", "UNAVAILABLE", "429",
                "RESOURCE_EXHAUSTED", "OVERLOADED"
            ]):
                time.sleep(delay)
            else:
                raise error

    return "AI service abhi busy hai. Thodi der baad try karein."


# SAVE CHAT TO SUPABASE
def save_chat(question, answer):
    supabase.table("chat_history").insert({
        "user_id": str(st.session_state.user_id),
        "question": question,
        "answer": answer
    }).execute()


# LOAD PERMANENT HISTORY
def load_history():
    result = (
        supabase.table("chat_history")
        .select("question, answer, created_at")
        .eq("user_id", str(st.session_state.user_id))
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )

    return result.data or []


# MAIN APP
st.title("🤖 IntelliAssist AI")
st.write("Smart Document AI Assistant")

with st.sidebar:
    st.success("Logged in")
    st.caption("Your chats are saved in Supabase.")

    if st.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.logged_in = False
        st.session_state.chat_history = []
        st.rerun()

    language = st.selectbox(
        "Answer Language",
        ["Auto", "Hindi", "English"]
    )


# UPLOAD DOCUMENT
st.subheader("📄 Upload Document")

uploaded_file = st.file_uploader(
    "Upload PDF, TXT or DOCX",
    type=["pdf", "txt", "docx"]
)

if uploaded_file:
    try:
        text, pages = read_document(uploaded_file)

        st.session_state.document_text = text
        st.session_state.pages = pages

        st.success("Document uploaded successfully!")

    except Exception as error:
        st.error(f"Document error: {error}")


# ASK QUESTION
st.subheader("💬 Ask a Question")

question = st.text_area(
    "Write your question here"
)

if st.button("Get Answer"):
    if not st.session_state.document_text:
        st.warning("Please upload a document first.")

    elif not question.strip():
        st.warning("Please enter a question.")

    else:
        prompt = f"""
You are IntelliAssist AI.

Answer in {language} language.
Explain in very simple language.
Use step-by-step explanation and examples.
Use document information only.
Mention page numbers when possible.
If answer is not in document, clearly say so.

DOCUMENT:
{st.session_state.document_text[:100000]}

QUESTION:
{question}
"""

        with st.spinner("Generating answer..."):
            try:
                answer = ask_gemini(prompt)

                save_chat(question, answer)

                st.session_state.chat_history.append({
                    "question": question,
                    "answer": answer
                })

                st.subheader("Answer")
                st.write(answer)

            except Exception as error:
                st.error(f"Error: {error}")


# SUMMARY
st.divider()
st.subheader("📝 Document Summary")

if st.button("Generate Summary"):
    if not st.session_state.document_text:
        st.warning("Upload a document first.")

    else:
        with st.spinner("Creating summary..."):
            try:
                summary = ask_gemini(
                    "Summarize this document in simple "
                    + language
                    + " language:\n"
                    + st.session_state.document_text[:100000]
                )

                st.write(summary)

            except Exception as error:
                st.error(f"Error: {error}")


# DOCUMENT SEARCH
st.divider()
st.subheader("🔍 Search in Document")

search_word = st.text_input("Enter search word")

if st.button("Search"):
    document = st.session_state.document_text

    if not document:
        st.warning("Upload a document first.")

    elif not search_word.strip():
        st.warning("Enter a search word.")

    elif search_word.lower() in document.lower():
        st.success("Word found in document.")

    else:
        st.info("Word not found.")


# SENTIMENT ANALYSIS
st.divider()
st.subheader("😊 Sentiment Analysis")

sentiment_text = st.text_area(
    "Enter text for sentiment analysis",
    key="sentiment_input"
)

if st.button("Analyze Sentiment"):
    positive = ["good", "great", "happy", "excellent", "love"]
    negative = ["bad", "sad", "poor", "hate", "angry"]

    words = sentiment_text.lower().split()

    p = sum(word in positive for word in words)
    n = sum(word in negative for word in words)

    if not sentiment_text.strip():
        st.warning("Enter some text.")

    elif p > n:
        st.success("Positive Sentiment")

    elif n > p:
        st.error("Negative Sentiment")

    else:
        st.info("Neutral Sentiment")


# INTENT ANALYSIS
st.subheader("🎯 Intent Analysis")

intent_text = st.text_input(
    "Enter text for intent analysis"
)

if st.button("Analyze Intent"):
    if not intent_text.strip():
        st.warning("Enter some text.")

    else:
        text = intent_text.lower()

        if any(word in text for word in ["buy", "purchase", "order"]):
            st.write("Intent: Purchase")

        elif any(word in text for word in ["help", "support", "problem"]):
            st.write("Intent: Support")

        elif any(word in text for word in ["learn", "explain", "study"]):
            st.write("Intent: Learning")

        else:
            st.write("Intent: General")


# CHAT HISTORY
st.divider()
st.subheader("💬 Permanent Chat History")

if st.button("Refresh Chat History"):
    try:
        history = load_history()

        for item in history:
            with st.expander(item["question"]):
                st.write(item["answer"])

    except Exception as error:
        st.error(f"History error: {error}")


# DOWNLOAD HISTORY
try:
    history = load_history()

    history_text = ""

    for item in history:
        history_text += (
            "Question: " + item["question"] + "\n"
            + "Answer: " + item["answer"] + "\n\n"
        )

    st.download_button(
        "Download Chat History",
        history_text or "No chat history available.",
        file_name="IntelliAssist_Chat_History.txt",
        mime="text/plain"
    )

except Exception as error:
    st.error(f"History error: {error}")
