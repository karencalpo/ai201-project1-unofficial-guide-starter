from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_TOP_K = 3
DEFAULT_COLLECTION = "omscs_course_reviews"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no} in {path}: {exc}") from exc

    return records


def _build_chunk_id(chunk: dict[str, Any], fallback_index: int) -> str:
    doc_id = str(chunk.get("doc_id", "doc_unknown"))
    chunk_id = chunk.get("chunk_id")
    if chunk_id is None:
        chunk_id = fallback_index
    return f"{doc_id}_chunk_{chunk_id}"


def _chunk_metadata(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "doc_id": str(chunk.get("doc_id", "")),
        "course": str(chunk.get("course", "")),
        "source_url": str(chunk.get("source_url", "")),
        "chunk_id": str(chunk.get("chunk_id", "")),
        "chunk_type": str(chunk.get("chunk_type", "review")),
        "start_char": int(chunk.get("start_char", -1)),
        "end_char": int(chunk.get("end_char", -1)),
    }


def build_vector_store(
    chunks_path: Path,
    persist_dir: Path,
    collection_name: str,
    model_name: str,
    batch_size: int = 64,
    rebuild: bool = False,
) -> tuple[chromadb.Collection, SentenceTransformer]:
    chunks = read_jsonl(chunks_path)
    if not chunks:
        raise ValueError(f"No chunk records found in {chunks_path}")

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))

    if rebuild:
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    model = SentenceTransformer(model_name)

    # Only build embeddings if the collection is currently empty.
    if collection.count() == 0:
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            ids = [_build_chunk_id(chunk, fallback_index=start + i) for i, chunk in enumerate(batch)]
            docs = [str(chunk.get("text", "")) for chunk in batch]
            metadatas = [_chunk_metadata(chunk) for chunk in batch]
            embeddings = model.encode(docs, normalize_embeddings=True).tolist()

            collection.add(
                ids=ids,
                documents=docs,
                metadatas=metadatas,
                embeddings=embeddings,
            )

    return collection, model


def retrieve(
    collection: chromadb.Collection,
    model: SentenceTransformer,
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    query = query.strip()
    if not query:
        raise ValueError("query cannot be empty")

    query_embedding = model.encode([query], normalize_embeddings=True).tolist()[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    matches: list[dict[str, Any]] = []
    for rank, (doc, meta, distance) in enumerate(zip(docs, metas, distances), start=1):
        matches.append(
            {
                "rank": rank,
                "distance": float(distance),
                "text": doc,
                "metadata": meta,
            }
        )

    return matches


def print_matches(query: str, matches: list[dict[str, Any]], preview_chars: int = 350) -> None:
    print(f"\nQuery: {query}")
    print(f"Retrieved {len(matches)} chunk(s).")

    for match in matches:
        metadata = match["metadata"]
        text = match["text"]
        preview = text[:preview_chars]
        if len(text) > preview_chars:
            preview += "..."

        print("\n" + "-" * 72)
        print(f"Rank: {match['rank']} | Distance: {match['distance']:.6f}")
        print(f"Course: {metadata.get('course', '')}")
        print(f"Doc ID: {metadata.get('doc_id', '')} | Chunk ID: {metadata.get('chunk_id', '')}")
        print(f"Source: {metadata.get('source_url', '')}")
        print(f"Char span: {metadata.get('start_char', '')}..{metadata.get('end_char', '')}")
        print(f"Text preview: {preview}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Chroma embeddings from chunks and run semantic retrieval."
    )
    parser.add_argument(
        "--chunks-path",
        default="data/chunks.jsonl",
        help="Path to chunk records produced by ingest_and_chunk.py",
    )
    parser.add_argument(
        "--persist-dir",
        default="data/chroma",
        help="Directory for persistent Chroma database files.",
    )
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        help="Chroma collection name.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Sentence-Transformers embedding model name.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="Number of chunks to retrieve per query.",
    )
    parser.add_argument(
        "--query",
        default="",
        help="User question to retrieve against. If omitted, only builds/loads the vector store.",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional output path to save query + retrieved chunks as JSON.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete and rebuild the Chroma collection from chunks.",
    )
    args = parser.parse_args()

    collection, model = build_vector_store(
        chunks_path=Path(args.chunks_path),
        persist_dir=Path(args.persist_dir),
        collection_name=args.collection,
        model_name=args.model,
        rebuild=args.rebuild,
    )

    print(
        "Vector store ready: "
        f"collection='{args.collection}', chunks_indexed={collection.count()}, model='{args.model}'"
    )

    if args.query.strip():
        matches = retrieve(
            collection=collection,
            model=model,
            query=args.query,
            top_k=args.top_k,
        )
        print_matches(args.query, matches)

        if args.json_out.strip():
            output_payload = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "query": args.query,
                "top_k": args.top_k,
                "model": args.model,
                "collection": args.collection,
                "matches": matches,
            }
            output_path = Path(args.json_out)
            write_json(output_path, output_payload)
            print(f"\nSaved retrieval results to {output_path}")


if __name__ == "__main__":
    main()
