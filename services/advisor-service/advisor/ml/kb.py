import json
import pickle
from collections import Counter

from django.conf import settings

from advisor.models import KBDocument
from advisor.ml.kb_vector import retrieve_documents_hybrid
from advisor.ml.kb_graph import retrieve_documents_graph


def bootstrap_documents(refresh: bool = False):
    if not settings.KB_BOOTSTRAP_PATH.exists():
        return {"inserted": 0, "updated": 0}

    if KBDocument.objects.exists() and not refresh:
        return {"inserted": 0, "updated": 0}

    payload = json.loads(settings.KB_BOOTSTRAP_PATH.read_text())
    inserted = 0
    updated = 0
    for item in payload:
        defaults = {
            "category": item.get("category", "general"),
            "content": item["content"],
            "metadata": item.get("metadata", {}),
        }
        existing = KBDocument.objects.filter(
            title=item["title"],
            language=item.get("language", "vi"),
            source=item.get("source", "internal"),
        ).first()
        document, created = KBDocument.objects.update_or_create(
            title=item["title"],
            language=item.get("language", "vi"),
            source=item.get("source", "internal"),
            defaults=defaults,
        )
        if created:
            inserted += 1
        elif existing and (
            existing.category != defaults["category"]
            or existing.content != defaults["content"]
            or existing.metadata != defaults["metadata"]
        ):
            updated += 1
    return {"inserted": inserted, "updated": updated}


def retrieve_documents(query: str, language: str = "vi", limit: int = 3):
    # Try Neo4j Knowledge Graph first
    try:
        graph_docs, graph_mode = retrieve_documents_graph(
            query, language=language, limit=limit
        )
        if graph_docs and graph_mode not in ("graph_unavailable", "graph_error"):
            return graph_docs
    except Exception:  # noqa: BLE001
        pass

    # Fallback: hybrid TF-IDF
    hybrid_docs, mode = retrieve_documents_hybrid(
        query=query,
        artifact_dir=settings.ARTIFACTS_DIR,
        language=language,
        limit=limit,
    )
    if hybrid_docs:
        return hybrid_docs

    tokens = [token.lower() for token in query.split() if token.strip()]
    documents = list(KBDocument.objects.filter(language__in=[language, "vi", "en"]))
    scored = []
    for document in documents:
        haystack = f"{document.title} {document.category} {document.content}".lower()
        score = sum(Counter(haystack.split()).get(token, 0) for token in tokens)
        if score > 0:
            scored.append((score, document))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:limit]] or documents[:limit]


def get_retrieval_mode():
    # Check graph first
    try:
        from advisor.ml.kb_graph import get_neo4j_driver  # noqa: PLC0415

        if get_neo4j_driver() is not None:
            return "graph_neo4j"
    except Exception:  # noqa: BLE001
        pass
    # Check TF-IDF pkl fallback
    index_path = settings.ARTIFACTS_DIR / "kb_hybrid_index.pkl"
    if not index_path.exists():
        return "keyword_tf"
    try:
        with index_path.open("rb") as input_file:
            bundle = pickle.load(input_file)
        return "hybrid_tfidf_chunked" if bundle.get("chunks") else "hybrid_tfidf"
    except Exception:  # noqa: BLE001
        return "hybrid_tfidf"
