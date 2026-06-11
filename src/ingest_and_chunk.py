from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class SourceDocument:
    course: str
    url: str


SOURCES: list[SourceDocument] = [
    SourceDocument(
        course="Artificial Intelligence",
        url="https://www.omscentral.com/courses/artificial-intelligence/reviews",
    ),
    SourceDocument(
        course="Knowledge-Based AI",
        url="https://www.omscentral.com/courses/knowledge-based-ai/reviews",
    ),
    SourceDocument(
        course="Machine Learning",
        url="https://www.omscentral.com/courses/machine-learning/reviews",
    ),
    SourceDocument(
        course="Introduction to Graduate Algorithms",
        url="https://www.omscentral.com/courses/introduction-to-graduate-algorithms/reviews",
    ),
    SourceDocument(
        course="AI, Ethics, and Society",
        url="https://www.omscentral.com/courses/ai-ethics-and-society/reviews",
    ),
    SourceDocument(
        course="Human-Computer Interaction",
        url="https://www.omscentral.com/courses/human-computer-interaction/reviews",
    ),
    SourceDocument(
        course="Introduction to Computer Vision",
        url="https://www.omscentral.com/courses/introduction-to-computer-vision/reviews",
    ),
    SourceDocument(
        course="Game Artificial Intelligence",
        url="https://www.omscentral.com/courses/game-artificial-intelligence/reviews",
    ),
    SourceDocument(
        course="Deep Learning",
        url="https://www.omscentral.com/courses/deep-learning/reviews",
    ),
    SourceDocument(
        course="Natural Language Processing",
        url="https://www.omscentral.com/courses/natural-language-processing/reviews",
    ),
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
}


def fetch_html(url: str, timeout: int = 30) -> str:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _remove_identifier_like_tokens(text: str) -> str:
    token_pattern = re.compile(r"\b[A-Za-z0-9+/]{16,}={0,2}\b")

    def replace_if_identifier(match: re.Match[str]) -> str:
        token = match.group(0)
        has_upper = any(char.isupper() for char in token)
        has_lower = any(char.islower() for char in token)
        has_digit = any(char.isdigit() for char in token)
        has_base64_chars = ("+" in token) or ("/" in token) or ("=" in token)

        # Heuristic: drop long, mixed-case alphanumeric tokens that look like IDs.
        if has_upper and has_lower and has_digit and (has_base64_chars or len(token) >= 20):
            return " "
        return token

    cleaned = token_pattern.sub(replace_if_identifier, text)
    return _normalize_whitespace(cleaned)


def _remove_stray_equals_artifacts(text: str) -> str:
    text = text.replace("+ ==", " ")
    text = text.replace("==", " ")
    text = " ".join(text.split())
    return text


def _find_course_metadata(obj: Any) -> dict[str, Any]:
    """Walk __NEXT_DATA__ JSON and extract top-level course fact fields."""
    result: dict[str, Any] = {}

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key in ("creditHours", "credit_hours"):
                if key in value and isinstance(value[key], (int, float)):
                    result.setdefault("credit_hours", value[key])
            for key in ("avgRating", "averageRating"):
                if key in value and isinstance(value[key], (int, float)):
                    result.setdefault("avg_rating", value[key])
            for key in ("avgDifficulty", "averageDifficulty"):
                if key in value and isinstance(value[key], (int, float)):
                    result.setdefault("avg_difficulty", value[key])
            for key in ("avgWorkload", "averageWorkload"):
                if key in value and isinstance(value[key], (int, float)):
                    result.setdefault("avg_workload", value[key])
            for key in ("codes", "courseCode", "code"):
                if key in value:
                    val = value[key]
                    if isinstance(val, list) and val:
                        result.setdefault("course_code", str(val[0]))
                    elif isinstance(val, str) and val:
                        result.setdefault("course_code", val)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    return result


def extract_course_facts(raw_html: str) -> dict[str, Any]:
    """Return a dict of course fact fields extracted from the page's __NEXT_DATA__ JSON."""
    soup = BeautifulSoup(raw_html, "html.parser")
    next_data_script = soup.find("script", id="__NEXT_DATA__")
    if not next_data_script or not next_data_script.string:
        return {}
    try:
        payload = json.loads(next_data_script.string)
    except json.JSONDecodeError:
        return {}
    return _find_course_metadata(payload)


