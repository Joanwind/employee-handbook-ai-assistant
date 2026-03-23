# app/search_agent.py
from __future__ import annotations

import os
from openai import OpenAI

from app.search_tools import SearchTool


SYSTEM_PROMPT = """
You are an internal employee knowledge assistant.
Answer ONLY using the handbook content returned by the search tool.
If the tool returns NO_RESULTS, say you cannot confirm from the handbook.
When answering, always refer to the company as "our company".

Always include a Sources section with FILE and TITLE for each source you used.
""".strip()


def make_client() -> OpenAI:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing env var: GROQ_API_KEY")

    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )


def rag_answer(question: str, search_tool: SearchTool, model: str = "llama-3.1-8b-instant") -> str:
    client = make_client()
    context = search_tool.search(question)

    if context == "NO_RESULTS":
        return "I could not find this information in the handbook."

    prompt = f"""{SYSTEM_PROMPT}

Handbook content:
{context}

Question:
{question}

Answer:
"""
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""
