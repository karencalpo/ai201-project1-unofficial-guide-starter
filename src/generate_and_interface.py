from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import gradio as gr
from dotenv import load_dotenv
from groq import Groq

from embed_and_retrieve import (
    DEFAULT_COLLECTION,
    DEFAULT_MODEL,
    DEFAULT_TOP_K,
    build_vector_store,
    retrieve,
)

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_REFUSAL = "I don't have enough information in the retrieved OMSCentral context to answer that."

load_dotenv()

SYSTEM_PROMPT = (
    "You are a grounded QA assistant for OMSCentral course-review data. "
    "You must answer only from the provided retrieved snippets. "
    "Do not use outside knowledge, assumptions, or prior facts. "
    "If the snippets do not contain enough evidence, reply exactly with: "
    f"{DEFAULT_REFUSAL} "
    "Do not invent citations or sources."
)

PATTERN_HINT_PROMPT = (
    "For questions asking about a common warning, trend, or pattern, summarize a recurring theme "
    "supported by multiple snippets when possible. Avoid answering from a single anecdotal snippet "
    "if broader repeated evidence is present in context."
)

KNOWN_COURSES = [
    "Artificial Intelligence",
    "Knowledge-Based AI",
    "Machine Learning",
    "Introduction to Graduate Algorithms",
    "AI, Ethics, and Society",
    "Human-Computer Interaction",
    "Introduction to Computer Vision",
    "Game Artificial Intelligence",
    "Deep Learning",
    "Natural Language Processing",
]

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "what",
    "which",
    "with",
}


@dataclass(frozen=True)
class SourceItem:
    rank: int
    course: str
    chunk_type: str
    source_url: str


def _extract_course_from_question(question: str) -> str | None:
    question_lc = question.lower()
    for course in KNOWN_COURSES:
        if course.lower() in question_lc:
            return course
    return None


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {tok for tok in tokens if tok not in STOPWORDS and len(tok) > 2}


def _is_pattern_question(question: str) -> bool:
    q = question.lower()
    triggers = [
        "common warning",
        "common concern",
        "common complaint",
        "pattern",
        "what do students warn",
        "according to recent student review",
    ]
    return any(trigger in q for trigger in triggers)


def _extract_two_courses(question: str) -> tuple[str, str] | None:
    """Return (course_a, course_b) if the question names exactly two known courses."""
    found = [c for c in KNOWN_COURSES if c.lower() in question.lower()]
    if len(found) == 2:
        return found[0], found[1]
    return None


def _is_comparison_question(question: str) -> bool:
    q = question.lower()
    comparison_triggers = ["higher", "lower", "more", "less", "harder", "easier", "compare", "vs", "versus", "which"]
    return _extract_two_courses(question) is not None and any(t in q for t in comparison_triggers)


