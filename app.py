import streamlit as st
import time
import hashlib
import numpy as np
import faiss

from google import genai
from supabase import create_client
from pypdf import PdfReader
from docx import Document
from io import BytesIO

from streamlit_cookies_manager import EncryptedCookieManager
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter


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

    cookies = EncryptedCookieManager(
        prefix="IntelliAssist/",
        password=st.secrets["COOKIES_PASSWORD"]
    )

except Exception as error:
    st.error(f"Connection error: {error}")
    st.stop()


if not cookies.ready():
    st.stop()


MODEL = "gemini-3.5-flash-lite"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# LOAD EMBEDDING MODEL
@st.cache_resource
def load_embedding_model():
    return SentenceTransformer(EMBEDDING_MODEL)


# SESSION STATE
defaults = {
    "access_token": None,
    "refresh_token": None,
    "user_id": None,
    "logged_in": False,
    "document_text": "",
    "pages": [],
    "chat_history": [],
    "faiss_index": None,
    "document_chunks": [],
    "document_hash": None,
    "last_sources": []
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


# RESTORE LOGIN
if not st.session_state.access_token:
    saved_refresh_token = cookies.get("refresh_token")

    if saved_refresh_token:
        try:
            result = supabase.auth.refresh_session(
                saved_refresh_token
            )

            if result.session and result.user:
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

                cookies["refresh_token"] = (
                    result.session.refresh_token
                )
                cookies.save()

        except Exception:
            cookies["refresh_token"] = ""
            cookies.save()
            clear_login()


# RESTORE ACTIVE SESSION
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

                cookies["refresh_token"] = (
                    result.session.refresh_token
                )
                cookies.save()

                st.success("Login successful!")
                st.rerun()

            except Exception:
                st.error("Email ya password check karein.")


if not st.session_state.logged_in:
    login()
    st.stop()


# DOCUMENT READER
def read_document(file_bytes, filename):
    text = ""
    pages = []

    filename = filename.lower()

    if filename.endswith(".pdf"):
        reader = PdfReader(BytesIO(file_bytes))

        for number, page in enumerate(reader.pages, 1):
            content = page.extract_text() or ""

            pages.append({
                "page": number,
                "text": content
            })

            text += f"\n[PAGE {number}]\n{content}"

    elif filename.endswith(".txt"):
        text = file_bytes.decode(
            "utf-8",
            errors="ignore"
        )

        pages.append({
            "page": 1,
            "text": text
        })

    elif filename.endswith(".docx"):
        doc = Document(BytesIO(file_bytes))

        text = "\n".join(
            paragraph.text
            for paragraph in doc.paragraphs
        )

        pages.append({
            "page": 1,
            "text": text
        })

    return text, pages


# BUILD RAG VECTOR DATABASE
def build_vector_database(pages):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150
    )

    chunks = []

    for page in pages:
        page_chunks = splitter.split_text(
            page["text"]
        )

        for chunk in page_chunks:
            if chunk.strip():
                chunks.append({
                    "text": chunk,
                    "page": page["page"]
                })

    if not chunks:
        raise ValueError(
            "No readable text found for creating embeddings."
        )

    model = load_embedding_model()

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32
    )

    index = faiss.IndexFlatIP(
        embeddings.shape[1]
    )

    index.add(embeddings)

    return index, chunks


# SEMANTIC SEARCH
def search_document(question, top_k=5):
    model = load_embedding_model()

    query_embedding = model.encode(
        [question],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype=np.float32
    )

    index = st.session_state.faiss_index
    chunks = st.session_state.document_chunks

    count = min(top_k, len(chunks))

    scores, indices = index.search(
        query_embedding,
        count
    )

    results = []

    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0:
            item = chunks[idx].copy()
            item["score"] = float(score)
            results.append(item)

    return results


# GEMINI RAG ANSWER
def ask_gemini(question, context, language):
    if language == "Hindi":
        instruction = "Answer completely in simple Hindi."

    elif language == "English":
        instruction = "Answer completely in clear English."

    else:
        instruction = (
            "Answer in the same language used in the user's question."
        )

    prompt = f"""
You are IntelliAssist AI, a RAG-based document assistant.

Use ONLY the retrieved document context below.

Rules:
1. Answer using the provided context.
2. Do not invent information.
3. Explain in simple language.
4. Give examples when useful.
5. Explain step by step when needed.
6. Mention source page numbers using [Page X].
7. If information is not present, clearly say it was not found.
8. Do not make up page numbers.

LANGUAGE:
{instruction}

RETRIEVED DOCUMENT CONTEXT:
{context}

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

            return "AI did not return an answer."

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

        cookies["refresh_token"] = ""
        cookies.save()

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
    file_bytes = uploaded_file.getvalue()

    current_hash = hashlib.sha256(
        file_bytes
    ).hexdigest()

    if current_hash != st.session_state.document_hash:
        try:
            with st.spinner(
                "Reading document and creating embeddings..."
            ):
                text, pages = read_document(
                    file_bytes,
                    uploaded_file.name
                )

                if not text.strip():
                    st.warning(
                        "No readable text found in this document."
                    )

                else:
                    index, chunks = build_vector_database(
                        pages
                    )

                    st.session_state.document_text = text
                    st.session_state.pages = pages
                    st.session_state.faiss_index = index
                    st.session_state.document_chunks = chunks
                    st.session_state.document_hash = current_hash

                    st.success(
                        "Document uploaded and FAISS database created!"
                    )

        except Exception as error:
            st.error(
                f"Document processing error: {error}"
            )


# ASK QUESTION USING RAG
st.divider()
st.subheader("💬 Ask a Question")

question = st.text_area(
    "Write your question here",
    placeholder="Ask anything about your document..."
)

if st.button("🤖 Get Answer"):
    if st.session_state.faiss_index is None:
        st.warning("Please upload a document first.")

    elif not question.strip():
        st.warning("Please enter your question.")

    else:
        try:
            with st.spinner(
                "Searching document and generating answer..."
            ):
                results = search_document(question)

                context_parts = []

                source_pages = sorted(
                    set(
                        item["page"]
                        for item in results
                    )
                )

                for item in results:
                    context_parts.append(
                        f"[Page {item['page']}]\n{item['text']}"
                    )

                context = "\n\n".join(
                    context_parts
                )

                answer = ask_gemini(
                    question,
                    context,
                    language
                )

            st.session_state.last_sources = source_pages

            save_chat(question, answer)

            st.session_state.chat_history.append({
                "question": question,
                "answer": answer
            })

            st.subheader("Answer")
            st.write(answer)

            st.subheader("📚 Source Citations")

            if source_pages:
                for page in source_pages:
                    st.write(f"📄 Document Page: {page}")
            else:
                st.info("No source page found.")

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


# SEMANTIC SEARCH
st.divider()
st.subheader("🔍 Semantic Search")

semantic_query = st.text_input(
    "Enter what you want to find in the document"
)

if st.button("Search Document"):
    if st.session_state.faiss_index is None:
        st.warning("Upload a document first.")

    elif not semantic_query.strip():
        st.warning("Enter a search query.")

    else:
        try:
            results = search_document(
                semantic_query,
                top_k=5
            )

            if results:
                st.success("Relevant information found!")

                for item in results:
                    with st.expander(
                        f"📄 Page {item['page']}"
                    ):
                        st.write(item["text"])

            else:
                st.info("No relevant information found.")

        except Exception as error:
            st.error(f"Search error: {error}")


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
