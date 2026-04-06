# app.py

"""
PDF / Document Q&A Tool - RAG-style GenAI Prototype

Features:
- Upload PDF
- Extract + chunk text
- Embed chunks locally using Sentence Transformers
- Retrieve relevant chunks using FAISS
- Ask questions in chat style
- Answer with Groq API
- Compare prompt strategies
- Show source chunks for transparency
"""

import os
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from utils.pdf_processor import process_pdf
from utils.retriever import DocumentRetriever
from utils.prompt_engine import (
    format_context,
    get_prompt,
    get_available_prompt_types
)

# ---------------------------------------------------
# App Configuration
# ---------------------------------------------------
st.set_page_config(
    page_title="PDF Q&A Tool - RAG Prototype",
    page_icon="📄",
    layout="wide"
)

load_dotenv()

# ---------------------------------------------------
# Session State Initialization
# ---------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "retriever" not in st.session_state:
    st.session_state.retriever = None

if "chunks" not in st.session_state:
    st.session_state.chunks = []

if "document_loaded" not in st.session_state:
    st.session_state.document_loaded = False

if "last_question" not in st.session_state:
    st.session_state.last_question = ""

if "last_sources" not in st.session_state:
    st.session_state.last_sources = []

if "last_answer" not in st.session_state:
    st.session_state.last_answer = ""


# ---------------------------------------------------
# Helper Functions
# ---------------------------------------------------
def get_groq_client(api_key: str):
    """
    Create Groq client.
    """
    return Groq(api_key=api_key)


def get_groq_response(prompt: str, api_key: str, model_name: str, temperature: float):
    """
    Call Groq API and return text response.
    Handles common API errors cleanly.
    """
    try:
        client = get_groq_client(api_key)

        response = client.chat.completions.create(
            model=model_name,
            temperature=temperature,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise, grounded document question-answering assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        error_text = str(e).lower()

        if "rate limit" in error_text or "429" in error_text:
            return (
                "⚠️ Groq API rate limit reached.\n\n"
                "Possible fixes:\n"
                "- Wait a minute and retry\n"
                "- Use another Groq API key\n"
                "- Try a smaller/faster model"
            )

        elif "api key" in error_text or "authentication" in error_text or "401" in error_text:
            return (
                "⚠️ Invalid or missing Groq API key.\n\n"
                "Please check your `.env` file or sidebar API key input."
            )

        elif "model" in error_text or "not found" in error_text:
            return (
                f"⚠️ Selected Groq model `{model_name}` is not available.\n\n"
                "Please choose another model from the sidebar."
            )

        else:
            return f"⚠️ Groq API Error: {str(e)}"


@st.cache_resource(show_spinner=False)
def load_retriever_model():
    """
    Cache the retriever model so it loads only once.
    """
    return DocumentRetriever(model_name="all-MiniLM-L6-v2")


def process_uploaded_pdf(uploaded_file):
    """
    Process PDF, chunk it, and build retrieval index.
    """
    with st.spinner("Processing PDF and building retrieval index..."):
        chunks = process_pdf(uploaded_file)

        retriever = load_retriever_model()
        retriever.build_index(chunks)

        st.session_state.chunks = chunks
        st.session_state.retriever = retriever
        st.session_state.document_loaded = True


def answer_question(question, prompt_type, api_key, model_name, temperature, top_k):
    """
    Full RAG pipeline:
    1. Retrieve relevant chunks
    2. Build prompt
    3. Call Groq
    """
    retriever = st.session_state.retriever

    retrieved = retriever.retrieve(question, top_k=top_k)
    context = format_context(retrieved)
    final_prompt = get_prompt(question, context, "grounded_fewshot")
    answer = get_groq_response(final_prompt, api_key, model_name, temperature)

    return answer, retrieved, final_prompt


def compare_all_prompts(question, api_key, model_name, temperature, top_k):
    """
    Run all prompt versions for comparison.
    """
    results = {}
    retriever = st.session_state.retriever
    retrieved = retriever.retrieve(question, top_k=top_k)
    context = format_context(retrieved)

    for prompt_type in ["basic", "cot", "grounded_fewshot"]:
        prompt = get_prompt(question, context, prompt_type)
        answer = get_groq_response(prompt, api_key, model_name, temperature)
        results[prompt_type] = answer

    return results, retrieved


# ---------------------------------------------------
# Sidebar
# ---------------------------------------------------
st.sidebar.title("⚙️ Settings")

default_api_key = os.getenv("GROQ_API_KEY", "")
if not default_api_key:
    try:
        default_api_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        default_api_key = ""

api_key = default_api_key

model_name = st.sidebar.selectbox(
    "Groq Model",
    options=[
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768"
    ],
    index=1
)

temperature = st.sidebar.slider(
    "Temperature (lower = more factual)",
    min_value=0.0,
    max_value=1.0,
    value=0.2,
    step=0.05
)

top_k = st.sidebar.slider(
    "Top Chunks to Retrieve",
    min_value=2,
    max_value=8,
    value=4,
    step=1
)

prompt_options = get_available_prompt_types()
selected_prompt_type = st.sidebar.selectbox(
    "Prompt Strategy",
    options=list(prompt_options.keys()),
    format_func=lambda x: prompt_options[x]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Upload PDF")

uploaded_file = st.sidebar.file_uploader(
    "Choose a PDF file",
    type=["pdf"]
)

if uploaded_file is not None:
    if st.sidebar.button("Process PDF"):
        try:
            process_uploaded_pdf(uploaded_file)
            st.sidebar.success("PDF processed successfully!")
        except Exception as e:
            st.sidebar.error(f"Error processing PDF: {e}")

# ---------------------------------------------------
# Main UI
# ---------------------------------------------------
st.title("📄 PDF / Document Q&A Tool")
st.caption("RAG-style GenAI prototype using Streamlit, FAISS, local embeddings, and Groq LLMs")

if not api_key:
    st.error("API key is not found. Please configure it in `.env` (local) or Streamlit Secrets (deployment).")

if not st.session_state.document_loaded:
    st.info("Upload and process a PDF from the sidebar to start asking questions.")
else:
    st.success("Document ready. Ask your questions below.")

# ---------------------------------------------------
# Chat History Display
# ---------------------------------------------------
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant" and "sources" in msg:
            with st.expander("🔎 View Retrieved Source Chunks"):
                for i, (chunk, score, idx, page_num) in enumerate(msg["sources"], start=1):
                    st.markdown(
                        f"**Source {i}** | **Page:** `{page_num}` | Chunk ID: `{idx}` | Similarity: `{score:.4f}`"
                    )
                    st.code(chunk, language="text")

        if msg["role"] == "assistant" and "feedback_key" in msg:
            col1, col2 = st.columns(2)
            with col1:
                st.button("👍 Helpful", key=f"up_{msg['feedback_key']}")
            with col2:
                st.button("👎 Not Helpful", key=f"down_{msg['feedback_key']}")

# ---------------------------------------------------
# Chat Input
# ---------------------------------------------------
question = st.chat_input("Ask a question about the uploaded PDF...")

if question and st.session_state.document_loaded and api_key:
    st.session_state.chat_history.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer, retrieved_sources, used_prompt = answer_question(
                    question=question,
                    prompt_type=selected_prompt_type,
                    api_key=api_key,
                    model_name=model_name,
                    temperature=temperature,
                    top_k=top_k
                )

                st.markdown(answer)

                with st.expander("🔎 View Retrieved Source Chunks"):
                    for i, (chunk, score, idx, page_num) in enumerate(retrieved_sources, start=1):   
                        st.markdown(
                            f"**Source {i}** | **Page:** `{page_num}` | Chunk ID: `{idx}` | Similarity: `{score:.4f}`"
                    )
                    st.code(chunk, language="text")

                with st.expander("🧠 View Prompt Used"):
                    st.code(used_prompt, language="text")

                col1, col2 = st.columns(2)
                with col1:
                    st.button("👍 Helpful", key=f"live_up_{len(st.session_state.chat_history)}")
                with col2:
                    st.button("👎 Not Helpful", key=f"live_down_{len(st.session_state.chat_history)}")

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": retrieved_sources,
                    "feedback_key": len(st.session_state.chat_history)
                })

                st.session_state.last_question = question
                st.session_state.last_sources = retrieved_sources
                st.session_state.last_answer = answer

            except Exception as e:
                st.error(f"Error generating answer: {e}")

