# app/search_tools.py
from __future__ import annotations

from typing import List

from app.ingestion import VectorResources, handbook_search


class SearchTool:
    def __init__(self, resources: VectorResources, base_repo_url: str, top_k: int = 2, max_chars: int = 1200):
        self.resources = resources
        self.base_repo_url = base_repo_url.rstrip("/") + "/"
        self.top_k = top_k
        self.max_chars = max_chars

    def search(self, query: str) -> str:
        hits = handbook_search(self.resources, query, k=self.top_k)
        if not hits:
            return "NO_RESULTS"

        blocks: List[str] = []
        for h in hits:
            file_path = h.get("filename", "")
            title = h.get("chunk_title", "")
            text = (h.get("chunk_text") or "").strip()

            if len(text) > self.max_chars:
                text = text[: self.max_chars] + "\n...[TRUNCATED]..."

            blocks.append(
                f"FILE: {file_path}\n"
                f"TITLE: {title}\n"
                f"LINK: {self.base_repo_url}{file_path}\n"
                f"CONTENT:\n{text}"
            )

        return "\n\n---\n\n".join(blocks)
