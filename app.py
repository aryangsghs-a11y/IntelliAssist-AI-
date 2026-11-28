import streamlit as st
import time
from google import genai
from supabase import create_client
from pypdf import PdfReader
from docx import Document
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="IntelliAssist AI",
    page_icon="🤖",
    layout="wide"
)

# CONNECTIONS
try:
    supabase = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

    gemini = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )

except Exception as error:
    st.error(f"Connection error: {error}")
    st.stop()

MODEL = "gemini-3.5-flash-lite"

# SESSION STATE
defaults = {
    "access_token": None,
    "refresh_token": None,
    "user_id": None,
    "logged_in": False,
    "document_text": "",
    "pages": [],
    "chat_history": []
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def clear_login():
    st.session_state.logged_in = False
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user_id = None
    st.session_state.chat_history = []


# LOGIN
def login():
    st.title("🤖 IntelliAssist AI")
    st.subheader("Login to your account")

    with st.form("login_form"):
        email = st.text_input("Email Address")
        password = st.text_input(
            "Password",
            type="password"
        )

        submitted = st.form_submit_button(
            "Login",
            use_container_width=True
        )

    if submitted:
        if not email.strip() or not password:
            st.warning("Email and password are required.")

        else:
            try:
                result = supabase.auth.sign_in_with_password({
                    "email": email.strip(),
                    "password": password
                })

                if not result.session or not result.user:
                    st.error("Login session could not be created.")
                    return

                st.session_state.access_token = (
                    result.session.access_token
                )

                st.session_state.refresh_token = (
                    result.session.refresh_token
                )

                st.session_state.user_id = str(
                    result.user.id
                )

                st.session_state.logged_in = True

                st.success("Login successful!")
                st.rerun()

            except Exception as error:
                st.error(f"Login failed: {error}")


# RESTORE LOGIN SESSION
if (
    st.session_state.access_token
    and st.session_state.refresh_token
):
    try:
        supabase.auth.set_session(
            st.session_state.access_token,
            st.session_state.refresh_token
        )

        st.session_state.logged_in = True

    except Exception:
        clear_login()


if not st.session_state.logged_in:
    login()
    st.stop()


# DOCUMENT READER
def read_document(file):
    text = ""
    pages = []

    filename = file.name.lower()

    if filename.endswith(".pdf"):
        reader = PdfReader(BytesIO(file.read()))

        for number, page in enumerate(reader.pages, 1):
            content = page.extract_text() or ""

            pages.append({
                "page": number,
                "text": content
            })

            text += f"\n[PAGE {number}]\n{content}"

    elif filename.endswith(".txt"):
        text = file.read().decode(
            "utf-8",
            errors="ignore"
        )

        pages.append({
            "page": 1,
            "text": text
        })

    elif filename.endswith(".docx"):
        doc = Document(BytesIO(file.read()))

        text = "\n".join(
            paragraph.text
            for paragraph in doc.paragraphs
        )

        pages.append({
            "page": 1,
            "text": text
        })

    return text, pages


# GEMINI ANSWER
def ask_gemini(question, document, language):
    if language == "Hindi":
        instruction = "Answer completely in simple Hindi."

    elif language == "English":
        instruction = "Answer completely in clear English."

    else:
        instruction = (
            "Answer in the same language used in the user's question."
        )

    prompt = f"""
You are IntelliAssist AI, a document assistant.

Follow these rules:
1. Read the document carefully.
2. Answer using information from the document.
3. Explain in simple language.
4. Give examples when useful.
5. Explain step by step when needed.
6. Mention source page numbers when possible.
7. Do not invent information.
8. If the answer is not in the document, say so clearly.

LANGUAGE:
{instruction}

DOCUMENT:
{document[:100000]}

QUESTION:
{question}
"""

    delays = [2, 5, 10]

    for attempt in range(3):
        try:
            response = gemini.models.generate_content(
                model=MODEL,
                contents=prompt
            )

            if response.text:
                return response.text

            return "AI did not return an answer. Please try again."

        except Exception as error:
            message = str(error).upper()

            temporary = any(
                code in message
                for code in [
                    "503",
                    "UNAVAILABLE",
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "OVERLOADED"
                ]
            )

            if temporary and attempt < 2:
                time.sleep(delays[attempt])
                continue

            raise error


# SAVE CHAT
def save_chat(question, answer):
    supabase.table("chat_history").insert({
        "user_id": str(st.session_state.user_id),
        "question": question,
        "answer": answer
    }).execute()


# LOAD CHAT HISTORY
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
    st.success("Logged in successfully")

    st.caption(
        "Your chat history is saved permanently."
    )

    language = st.selectbox(
        "Choose Answer Language",
        ["Auto", "Hindi", "English"]
    )

    if st.button("Logout", use_container_width=True):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass

        clear_login()
        st.rerun()


# DOCUMENT UPLOAD
st.divider()
st.subheader("📄 Upload Your Document")

uploaded_file = st.file_uploader(
    "Upload PDF, TXT or DOCX",
    type=["pdf", "txt", "docx"]
)

if uploaded_file:
    try:
        text, pages = read_document(uploaded_file)

        if not text.strip():
            st.warning(
                "No readable text found in this document."
            )

        else:
            st.session_state.document_text = text
            st.session_state.pages = pages

            st.success("Document uploaded successfully!")

    except Exception as error:
        st.error(f"Document error: {error}")


# ASK QUESTION
st.divider()
st.subheader("💬 Ask a Question")

question = st.text_area(
    "Write your question here",
    placeholder="Ask anything about your document..."
)

if st.button("🤖 Get Answer"):
    if not st.session_state.document_text:
        st.warning("Please upload a document first.")

    elif not question.strip():
        st.warning("Please enter your question.")

    else:
        try:
            with st.spinner("Generating answer..."):
                answer = ask_gemini(
                    question,
                    st.session_state.document_text,
                    language
                )

            save_chat(question, answer)

            st.session_state.chat_history.append({
                "question": question,
                "answer": answer
            })

            st.subheader("Answer")
            st.write(answer)

        except Exception as error:
            st.error(f"Answer error: {error}")


# SUMMARY
st.divider()
st.subheader("📝 Document Summary")

if st.button("Generate Summary"):
    if not st.session_state.document_text:
        st.warning("Upload a document first.")

    else:
        try:
            with st.spinner("Creating summary..."):
                summary = ask_gemini(
                    "Summarize the complete document with important points.",
                    st.session_state.document_text,
                    language
                )

            st.write(summary)

        except Exception as error:
            st.error(f"Summary error: {error}")


# DOCUMENT SEARCH
st.divider()
st.subheader("🔍 Search in Document")

search_word = st.text_input(
    "Enter search word"
)

if st.button("Search Document"):
    document = st.session_state.document_text

    if not document:
        st.warning("Upload a document first.")

    elif not search_word.strip():
        st.warning("Enter a search word.")

    elif search_word.lower() in document.lower():
        index = document.lower().find(
            search_word.lower()
        )

        st.success("Word found in document.")

        st.write(
            document[index:index + 1000]
        )

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
    positive = [
        "good", "great", "happy",
        "excellent", "love", "success"
    ]

    negative = [
        "bad", "sad", "poor",
        "hate", "angry", "failure"
    ]

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
st.divider()
st.subheader("🎯 Intent Analysis")

intent_text = st.text_input(
    "Enter text for intent analysis"
)

if st.button("Analyze Intent"):
    if not intent_text.strip():
        st.warning("Enter some text.")

    else:
        text = intent_text.lower()

        if any(word in text for word in [
            "buy", "purchase", "order"
        ]):
            st.write("Intent: Purchase")

        elif any(word in text for word in [
            "help", "support", "problem"
        ]):
            st.write("Intent: Support")

        elif any(word in text for word in [
            "learn", "explain", "study"
        ]):
            st.write("Intent: Learning")

        else:
            st.write("Intent: General Information")


# PERMANENT CHAT HISTORY
st.divider()
st.subheader("💬 Permanent Chat History")

try:
    history = load_history()

    if history:
        history_text = ""

        for item in history:
            with st.expander(item["question"]):
                st.write(item["answer"])

                if item.get("created_at"):
                    st.caption(
                        "Saved: " + str(item["created_at"])
                    )

            history_text += (
                "Question: " + item["question"] + "\n"
                + "Answer: " + item["answer"] + "\n\n"
                + "-------------------------\n\n"
            )

        st.download_button(
            "📥 Download Chat History",
            history_text,
            file_name="IntelliAssist_Chat_History.txt",
            mime="text/plain"
        )

    else:
        st.info("No chat history yet.")

except Exception as error:
    st.error(f"History error: {error}")
