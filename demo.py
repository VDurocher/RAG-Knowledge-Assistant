#!/usr/bin/env python3
"""
RAG Knowledge Assistant — Demo Script
======================================
Runs 6 preset questions through the full RAG pipeline and prints
formatted answers with source citations.

Usage:
    python demo.py
    python demo.py --model gpt-4o          # override LLM model
    python demo.py --questions 1 3 5       # run specific questions only
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.config import settings
from core.indexer import load_or_build_index
from core.loader import load_documents
from core.rag import ask_stream, build_llm, build_retriever

# ─── Demo questions ────────────────────────────────────────────────────────────

DEMO_QUESTIONS: list[tuple[str, str]] = [
    (
        "Supplier Pricing",
        "Which supplier has the best price for the Jabra Evolve2 85 headset? "
        "Show all three prices and the savings.",
    ),
    (
        "Client Spend",
        "What was Metro Digital Agency's total spend in Q1 2026? "
        "Break it down by order.",
    ),
    (
        "Selling Price & Margin",
        "What is our selling price for the Dell XPS 15 i7 and what margin does it generate?",
    ),
    (
        "Profit per Unit",
        "Compare buying price vs selling price for the Logitech MX Master 3S. "
        "What is our profit per unit and margin percentage?",
    ),
    (
        "Employee Schedule",
        "Who works on Saturdays? List their names and roles.",
    ),
    (
        "Client Ranking",
        "Which client had the highest average order value in Q1 2026, "
        "and which was the most active by number of orders?",
    ),
]

# ─── Terminal formatting ───────────────────────────────────────────────────────

WIDTH = 72
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
DIM    = "\033[2m"
BLUE   = "\033[94m"


def _line(char: str = "─") -> str:
    return char * WIDTH


def _header() -> None:
    print()
    print(CYAN + "╔" + "═" * (WIDTH - 2) + "╗" + RESET)
    title = "NEXUS SUPPLY CO. — RAG KNOWLEDGE ASSISTANT"
    sub   = "Automated Demo — Powered by LangChain + FAISS"
    print(CYAN + "║" + RESET + title.center(WIDTH - 2) + CYAN + "║" + RESET)
    print(CYAN + "║" + RESET + sub.center(WIDTH - 2) + CYAN + "║" + RESET)
    print(CYAN + "╚" + "═" * (WIDTH - 2) + "╝" + RESET)
    print()


def _question_header(index: int, total: int, category: str, question: str) -> None:
    print(BOLD + BLUE + f"[{index}/{total}]  {category.upper()}" + RESET)
    print(DIM + _line() + RESET)
    print(BOLD + "Q: " + RESET + question)
    print()
    print(BOLD + "A: " + RESET, end="", flush=True)


def _sources(citations: list[tuple[str, int | None]]) -> None:
    if not citations:
        return
    print()
    print()
    parts = []
    for source, page in citations:
        parts.append(f"{source}" + (f" · p.{page}" if page is not None else ""))
    print(DIM + "  Sources: " + " | ".join(parts) + RESET)


def _separator() -> None:
    print(DIM + _line() + RESET)
    print()


def _footer(elapsed: float) -> None:
    print(GREEN + _line("═") + RESET)
    print(GREEN + f"  Demo complete — {len(DEMO_QUESTIONS)} questions in {elapsed:.1f}s" + RESET)
    print(GREEN + _line("═") + RESET)
    print()


# ─── Pipeline setup ────────────────────────────────────────────────────────────

def _setup() -> tuple:
    print(DIM + "Loading knowledge base…" + RESET, end=" ", flush=True)
    try:
        settings.validate()
    except ValueError as error:
        print(f"\n\033[91mConfiguration error: {error}\033[0m")
        sys.exit(1)

    documents = load_documents(settings.knowledge_base_path)
    vector_store = load_or_build_index(documents, settings)
    retriever = build_retriever(vector_store, k=settings.retrieval_k)
    llm = build_llm(settings)

    print(GREEN + f"OK ({len(documents)} chunks indexed)" + RESET)
    print()
    return retriever, llm


# ─── Main ──────────────────────────────────────────────────────────────────────

def run_demo(question_indices: list[int] | None = None) -> None:
    _header()
    retriever, llm = _setup()

    questions = (
        [(i, DEMO_QUESTIONS[i]) for i in question_indices]
        if question_indices
        else list(enumerate(DEMO_QUESTIONS))
    )

    t_start = time.time()

    for rank, (idx, (category, question)) in enumerate(questions, start=1):
        _question_header(rank, len(questions), category, question)

        stream, source_docs, is_fallback = ask_stream(
            question, retriever, llm, fallback_to_llm=False
        )

        # Affichage du stream token par token
        full_response = ""
        for token in stream:
            print(token, end="", flush=True)
            full_response += token

        # Citations
        seen: set[str] = set()
        citations: list[tuple[str, int | None]] = []
        for doc in source_docs:
            key = doc.metadata.get("source", "")
            if key not in seen:
                seen.add(key)
                page = doc.metadata.get("page")
                citations.append((key, page + 1 if page is not None else None))

        _sources(citations)
        print()
        _separator()

        # Pause entre questions pour lisibilité
        if rank < len(questions):
            time.sleep(0.5)

    _footer(time.time() - t_start)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Knowledge Assistant demo")
    parser.add_argument(
        "--questions",
        nargs="+",
        type=int,
        metavar="N",
        help="Run specific questions by index (0-based). Default: all.",
    )
    args = parser.parse_args()

    indices = args.questions if args.questions else None
    run_demo(question_indices=indices)