# ---------------------------------------------------
# Extra Actions
# ---------------------------------------------------
if st.session_state.document_loaded and api_key and st.session_state.last_question:
    st.markdown("---")
    st.subheader("🛠 Extra Controls")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔁 Regenerate with Better Prompt"):
            with st.spinner("Regenerating using strongest prompt..."):
                try:
                    better_answer, retrieved_sources, used_prompt = answer_question(
                        question=st.session_state.last_question,
                        prompt_type="grounded_fewshot",
                        api_key=api_key,
                        model_name=model_name,
                        temperature=temperature,
                        top_k=top_k
                    )

                    st.markdown("### Regenerated Answer")
                    st.write(better_answer)

                    with st.expander("🔎 Retrieved Source Chunks"):
                        for i, (chunk, score, idx, page_num) in enumerate(retrieved_sources, start=1):
                            st.markdown(
                                f"**Source {i}** | **Page:** `{page_num}` | Chunk ID: `{idx}` | Similarity: `{score:.4f}`"
                         )
                            st.code(chunk, language="text")

                    with st.expander("🧠 Prompt Used"):
                        st.code(used_prompt, language="text")

                except Exception as e:
                    st.error(f"Error regenerating answer: {e}")

    with col2:
        if st.button("⚖️ Compare Prompt Versions"):
            with st.spinner("Comparing all prompt strategies..."):
                try:
                    comparison_results, retrieved_sources = compare_all_prompts(
                        question=st.session_state.last_question,
                        api_key=api_key,
                        model_name=model_name,
                        temperature=temperature,
                        top_k=top_k
                    )

                    st.markdown("### Prompt Comparison Results")

                    for prompt_type, answer in comparison_results.items():
                        st.markdown(f"#### {prompt_options[prompt_type]}")
                        st.write(answer)

                    with st.expander("🔎 Shared Retrieved Source Chunks"):
                        for i, (chunk, score, idx, page_num) in enumerate(retrieved_sources, start=1):
                            st.markdown(
                                f"**Source {i}** | **Page:** `{page_num}` | Chunk ID: `{idx}` | Similarity: `{score:.4f}`"
                            )
                            st.code(chunk, language="text")
                except Exception as e:
                    st.error(f"Error comparing prompts: {e}")