# app/main.py
from __future__ import annotations

from app.ingestion import init_resources
from app.search_tools import SearchTool
from app.search_agent import rag_answer
from app.logs import log_record_to_file

REPO_OWNER = "Joanwind"
REPO_NAME = "synthetic-employee-handbook"
BRANCH = None

BASE_REPO_URL = "https://github.com/Joanwind/synthetic-employee-handbook/blob/main/"


def main():
    print(f"Indexing repo: {REPO_OWNER}/{REPO_NAME} ...")
    resources = init_resources(REPO_OWNER, REPO_NAME, branch=BRANCH)

    tool = SearchTool(resources=resources, base_repo_url=BASE_REPO_URL, top_k=2, max_chars=1200)

    print("\nReady. Type 'stop' to exit.\n")
    while True:
        q = input("Your question: ").strip()
        if q.lower() == "stop":
            print("Goodbye!")
            break

        answer = rag_answer(q, tool)
        print("\nAnswer:\n", answer)
        print("\n" + "=" * 60 + "\n")

        log_record_to_file({"question": q, "answer": answer})


if __name__ == "__main__":
    main()
