# app/eval/eval_runner.py
from __future__ import annotations

import json
import os
import re

from openai import OpenAI

from app.eval.eval_prompt import EVALUATION_PROMPT
from app.eval.eval_schema import EvaluationChecklist


USER_PROMPT_FORMAT = """
<INSTRUCTIONS>{instructions}</INSTRUCTIONS>
<QUESTION>{question}</QUESTION>
<CONTEXT>{context}</CONTEXT>
<ANSWER>{answer}</ANSWER>
""".strip()

EVAL_MODEL = "llama-3.1-8b-instant"


def _extract_json(text: str) -> dict:
    if not text:
        raise ValueError("Empty model output; cannot extract JSON.")

    try:
        return json.loads(text)
    except Exception:
        pass

    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
    if fenced:
        return json.loads(fenced.group(1))

    brace = re.search(r"(\{.*\})", text, flags=re.S)
    if brace:
        return json.loads(brace.group(1))

    raise ValueError(f"Could not extract JSON from model output:\n{text[:500]}")


def evaluate_log_record(log_record: dict) -> EvaluationChecklist:
    user_prompt = USER_PROMPT_FORMAT.format(
        instructions=log_record["system_prompt"],
        question=log_record["question"],
        context=log_record["context"],
        answer=log_record["answer"],
    )

    client = OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )

    resp = client.chat.completions.create(
        model=EVAL_MODEL,
        messages=[
            {"role": "system", "content": EVALUATION_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )

    data = _extract_json(resp.choices[0].message.content or "")
    return EvaluationChecklist.model_validate(data)