def extract_course_facts_from_cleaned_text(cleaned_text: str) -> dict[str, Any]:
    """
    Parse course facts from the beginning of cleaned page text, where OMSCentral
    surfaces quick facts like rating, difficulty, workload, Listed As, and
    Credit Hours.
    """
    header = cleaned_text[:2000]
    facts: dict[str, Any] = {}

    rating_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*5\s+rating", header, flags=re.IGNORECASE)
    if rating_match:
        facts["avg_rating"] = float(rating_match.group(1))

    difficulty_match = re.search(
        r"(\d+(?:\.\d+)?)\s*/\s*5\s+difficulty", header, flags=re.IGNORECASE
    )
    if difficulty_match:
        facts["avg_difficulty"] = float(difficulty_match.group(1))

    workload_match = re.search(r"(\d+(?:\.\d+)?)\s*hrs?\s*/\s*week", header, flags=re.IGNORECASE)
    if workload_match:
        facts["avg_workload"] = float(workload_match.group(1))

    code_match = re.search(
        r"Listed As\s+([A-Za-z]{2,5}-?\d{3,5})", header, flags=re.IGNORECASE
    )
    if code_match:
        facts["course_code"] = code_match.group(1).upper()

    credit_match = re.search(r"Credit Hours\s+(\d+)", header, flags=re.IGNORECASE)
    if credit_match:
        facts["credit_hours"] = int(credit_match.group(1))

    return facts


def build_course_facts_text(course: str, facts: dict[str, Any]) -> str:
    """Format the text field for a course_facts chunk."""
    parts = [f"Course Facts: {course}."]
    if "course_code" in facts:
        parts.append(f"Listed As: {facts['course_code']}.")
    if "credit_hours" in facts:
        parts.append(f"Credit Hours: {int(facts['credit_hours'])}.")
    if "avg_rating" in facts:
        parts.append(f"Average Rating: {facts['avg_rating']:.2f} / 5.")
    if "avg_difficulty" in facts:
        parts.append(f"Average Difficulty: {facts['avg_difficulty']:.2f} / 5.")
    if "avg_workload" in facts:
        parts.append(f"Average Workload: {facts['avg_workload']:.2f} hrs / week.")
    return " ".join(parts)


def _find_reviews_containers(obj: Any) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if "reviews" in value and isinstance(value["reviews"], list):
                for review in value["reviews"]:
                    if isinstance(review, dict):
                        reviews.append(review)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    return reviews


def _extract_structured_text_from_next_data(soup: BeautifulSoup) -> str:
    next_data_script = soup.find("script", id="__NEXT_DATA__")
    if not next_data_script or not next_data_script.string:
        return ""

    try:
        payload = json.loads(next_data_script.string)
    except json.JSONDecodeError:
        return ""

    course_chunks: list[str] = []
    reviews = _find_reviews_containers(payload)

    for review in reviews:
        fields: list[str] = []
        for key in (
            "term",
            "rating",
            "difficulty",
            "workload",
            "professor",
            "title",
            "review",
            "createdAt",
        ):
            value = review.get(key)
            if value is None:
                continue
            value_text = _normalize_whitespace(str(value))
            if value_text:
                fields.append(f"{key}: {value_text}")
        if fields:
            course_chunks.append(" | ".join(fields))

    return "\n".join(course_chunks).strip()


def _extract_visible_page_text(soup: BeautifulSoup) -> str:
    for tag_name in ["script", "style", "noscript", "svg", "img", "footer", "header", "nav"]:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    candidate_roots = []
    for selector in ["main", "article", "section", "body"]:
        root = soup.select_one(selector)
        if root:
            candidate_roots.append(root)

    best_text = ""
    for root in candidate_roots:
        text = _normalize_whitespace(root.get_text(separator=" ", strip=True))
        if len(text) > len(best_text):
            best_text = text

    # Remove high-noise UI strings repeatedly seen on course sites.
    noise_patterns = [
        r"Sign in",
        r"Sign up",
        r"Back to all courses",
        r"Write a review",
        r"Share your experience",
        r"Cookie Policy",
        r"Privacy Policy",
        r"Terms of Service",
    ]
    cleaned = best_text
    for pattern in noise_patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    return _normalize_whitespace(cleaned)


def clean_course_document(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")

    structured_text = _extract_structured_text_from_next_data(soup)
    visible_text = _extract_visible_page_text(soup)

    combined = "\n\n".join(part for part in [structured_text, visible_text] if part)
    combined = _remove_identifier_like_tokens(combined)
    combined = _remove_stray_equals_artifacts(combined)
    return _normalize_whitespace(combined)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict[str, Any]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap cannot be negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    if not text:
        return []

    chunks: list[dict[str, Any]] = []
    step = chunk_size - overlap
    start = 0
    chunk_id = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "start_char": start,
                    "end_char": end,
                    "text": chunk,
                }
            )
            chunk_id += 1
        start += step

    return chunks


