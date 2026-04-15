import math
import pickle
import re
from datetime import date
from pathlib import Path
from typing import NamedTuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from advisor.models import KBDocument


TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)

CHUNK_SIZE = 300  # characters
CHUNK_OVERLAP = 50  # characters

CATEGORY_HINTS = {
    "computer": {"laptop", "pc", "computer", "notebook", "ultrabook", "gpu"},
    "mobile": {"mobile", "phone", "smartphone", "iphone", "android"},
    "clothes": {"clothes", "fashion", "shirt", "jacket", "jean", "ao"},
    "tablet": {"tablet", "ipad"},
    "audio": {"audio", "headphone", "earbud", "speaker", "tai", "nghe"},
    "wearable": {"wearable", "smartwatch", "watch", "dong", "ho"},
    "component": {"component", "cpu", "ram", "ssd", "mainboard", "psu"},
    "peripheral": {"peripheral", "keyboard", "mouse", "webcam"},
    "monitor": {"monitor", "display", "man", "hinh"},
    "accessory": {"accessory", "case", "cover", "phu", "kien"},
    "charging": {"charging", "charger", "powerbank", "sac", "pin"},
    "book": {"book", "sach", "guide", "learning"},
}

TEMPORAL_KEYWORDS = {
    "today",
    "hom",
    "nay",
    "hien",
    "tai",
    "promo",
    "promotion",
    "khuyen",
    "mai",
    "sale",
}


class KBChunk(NamedTuple):
    """Lightweight chunk returned by retrieval — same interface as KBDocument."""

    id: int  # parent doc_id
    title: str
    language: str
    source: str
    category: str
    content: str  # chunk text (not full doc)
    metadata: dict


def _normalize_text(text: str):
    return (text or "").strip().lower()


def _tokenize(text: str):
    return TOKEN_PATTERN.findall(_normalize_text(text))


def _lexical_score(query_tokens, document_text: str):
    if not query_tokens:
        return 0.0
    haystack = _normalize_text(document_text)
    hits = sum(1 for token in query_tokens if token in haystack)
    return hits / max(1, len(query_tokens))


def _infer_query_category(query_tokens):
    token_set = set(query_tokens)
    if not token_set:
        return ""

    best_category = ""
    best_score = 0
    for category, hints in CATEGORY_HINTS.items():
        score = len(token_set & hints)
        if score > best_score:
            best_score = score
            best_category = category
    return best_category


def _is_temporal_query(query_tokens):
    return bool(set(query_tokens) & TEMPORAL_KEYWORDS)


def _is_doc_active(metadata):
    metadata = metadata or {}
    valid_from = str(metadata.get("valid_from") or "").strip()
    valid_to = str(metadata.get("valid_to") or "").strip()
    if not valid_from and not valid_to:
        return True

    today = date.today()
    try:
        if valid_from and today < date.fromisoformat(valid_from):
            return False
        if valid_to and today > date.fromisoformat(valid_to):
            return False
    except ValueError:
        return True
    return True


def _priority_weight(metadata):
    metadata = metadata or {}
    try:
        weight = float(metadata.get("priority", 1.0))
    except (TypeError, ValueError):
        weight = 1.0
    return max(0.5, min(2.0, weight))


