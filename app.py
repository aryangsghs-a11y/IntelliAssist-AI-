import streamlit as st
import time
from google import genai
from supabase import create_client
from pypdf import PdfReader
from docx import Document
from datetime import datetime
from zoneinfo import ZoneInfo

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

# SESSION STATE
defaults = {
    "logged_in": False,
    "access_token": None,
    "refresh_token": None,
    "user_id": None,
    "chat_history": [],
    "pages": []
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# LOGIN AND SIGNUP
def authentication_page():
    st.title("🤖 IntelliAssist AI")
    st.write("Smart Document AI Assistant")

    login_tab, signup_tab = st.tabs(
        ["Login", "Create Account"]
    )

    with login_tab:
        st.subheader("Login to your account")

        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input(
                "Password",
                type="password"
            )

            login_button = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        if login_button:
            if not email.strip() or not password:
                st.warning("Enter email and password.")

            else:
                try:
                    result = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })

                    st.session_state.logged_in = True
                    st.session_state.access_token = (
                        result.session.access_token
                    )
                    st.session_state.refresh_token = (
                        result.session.refresh_token
                    )
                    st.session_state.user_id = result.user.id

                    st.rerun()

                except Exception:
                    st.error(
                        "Login failed. Check your email and password."
                    )

    with signup_tab:
        st.subheader("Create a new account")

        with st.form("signup_form"):
            new_email = st.text_input(
                "Email Address",
                key="signup_email"
            )

            new_password = st.text_input(
                "Create Password",
                type="password",
                key="signup_password"
            )

            signup_button = st.form_submit_button(
                "Create Account",
                use_container_width=True
            )

        if signup_button:
            if not new_email.strip() or not new_password:
                st.warning("Enter email and password.")

            elif len(new_password) < 12:
                st.warning(
                    "Use a password with at least 12 characters."
                )

            else:
                try:
                    result = supabase.auth.sign_up({
                        "email": new_email,
                        "password": new_password
                    })

                    if result.session:
                        st.session_state.logged_in = True
                        st.session_state.access_token = (
                            result.session.access_token
                        )
                        st.session_state.refresh_token = (
                            result.session.refresh_token
                        )
                        st.session_state.user_id = result.user.id

                        st.success("Account created!")
                        st.rerun()

                    else:
                        st.success(
                            "Account created. Check your email "
                            "for confirmation before logging in."
                        )

                except Exception as e:
                    st.error(f"Signup failed: {e}")


# AUTHENTICATION CHECK
if not st.session_state.logged_in:
    authentication_page()
    st.stop()


# RESTORE USER SESSION
try:
    supabase.auth.set_session(
        st.session_state.access_token,
        st.session_state.refresh_token
    )

except Exception:
    st.session_state.logged_in = False
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user_id = None
    st.rerun()


# GEMINI CONNECTION
client = genai.Client(
    api_key=st.secrets["GEMINI_API_KEY"]
)


# DOCUMENT READER
def read_document(file):
    pages = []

    if file.name.lower().endswith(".pdf"):
        pdf = PdfReader(file)

        for i, page in enumerate(pdf.pages):
            pages.append({
                "text": page.extract_text() or "",
                "page": i + 1
            })

    elif file.name.lower().endswith(".txt"):
        text = file.read().decode(
            "utf-8", errors="ignore"
        )

        pages.append({
            "text": text,
            "page": 1
        })

    elif file.name.lower().endswith(".docx"):
        doc = Document(file)

        text = "\n".join(
            p.text for p in doc.paragraphs
        )

        pages.append({
            "text": text,
            "page": 1
        })

    return pages


# GEMINI AI
def ask_gemini(question, pages, language):
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
{document_text[:100000]}