def build_documents_and_chunks(
    sources: list[SourceDocument], chunk_size: int = 500, overlap: int = 50
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    documents: list[dict[str, Any]] = []
    all_chunks: list[dict[str, Any]] = []

    for index, source in enumerate(sources, start=1):
        raw_html = fetch_html(source.url)
        cleaned_text = clean_course_document(raw_html)

        doc_id = f"doc_{index:02d}"
        documents.append(
            {
                "doc_id": doc_id,
                "course": source.course,
                "source_url": source.url,
                "text": cleaned_text,
                "char_count": len(cleaned_text),
            }
        )

        chunks = chunk_text(cleaned_text, chunk_size=chunk_size, overlap=overlap)
        for chunk in chunks:
            all_chunks.append(
                {
                    "doc_id": doc_id,
                    "course": source.course,
                    "source_url": source.url,
                    "chunk_id": chunk["chunk_id"],
                    "chunk_type": "review",
                    "start_char": chunk["start_char"],
                    "end_char": chunk["end_char"],
                    "text": chunk["text"],
                }
            )

        # Append one synthetic course_facts chunk per document.
        facts = extract_course_facts(raw_html)
        # Fill any missing facts from the cleaned document header.
        header_facts = extract_course_facts_from_cleaned_text(cleaned_text)
        for key, value in header_facts.items():
            facts.setdefault(key, value)
        facts_text = build_course_facts_text(source.course, facts)
        all_chunks.append(
            {
                "doc_id": doc_id,
                "course": source.course,
                "source_url": source.url,
                "chunk_id": "facts",
                "chunk_type": "course_facts",
                "start_char": 0,
                "end_char": 0,
                "text": facts_text,
            }
        )

    return documents, all_chunks


def write_jsonl(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def select_representative_chunks(
    chunks: list[dict[str, Any]], sample_count: int
) -> list[dict[str, Any]]:
    if sample_count <= 0 or not chunks:
        return []
    if sample_count >= len(chunks):
        return chunks

    # Evenly spread samples across the full chunk list.
    if sample_count == 1:
        indices = [0]
    else:
        indices = [round(i * (len(chunks) - 1) / (sample_count - 1)) for i in range(sample_count)]

    seen: set[int] = set()
    selected: list[dict[str, Any]] = []
    for idx in indices:
        if idx in seen:
            continue
        seen.add(idx)
        selected.append(chunks[idx])
    return selected


def print_representative_chunks(
    chunks: list[dict[str, Any]], sample_count: int, preview_chars: int
) -> None:
    selected = select_representative_chunks(chunks, sample_count)
    if not selected:
        print("No chunks available to sample.")
        return

    print(f"\nRepresentative chunk samples ({len(selected)}):")
    for i, chunk in enumerate(selected, start=1):
        text = chunk["text"]
        preview = text[:preview_chars]
        if len(text) > preview_chars:
            preview += "..."

        print(f"\n[{i}] {chunk['course']} | {chunk['doc_id']} | chunk_id={chunk['chunk_id']}")
        print(f"source_url: {chunk['source_url']}")
        print(f"char_span: {chunk['start_char']}..{chunk['end_char']}")
        print(f"text_preview: {preview}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest OMSCentral course pages and create fixed-size chunks for RAG."
    )
    parser.add_argument(
        "--documents-out",
        default="data/documents.jsonl",
        help="Output path for cleaned source documents as JSONL.",
    )
    parser.add_argument(
        "--chunks-out",
        default="data/chunks.jsonl",
        help="Output path for chunked records as JSONL.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Chunk size in characters.",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Overlap size in characters.",
    )
    parser.add_argument(
        "--debug-sample-count",
        type=int,
        default=0,
        help="Print this many representative chunks for inspection. Set 0 to disable.",
    )
    parser.add_argument(
        "--debug-preview-chars",
        type=int,
        default=240,
        help="Maximum characters to print per sampled chunk preview.",
    )
    args = parser.parse_args()

    documents, chunks = build_documents_and_chunks(
        SOURCES,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )

    docs_path = Path(args.documents_out)
    chunks_path = Path(args.chunks_out)
    write_jsonl(documents, docs_path)
    write_jsonl(chunks, chunks_path)

    print(f"Saved {len(documents)} documents to {docs_path}")
    print(f"Saved {len(chunks)} chunks to {chunks_path}")

    # Debug chunk preview disabled.
    # if args.debug_sample_count > 0:
    #     print_representative_chunks(
    #         chunks,
    #         sample_count=args.debug_sample_count,
    #         preview_chars=args.debug_preview_chars,
    #     )


if __name__ == "__main__":
    main()
