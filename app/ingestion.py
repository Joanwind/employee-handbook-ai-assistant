# app/ingestion.py
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import frontmatter
import numpy as np
import requests
from minsearch import VectorSearch
from sentence_transformers import SentenceTransformer


MD_EXTS = (".md", ".mdx")


def read_repo_data(repo_owner: str, repo_name: str, branch: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Download a GitHub repo as zip and parse .md/.mdx files with frontmatter.
    Returns list of dicts, including:
      - filename: path inside zip
      - content: markdown body (without frontmatter)
      - any frontmatter fields
    """
    prefix = "https://codeload.github.com"
    branches = [branch] if branch else ["main", "master"]

    resp: Optional[requests.Response] = None
    for b in branches:
        url = f"{prefix}/{repo_owner}/{repo_name}/zip/refs/heads/{b}"
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            resp = r
            break

    if resp is None:
        raise RuntimeError(f"Failed to download repository: {repo_owner}/{repo_name}")

    docs: List[Dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for file in zf.infolist():
            if not file.filename.lower().endswith(MD_EXTS):
                continue

            raw = zf.read(file).decode("utf-8", errors="ignore")
            post = frontmatter.loads(raw)
            data = post.to_dict()
            data["filename"] = file.filename
            data["content"] = post.content
            docs.append(data)

    return docs


def split_markdown(text: str, level: int = 2) -> List[Dict[str, str]]:
    """
    Split markdown by header level (default: ##).
    Returns list of {title, content}.
    """
    header_re = re.compile(rf"^(#{{{level}}})\s+(.+)$", re.MULTILINE)
    matches = list(header_re.finditer(text))
    if not matches:
        return [{"title": "DOCUMENT", "content": text.strip()}]

    sections: List[Dict[str, str]] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append(
            {
                "title": f"{m.group(1)} {m.group(2)}",
                "content": text[start:end].strip(),
            }
        )
    return sections


def build_chunks(docs: List[Dict[str, Any]], min_chars: int = 80, header_level: int = 2) -> List[Dict[str, Any]]:
    """
    Build chunk records from docs (non-destructive).
    """
    chunks: List[Dict[str, Any]] = []

    for doc in docs:
        content = (doc.get("content") or "").strip()
        if not content:
            continue

        sections = split_markdown(content, level=header_level)
        for idx, sec in enumerate(sections):
            text = f"{sec['title']}\n\n{sec['content']}".strip()
            if len(text) < min_chars:
                continue

            chunk = {
                **{k: v for k, v in doc.items() if k != "content"},
                "chunk_index": idx,
                "chunk_title": sec["title"],
                "chunk_text": text,
            }
            chunks.append(chunk)

    return chunks


@dataclass
class VectorResources:
    embedding_model: SentenceTransformer
    index: VectorSearch


def build_vector_index(chunks: List[Dict[str, Any]], model_name: str = "multi-qa-distilbert-cos-v1") -> VectorResources:
    embedding_model = SentenceTransformer(model_name)
    vectors = np.array([embedding_model.encode(c["chunk_text"]) for c in chunks])

    index = VectorSearch()
    index.fit(vectors, chunks)

    return VectorResources(embedding_model=embedding_model, index=index)


def handbook_search(resources: VectorResources, query: str, k: int = 5) -> List[Dict[str, Any]]:
    q_vec = resources.embedding_model.encode(query)
    return resources.index.search(q_vec, num_results=k)


def init_resources(
    repo_owner: str,
    repo_name: str,
    branch: Optional[str] = None,
    min_chars: int = 80,
    header_level: int = 2,
    embedding_model_name: str = "multi-qa-distilbert-cos-v1",
) -> VectorResources:
    docs = read_repo_data(repo_owner, repo_name, branch=branch)
    chunks = build_chunks(docs, min_chars=min_chars, header_level=header_level)
    return build_vector_index(chunks, model_name=embedding_model_name)
