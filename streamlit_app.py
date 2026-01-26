# streamlit_app.py
from __future__ import annotations

import os
import streamlit as st

from app.ingestion import init_resources
from app.search_tools import SearchTool
from app.search_agent import rag_answer

# -----------------------------
# Config
# -----------------------------
REPO_OWNER = "basecamp"
REPO_NAME = "handbook"
BRANCH = None

BASE_REPO_URL = "https://github.com/basecamp/handbook/blob/master/"
MODEL_NAME = "llama-3.1-8b-instant"

DEFAULT_TOP_K = 2
DEFAULT_MAX_CHARS = 1200

SUGGESTED_QUESTIONS = [
    "What is Basecamp's vacation policy?",
    "How does parental leave work?",
    "Are employees allowed to work remotely?",
]


# -----------------------------
# Helpers
# -----------------------------
def split_answer_and_sources(answer: str) -> tuple[str, str | None]:
    """
    Many RAG demos append a 'Sources:' section at the end.
    This helper splits it for nicer UI presentation.
    """
    if not answer:
        return "", None
    if "Sources:" not in answer:
        return answer, None
    main, sources = answer.split("Sources:", 1)
    main = main.strip()
    sources = ("Sources:\n" + sources.strip()).strip()
    return main, sources


@st.cache_resource
def init_rag(top_k: int, max_chars: int) -> SearchTool:
    """
    Cache heavy work: downloading repo, building chunks, embeddings and vector index.
    The cache key depends on (top_k, max_chars) so changing settings rebuilds the tool.
    """
    resources = init_resources(REPO_OWNER, REPO_NAME, branch=BRANCH)
    tool = SearchTool(
        resources=resources,
        base_repo_url=BASE_REPO_URL,
        top_k=top_k,
        max_chars=max_chars,
    )
    return tool


def ensure_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = ""


def push_user_message(text: str):
    st.session_state.messages.append({"role": "user", "content": text})


def push_assistant_message(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})


# -----------------------------
# UI
# -----------------------------
st.set_page_config(
    page_title="Basecamp Handbook AI Assistant",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

ensure_session_state()

st.title("🤖 Basecamp Handbook AI Assistant")
st.caption(
    "Ask questions and get answers grounded in the Basecamp handbook. "
    "If the handbook doesn't cover something, the assistant will say so."
)

# Sidebar controls
with st.sidebar:
    st.markdown("### Settings")
    top_k = st.slider("Top-K search results", min_value=1, max_value=8, value=DEFAULT_TOP_K)
    max_chars = st.slider("Max chars per source", min_value=400, max_value=3000, value=DEFAULT_MAX_CHARS, step=100)

    st.markdown("---")
    st.markdown("### Quick actions")

    if st.button("🧹 Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_prompt = ""
        st.rerun()

    st.markdown("---")
    st.markdown("### Status")
    if os.environ.get("GROQ_API_KEY"):
        st.success("GROQ_API_KEY detected")
    else:
        st.warning("GROQ_API_KEY not found (set it in your terminal)")

# Init tool (cached)
tool = init_rag(top_k=top_k, max_chars=max_chars)

# Suggested questions (buttons)
st.markdown("**Try asking:**")
cols = st.columns(len(SUGGESTED_QUESTIONS))
for i, q in enumerate(SUGGESTED_QUESTIONS):
    if cols[i].button(q, use_container_width=True):
        st.session_state.pending_prompt = q
        st.rerun()

st.markdown("---")

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # For assistant messages, render Sources folded if present
        if msg["role"] == "assistant":
            main, sources = split_answer_and_sources(msg["content"])
            st.markdown(main)
            if sources:
                with st.expander("Sources"):
                    st.markdown(sources)
        else:
            st.markdown(msg["content"])

# Chat input (supports "pending_prompt" from buttons)
prompt_from_button = st.session_state.pending_prompt.strip()
user_input = st.chat_input("Ask your question...")

prompt = ""
if prompt_from_button:
    prompt = prompt_from_button
    st.session_state.pending_prompt = ""  # consume it
elif user_input:
    prompt = user_input.strip()

if prompt:
    # user
    push_user_message(prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    # assistant
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = rag_answer(prompt, tool, model=MODEL_NAME)

        main, sources = split_answer_and_sources(answer)
        st.markdown(main)
        if sources:
            with st.expander("Sources"):
                st.markdown(sources)

    push_assistant_message(answer)