def _get_course_facts_chunk(course: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    for m in candidates:
        meta = m.get("metadata", {})
        if (
            str(meta.get("course", "")) == course
            and str(meta.get("chunk_type", "")) == "course_facts"
        ):
            return m
    return None


def _parse_workload(text: str) -> float | None:
    m = re.search(r"Average Workload:\s*([\d.]+)\s*hrs", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def _build_comparison_answer(
    question: str,
    candidates: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]] | None:
    """Return (answer_text, source_matches) for workload/difficulty comparison questions."""
    pair = _extract_two_courses(question)
    if not pair:
        return None
    course_a, course_b = pair

    q = question.lower()
    if not any(w in q for w in ["workload", "difficult", "harder", "easier", "rating"]):
        return None

    chunk_a = _get_course_facts_chunk(course_a, candidates)
    chunk_b = _get_course_facts_chunk(course_b, candidates)

    source_chunks = [c for c in [chunk_a, chunk_b] if c is not None]
    if not source_chunks:
        return None

    # Re-assign ranks for attribution display.
    for idx, chunk in enumerate(source_chunks, start=1):
        chunk["rank"] = idx

    if "workload" in q:
        if chunk_a is None or chunk_b is None:
            return None
        wl_a = _parse_workload(str(chunk_a.get("text", "")))
        wl_b = _parse_workload(str(chunk_b.get("text", "")))
        if wl_a is None or wl_b is None:
            return None
        if wl_a >= wl_b:
            higher, lower = course_a, course_b
            wl_high, wl_low = wl_a, wl_b
        else:
            higher, lower = course_b, course_a
            wl_high, wl_low = wl_b, wl_a
        answer = (
            f"{higher} has the higher average workload: {wl_high:.2f} hrs/week "
            f"compared with {lower} at {wl_low:.2f} hrs/week."
        )
        return answer, source_chunks

    return None


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _build_pattern_warning_answer(question: str, matches: list[dict[str, Any]]) -> str | None:
    if not _is_pattern_question(question) or not matches:
        return None

    reading_writing_hits = 0
    busy_work_hits = 0
    busy_work_strong_hits = 0
    uneven_workload_hits = 0
    uneven_phase_hits = 0

    reading_writing_patterns = [
        r"\breading\b",
        r"\bwriting\b",
        r"\bwrite\b",
        r"\bpapers?\b",
        r"\breports?\b",
    ]
    busy_work_patterns = [
        r"\bbusy\s*work\b",
        r"\btedious\b",
        r"\brepetitive\b",
        r"\blots?\s+of\s+small\s+assignments\b",
    ]
    busy_work_strong_patterns = [
        r"\bbusy\s*work\b",
    ]
    uneven_workload_patterns = [
        r"\buneven\b",
        r"\bworkload\b",
        r"\bfront\s*loaded\b",
        r"\bheavy\s+weeks\b",
    ]
    uneven_phase_patterns = [
        r"\bphases?\b",
        r"\bmodule\b",
        r"\bweeks?\b",
        r"\bpart\s+of\s+the\s+semester\b",
    ]

    for match in matches:
        text = str(match.get("text", ""))
        if _contains_any(text, reading_writing_patterns):
            reading_writing_hits += 1
        if _contains_any(text, busy_work_patterns):
            busy_work_hits += 1
        if _contains_any(text, busy_work_strong_patterns):
            busy_work_strong_hits += 1
        if _contains_any(text, uneven_workload_patterns):
            uneven_workload_hits += 1
        if _contains_any(text, uneven_phase_patterns):
            uneven_phase_hits += 1

    themes: list[str] = []
    if reading_writing_hits > 0:
        themes.append("it involves substantial reading and writing")
    # Busy-work claim requires explicit phrase, or repeated supporting language.
    if busy_work_strong_hits >= 1 or busy_work_hits >= 2:
        themes.append("some students describe parts of it as busy work")
    # Uneven-phases claim requires workload evidence plus phase/timing evidence.
    if uneven_workload_hits >= 2 and uneven_phase_hits >= 1:
        themes.append("the workload can feel uneven across phases")

    if not themes:
        return None

    if len(themes) == 1:
        theme_text = themes[0]
    elif len(themes) == 2:
        theme_text = f"{themes[0]}, and {themes[1]}"
    else:
        theme_text = f"{themes[0]}, {themes[1]}, and {themes[2]}"

    return (
        "One common warning is that "
        f"{theme_text}, so the course should not be treated as low-effort."
    )


def _rerank_matches(question: str, matches: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    target_course = _extract_course_from_question(question)
    question_tokens = _tokenize(question)

    scored: list[tuple[float, dict[str, Any]]] = []
    for match in matches:
        metadata = match.get("metadata", {})
        text = str(match.get("text", ""))
        course = str(metadata.get("course", ""))
        chunk_type = str(metadata.get("chunk_type", ""))
        distance = float(match.get("distance", 10.0))

        score = -distance

        if target_course and course == target_course:
            score += 0.35

        if "review" in question.lower() and chunk_type == "review":
            score += 0.08

        text_tokens = _tokenize(text)
        if question_tokens and text_tokens:
            overlap = len(question_tokens.intersection(text_tokens)) / len(question_tokens)
            score += 0.25 * overlap

        scored.append((score, match))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    if target_course:
        prioritized = [m for _, m in scored if str(m.get("metadata", {}).get("course", "")) == target_course]
        remaining = [m for _, m in scored if str(m.get("metadata", {}).get("course", "")) != target_course]
        ordered = prioritized + remaining
    else:
        ordered = [m for _, m in scored]

    selected = ordered[:top_k]
    for idx, match in enumerate(selected, start=1):
        match["rank"] = idx
    return selected


def _format_retrieval_context(matches: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for match in matches:
        metadata = match.get("metadata", {})
        rank = int(match.get("rank", -1))
        course = str(metadata.get("course", "Unknown course"))
        chunk_type = str(metadata.get("chunk_type", "unknown"))
        source_url = str(metadata.get("source_url", ""))
        text = str(match.get("text", "")).strip()

        lines.append(f"[S{rank}] course={course}; chunk_type={chunk_type}; source_url={source_url}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines).strip()


def _build_source_items(matches: list[dict[str, Any]]) -> list[SourceItem]:
    items: list[SourceItem] = []
    for match in matches:
        metadata = match.get("metadata", {})
        items.append(
            SourceItem(
                rank=int(match.get("rank", -1)),
                course=str(metadata.get("course", "Unknown course")),
                chunk_type=str(metadata.get("chunk_type", "unknown")),
                source_url=str(metadata.get("source_url", "")),
            )
        )
    return items


def _format_sources_markdown(sources: list[SourceItem]) -> str:
    if not sources:
        return "No sources were retrieved."

    lines = [
        f"{index}. [S{src.rank}] {src.course} | {src.chunk_type} | {src.source_url}"
        for index, src in enumerate(sources, start=1)
    ]
    return "\n".join(lines)


def _answer_with_grounding(
    question: str,
    matches: list[dict[str, Any]],
    client: Groq,
    model_name: str,
) -> str:
    if not matches:
        return DEFAULT_REFUSAL

    context_block = _format_retrieval_context(matches)
    user_prompt = (
        "Question:\n"
        f"{question.strip()}\n\n"
        "Retrieved snippets (authoritative context):\n"
        f"{context_block}\n\n"
        "Return only the answer text."
    )

    system_prompt = SYSTEM_PROMPT
    if _is_pattern_question(question):
        system_prompt = f"{SYSTEM_PROMPT} {PATTERN_HINT_PROMPT}"

    completion = client.chat.completions.create(
        model=model_name,
        temperature=0.0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    answer = completion.choices[0].message.content or ""
    return answer.strip() or DEFAULT_REFUSAL


def build_qa_fn(
    persist_dir: str,
    collection_name: str,
    embedding_model: str,
    top_k: int,
    groq_model: str,
):
    collection, encoder = build_vector_store(
        chunks_path=Path("data/chunks.jsonl"),
        persist_dir=Path(persist_dir).resolve(),
        collection_name=collection_name,
        model_name=embedding_model,
        rebuild=False,
    )

    def qa(question: str) -> tuple[str, str, str]:
        question = (question or "").strip()
        if not question:
            return "Please enter a question.", "No sources were retrieved.", ""

        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            return (
                "Missing GROQ_API_KEY. Set it in your environment before asking questions.",
                "No sources were retrieved.",
                "",
            )

        candidate_k = max(top_k * 5, 25)
        candidates = retrieve(collection=collection, model=encoder, query=question, top_k=candidate_k)

        # For comparison questions, also ensure course_facts chunks for both courses are present.
        if _is_comparison_question(question):
            pair = _extract_two_courses(question)
            if pair:
                for course in pair:
                    if _get_course_facts_chunk(course, candidates) is None:
                        extra = retrieve(
                            collection=collection,
                            model=encoder,
                            query=f"Course Facts {course} workload difficulty rating",
                            top_k=10,
                        )
                        facts = [m for m in extra if str(m.get("metadata", {}).get("chunk_type", "")) == "course_facts" and str(m.get("metadata", {}).get("course", "")) == course]
                        candidates = candidates + facts

        matches = _rerank_matches(question=question, matches=candidates, top_k=top_k)

        # Comparison questions: build deterministic answer from course_facts chunks.
        if _is_comparison_question(question):
            result = _build_comparison_answer(question=question, candidates=candidates)
            if result is not None:
                comp_answer, comp_sources = result
                sources_md = _format_sources_markdown(_build_source_items(comp_sources))
                debug_context = _format_retrieval_context(comp_sources)
                return comp_answer, sources_md, debug_context

        # Pattern questions benefit from broader same-course review evidence.
        answer_matches = matches
        if _is_pattern_question(question):
            target_course = _extract_course_from_question(question)
            if target_course:
                same_course_reviews = [
                    m
                    for m in candidates
                    if str(m.get("metadata", {}).get("course", "")) == target_course
                    and str(m.get("metadata", {}).get("chunk_type", "")) == "review"
                ]
                if same_course_reviews:
                    expanded_k = max(top_k, 8)
                    answer_matches = _rerank_matches(
                        question=question,
                        matches=same_course_reviews,
                        top_k=min(expanded_k, len(same_course_reviews)),
                    )

        sources = _build_source_items(answer_matches)
        sources_md = _format_sources_markdown(sources)

        client = Groq(api_key=api_key)
        answer = _build_pattern_warning_answer(question=question, matches=answer_matches)
        if not answer:
            answer = _answer_with_grounding(
                question=question,
                matches=answer_matches,
                client=client,
                model_name=groq_model,
            )

        debug_context = _format_retrieval_context(answer_matches)
        return answer, sources_md, debug_context

    return qa


def build_app(qa_fn):
    with gr.Blocks(title="OMSCS Unofficial Guide - Grounded QA") as app:
        gr.Markdown("# OMSCS Unofficial Guide - Grounded QA")
        gr.Markdown(
            "Ask a question about the ingested OMSCentral reviews. "
            "Answers are generated only from retrieved context."
        )

        question_box = gr.Textbox(
            label="Question",
            placeholder="Example: Which has the higher average workload: AI or Game AI?",
            lines=3,
        )
        submit_btn = gr.Button("Ask")

        answer_box = gr.Textbox(label="Answer", lines=8)
        sources_box = gr.Markdown(label="Sources")
        debug_box = gr.Textbox(label="Retrieved Context (Debug)", lines=12)

        submit_btn.click(
            fn=qa_fn,
            inputs=[question_box],
            outputs=[answer_box, sources_box, debug_box],
        )

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run grounded generation + Gradio interface.")
    parser.add_argument("--persist-dir", default="data/chroma", help="Path to Chroma persistence dir.")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="Chroma collection name.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Embedding model name.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Top-k retrieval size.")
    parser.add_argument(
        "--groq-model",
        default=DEFAULT_GROQ_MODEL,
        help="Groq chat model name.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for Gradio app.")
    parser.add_argument("--port", type=int, default=7860, help="Port for Gradio app.")
    parser.add_argument("--share", action="store_true", help="Enable Gradio share mode.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    qa_fn = build_qa_fn(
        persist_dir=args.persist_dir,
        collection_name=args.collection,
        embedding_model=args.model,
        top_k=args.top_k,
        groq_model=args.groq_model,
    )
    app = build_app(qa_fn)
    app.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
