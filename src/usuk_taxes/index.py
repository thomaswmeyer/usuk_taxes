"""Hybrid retrieval index: Chroma (local ONNX embeddings) + BM25.

Tax queries mix semantics ("can I deduct mortgage interest on my UK rental?")
with exact terms ("Form 1116", "section 911", "SA105"), so results from both
retrievers are merged with reciprocal rank fusion.
"""

import json
import re

import chromadb
from rank_bm25 import BM25Okapi

from .config import CHROMA_DIR, CHUNKS_PATH, DATA_DIR, FINAL_K, RETRIEVE_K
from .chunking import Chunk

COLLECTION = "usuk_taxes"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def build_index(chunks: list[Chunk]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHUNKS_PATH, "w") as f:
        for c in chunks:
            f.write(json.dumps(c.to_dict()) + "\n")

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    coll = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    batch = 256
    for i in range(0, len(chunks), batch):
        part = chunks[i : i + batch]
        coll.add(
            ids=[c.id for c in part],
            documents=[c.text for c in part],
            metadatas=[
                {"source_id": c.source_id, "title": c.title, "jurisdiction": c.jurisdiction, "seq": c.seq}
                for c in part
            ],
        )


def _load_chunks() -> list[dict]:
    if not CHUNKS_PATH.exists():
        raise SystemExit("No index found — run `usuk index` first.")
    with open(CHUNKS_PATH) as f:
        return [json.loads(line) for line in f]


def search(query: str, k: int = FINAL_K) -> list[dict]:
    """Hybrid search returning the top-k chunk dicts."""
    chunks = _load_chunks()
    by_id = {c["id"]: c for c in chunks}

    # Vector search
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    coll = client.get_collection(COLLECTION)
    res = coll.query(query_texts=[query], n_results=min(RETRIEVE_K, len(chunks)))
    vector_ranked = res["ids"][0]

    # BM25
    bm25 = BM25Okapi([_tokenize(c["text"]) for c in chunks])
    scores = bm25.get_scores(_tokenize(query))
    bm25_ranked = [
        chunks[i]["id"]
        for i in sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:RETRIEVE_K]
    ]

    # Reciprocal rank fusion
    fused: dict[str, float] = {}
    for ranking in (vector_ranked, bm25_ranked):
        for rank, cid in enumerate(ranking):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (60 + rank)

    top = sorted(fused, key=fused.get, reverse=True)[:k]
    return [by_id[cid] for cid in top]