def rerank_documents(query, docs, method="simple"):
    """Rerank retrieved docs with optional semantic step.

    method='simple': tf-idf cosine and keep docs over 0.6, fallback to top-1.
    method='cross_encoder': placeholder for Phase 8.
    """
    docs = list(docs or [])
    if not query or not docs:
        return docs

    if method == "cross_encoder":
        # Placeholder for a heavier reranker in a future phase.
        return docs

    corpus = [
        _normalize_text(
            " ".join(
                [
                    getattr(doc, "title", "") or "",
                    getattr(doc, "content", "") or "",
                    getattr(doc, "category", "") or "",
                ]
            )
        )
        for doc in docs
    ]

    try:
        vectorizer = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1)
        matrix = vectorizer.fit_transform([_normalize_text(query), *corpus])
        query_vec = matrix[0]
        doc_matrix = matrix[1:]
        scores = cosine_similarity(query_vec, doc_matrix).ravel()
    except Exception:
        return docs

    scored = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
    filtered = [docs[idx] for idx, score in scored if score >= 0.6]
    if filtered:
        return filtered

    # Keep at least one item so answer flow does not collapse when threshold is strict.
    return [docs[scored[0][0]]] if scored else docs


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Split text into overlapping chunks, splitting at word boundaries where possible."""
    text = (text or "").strip()
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Try to extend to a word boundary within a small lookahead window.
        if end < len(text):
            space_pos = text.rfind(" ", start, end + 30)
            if space_pos > start:
                end = space_pos
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        next_start = end - overlap
        if next_start <= start:
            next_start = start + 1
        start = next_start

    return chunks


def build_kb_hybrid_index(artifact_dir: Path):
    artifact_dir.mkdir(parents=True, exist_ok=True)
    documents = list(KBDocument.objects.all().order_by("id"))
    if not documents:
        return {
            "mode": "empty",
            "rows": 0,
            "chunks": 0,
            "index_path": str(artifact_dir / "kb_hybrid_index.pkl"),
        }

    corpus = []
    chunk_meta = []
    for doc in documents:
        content_chunks = _chunk_text(doc.content or "")
        if not content_chunks:
            content_chunks = [""]
        metadata = doc.metadata or {}
        metadata_text = " ".join(
            str(metadata.get(key, ""))
            for key in ["audience", "role", "scenario", "intent"]
        )
        for chunk_idx, chunk_text in enumerate(content_chunks):
            index_text = _normalize_text(
                f"{doc.title}\n{doc.category}\n{metadata_text}\n{chunk_text}"
            )
            corpus.append(index_text)
            chunk_meta.append(
                {
                    "doc_id": int(doc.id),
                    "chunk_idx": chunk_idx,
                    "title": doc.title,
                    "language": doc.language,
                    "source": doc.source,
                    "category": doc.category,
                    "chunk_text": chunk_text,
                    "metadata": metadata,
                }
            )

    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
    matrix = vectorizer.fit_transform(corpus)

    bundle = {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "chunks": chunk_meta,
        "rows": len(chunk_meta),
        # Retain legacy "metadata" key so old callers don't crash on load.
        "metadata": [
            {
                "id": c["doc_id"],
                "title": c["title"],
                "language": c["language"],
                "source": c["source"],
                "category": c["category"],
                "metadata": c.get("metadata", {}),
            }
            for c in chunk_meta
        ],
    }

    index_path = artifact_dir / "kb_hybrid_index.pkl"
    with index_path.open("wb") as output_file:
        pickle.dump(bundle, output_file)

    return {
        "mode": "hybrid_tfidf_chunked",
        "rows": len(documents),
        "chunks": len(chunk_meta),
        "index_path": str(index_path),
    }


def retrieve_documents_hybrid(
    query: str,
    artifact_dir: Path,
    language: str = "vi",
    limit: int = 3,
):
    index_path = artifact_dir / "kb_hybrid_index.pkl"
    if not index_path.exists():
        return [], "keyword_tf"

    with index_path.open("rb") as input_file:
        bundle = pickle.load(input_file)

    vectorizer = bundle["vectorizer"]
    matrix = bundle["matrix"]
    # Support both new chunk-aware format and legacy format.
    chunk_meta = bundle.get("chunks") or bundle.get("metadata") or []
    if not chunk_meta:
        return [], "hybrid_tfidf"

    query_text = _normalize_text(query)
    if not query_text:
        return [], "hybrid_tfidf"

    query_vector = vectorizer.transform([query_text])
    dense_scores = cosine_similarity(query_vector, matrix).ravel()
    query_tokens = _tokenize(query_text)
    inferred_category = _infer_query_category(query_tokens)
    temporal_query = _is_temporal_query(query_tokens)

    scored = []
    for idx, chunk in enumerate(chunk_meta):
        row_lang = (chunk.get("language") or "").lower()
        if row_lang and row_lang not in {language.lower(), "vi", "en"}:
            continue

        metadata = chunk.get("metadata") or {}
        if temporal_query and not _is_doc_active(metadata):
            continue

        lexical = _lexical_score(
            query_tokens,
            " ".join(
                [
                    chunk.get("title", ""),
                    chunk.get("category", ""),
                    chunk.get("source", ""),
                    str((chunk.get("metadata") or {}).get("audience", "")),
                    str((chunk.get("metadata") or {}).get("role", "")),
                    str((chunk.get("metadata") or {}).get("scenario", "")),
                    str(metadata.get("intent", "")),
                    " ".join(str(tag) for tag in (metadata.get("tags") or [])),
                ]
            ),
        )
        dense = float(dense_scores[idx]) if idx < len(dense_scores) else 0.0
        hybrid = 0.7 * dense + 0.3 * lexical
        if inferred_category and chunk.get("category") == inferred_category:
            hybrid *= 1.25
        hybrid *= _priority_weight(metadata)
        if hybrid <= 0:
            continue
        scored.append((hybrid, idx))

    scored.sort(key=lambda item: item[0], reverse=True)
    top_indices = [idx for _, idx in scored[: max(1, limit * 3)]]
    if not top_indices:
        return [], "hybrid_tfidf"

    # Diversity rerank: prefer one chunk per document, then fill remaining slots.
    final_chunks: list[KBChunk] = []
    seen_doc_ids: set[int] = set()
    remaining: list[KBChunk] = []

    for idx in top_indices:
        chunk = chunk_meta[idx]
        doc_id = chunk.get("doc_id") or chunk.get("id", 0)
        kb_chunk = KBChunk(
            id=int(doc_id),
            title=chunk.get("title", ""),
            language=chunk.get("language", "vi"),
            source=chunk.get("source", ""),
            category=chunk.get("category", ""),
            content=chunk.get("chunk_text") or chunk.get("content", ""),
            metadata=chunk.get("metadata") or {},
        )
        if doc_id not in seen_doc_ids:
            seen_doc_ids.add(doc_id)
            final_chunks.append(kb_chunk)
            if len(final_chunks) >= limit:
                break
        else:
            remaining.append(kb_chunk)

    for kb_chunk in remaining:
        if len(final_chunks) >= limit:
            break
        final_chunks.append(kb_chunk)

    reranked = rerank_documents(query_text, final_chunks[:limit], method="simple")
    return reranked[:limit], "hybrid_tfidf_chunked+rerank_simple"