QUESTION:
{question}
"""

    delays = [2, 5, 10]

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )

            if not response.text:
                return "AI did not return an answer."

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
                    "Gemini server is busy. Try again later."
                )

            raise


# SAVE CHAT TO SUPABASE
def save_chat(question, answer):
    supabase.table("chat_history").insert({
        "user_id": str(st.session_state.user_id),
        "question": question,
        "answer": answer
    }).execute()


# LOAD PERMANENT CHAT HISTORY
def load_chat_history():
    result = (
        supabase.table("chat_history")
        .select("question, answer, created_at")
        .eq("user_id", str(st.session_state.user_id))
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )

    return result.data or []


# SIDEBAR
with st.sidebar:
    st.success("Logged in")

    st.write("IntelliAssist AI")

    if st.button("Logout"):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass

        for key in [
            "logged_in",
            "access_token",
            "refresh_token",
            "user_id"
        ]:
            st.session_state[key] = (
                False if key == "logged_in" else None
            )

        st.session_state.chat_history = []
        st.session_state.pages = []

        st.rerun()


# MAIN APP
st.title("🤖 IntelliAssist AI")
st.write("Smart Document AI Assistant")

# LANGUAGE
language = st.selectbox(
    "Choose Answer Language",
    ["Auto", "Hindi", "English"]
)


# UPLOAD DOCUMENT
st.subheader("📄 Upload Your Document")

uploaded_file = st.file_uploader(
    "Upload PDF, TXT or DOCX",
    type=["pdf", "txt", "docx"]
)

if uploaded_file:
    try:
        st.session_state.pages = read_document(
            uploaded_file
        )

        st.success("Document uploaded successfully!")

    except Exception as e:
        st.error(f"Document error: {e}")


if st.session_state.pages:

    # ASK QUESTION
    st.divider()
    st.subheader("💬 Ask Your Document")

    question = st.text_area(
        "Enter your question",
        placeholder="Ask anything about your document..."
    )

    if st.button("🤖 Get Answer"):
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

                try:
                    save_chat(question, answer)

                    st.success(
                        "Chat saved permanently!"
                    )

                except Exception as e:
                    st.error(
                        f"Answer generated, but saving failed: {e}"
                    )

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


    # DOCUMENT SEARCH
    st.divider()
    st.subheader("🔎 Relevant Information")

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

                st.write(
                    full_text[index:index + 1000]
                )

            else:
                st.info("No matching information found.")


    # SUMMARY
    st.divider()
    st.subheader("📝 Summarize Document")

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


    # SENTIMENT
    st.divider()
    st.subheader("😊 Sentiment Analysis")

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


    # INTENT
    st.divider()
    st.subheader("🎯 Intent Analysis")

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


    # SOURCE CITATIONS
    st.divider()
    st.subheader("📚 Source Citations")

    st.write(
        "AI answers are instructed to mention source page numbers."
    )


# PERMANENT CHAT HISTORY
st.divider()
st.subheader("💬 Permanent Chat History")

if st.button("Refresh Chat History"):
    try:
        history = load_chat_history()

        st.session_state.chat_history = history

        st.success("Chat history loaded!")

    except Exception as e:
        st.error(f"History error: {e}")


# SHOW SAVED CHATS
try:
    permanent_history = load_chat_history()

    if permanent_history:
        history_text = ""

        for item in permanent_history:
            with st.expander(item["question"]):
                st.write(item["answer"])

                if item.get("created_at"):
                    st.caption(
                        "Saved: " + str(item["created_at"])
                    )

            history_text += (
                "Question: " + item["question"] + "\n"
                "Answer: " + item["answer"] + "\n"
                "Date: " + str(item.get("created_at", "")) + "\n\n"
                "-----------------------------\n\n"
            )

        st.download_button(
            label="📥 Download Chat History",
            data=history_text,
            file_name="IntelliAssist_Chat_History.txt",
            mime="text/plain"
        )

    else:
        st.info("No saved chat history yet.")

except Exception as e:
    st.error(f"Could not load chat history: {e}")


if not st.session_state.pages:
    st.info(
        "Please upload a PDF, TXT or DOCX file to begin."
    )
