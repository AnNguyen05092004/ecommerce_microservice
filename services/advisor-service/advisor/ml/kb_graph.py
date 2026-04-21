"""Neo4j Knowledge Graph layer for the advisor KB.

Graph schema
------------
Nodes:
  Document  {doc_id, title, language, content, source, category, priority,
             valid_from, valid_to}
  Product   {product_id, name, price, stock, product_type}
  Brand     {name}
  Category  {name}
  Customer  {user_id}
  Tag       {name}
  Intent    {name}

Relationships:
  (:Document)-[:BELONGS_TO]->(:Category)
  (:Document)-[:HAS_TAG]->(:Tag)
  (:Document)-[:HAS_INTENT]->(:Intent)
  (:Document)-[:ABOUT]->(:Product)
  (:Product)-[:BELONGS_TO]->(:Category)
  (:Product)-[:HAS_BRAND]->(:Brand)
  (:Product)-[:SIMILAR_TO {score}]->(:Product)
  (:Product)-[:OFTEN_BOUGHT_WITH]->(:Product)
  (:Customer)-[:VIEWS {count}]->(:Product)
  (:Customer)-[:BUYS {count}]->(:Product)
  (:Customer)-[:SEARCHES]->(:Category)
  (:Category)-[:IS_SUBCATEGORY_OF]->(:Category)
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter, defaultdict
from typing import TYPE_CHECKING

import requests
from django.conf import settings

from advisor.ml.kb_vector import KBChunk

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ─── Singleton driver ─────────────────────────────────────────────────────────

_driver = None


def get_neo4j_driver():
    """Return a (cached) Neo4j driver.  Returns None if neo4j is not installed
    or the server is unreachable, so callers can fall back gracefully."""
    global _driver  # noqa: PLW0603
    if _driver is not None:
        return _driver
    if not getattr(settings, "NEO4J_ENABLED", True):
        return None
    try:
        from neo4j import GraphDatabase  # noqa: PLC0415

        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        _driver.verify_connectivity()
        logger.info("Neo4j driver connected: %s", settings.NEO4J_URI)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Neo4j unavailable (%s) — graph retrieval disabled.", exc)
        _driver = None
    return _driver


def close_neo4j_driver():
    global _driver  # noqa: PLW0603
    if _driver is not None:
        _driver.close()
        _driver = None


# ─── Static category hierarchy ────────────────────────────────────────────────

CATEGORY_HIERARCHY = {
    "computer": None,
    "mobile": None,
    "tablet": None,
    "audio": None,
    "wearable": None,
    "component": "computer",
    "peripheral": "computer",
    "monitor": "computer",
    "accessory": None,
    "charging": None,
    "book": None,
    "clothes": None,
    "policy": None,
    "faq": None,
    "operations": None,
}

# ─── Intent / concept keywords (for query parsing) ────────────────────────────

CONCEPT_KEYWORDS = {
    "designer": ["computer", "monitor"],
    "gaming": ["computer", "monitor", "peripheral", "audio"],
    "sinh vien": ["computer", "mobile"],
    "student": ["computer", "mobile"],
    "van phong": ["computer", "peripheral"],
    "office": ["computer", "peripheral"],
    "chup anh": ["mobile"],
    "photography": ["mobile"],
    "nghe nhac": ["audio", "wearable"],
    "music": ["audio", "wearable"],
    "the thao": ["wearable"],
    "sport": ["wearable"],
    "doc sach": ["book", "tablet"],
    "reading": ["book", "tablet"],
}

CATEGORY_KEYWORDS = {
    "laptop": "computer",
    "computer": "computer",
    "pc": "computer",
    "may tinh": "computer",
    "mobile": "mobile",
    "phone": "mobile",
    "dien thoai": "mobile",
    "tablet": "tablet",
    "ipad": "tablet",
    "audio": "audio",
    "headphone": "audio",
    "tai nghe": "audio",
    "wearable": "wearable",
    "smartwatch": "wearable",
    "dong ho": "wearable",
    "monitor": "monitor",
    "man hinh": "monitor",
    "mouse": "peripheral",
    "keyboard": "peripheral",
    "chuot": "peripheral",
    "ban phim": "peripheral",
    "sac": "charging",
    "charger": "charging",
    "powerbank": "charging",
    "ram": "component",
    "cpu": "component",
    "ssd": "component",
    "accessory": "accessory",
    "phu kien": "accessory",
    "book": "book",
    "sach": "book",
    "clothes": "clothes",
    "quan ao": "clothes",
}

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _normalize_text(text: str) -> str:
    """Lowercase + strip accents for robust Vietnamese keyword matching."""
    raw = str(text or "").strip().lower()
    # NFD decomposition then drop combining marks to remove diacritics.
    return "".join(
        char
        for char in unicodedata.normalize("NFD", raw)
        if not unicodedata.combining(char)
    )


def _parse_query_intent(query: str):
    """Return (categories: list[str], concepts: list[str]) inferred from query."""
    normalized = _normalize_text(query)
    tokens = _TOKEN_RE.findall(normalized)
    token_set = set(tokens)

    categories = []
    concepts = []

    # Concept multi-word match
    for concept, cats in CONCEPT_KEYWORDS.items():
        if concept in normalized:
            concepts.append(concept)
            for cat in cats:
                if cat not in categories:
                    categories.append(cat)

    # Category match: support both single-word and multi-word phrases.
    for kw, cat in CATEGORY_KEYWORDS.items():
        normalized_kw = _normalize_text(kw)
        if (
            (" " in normalized_kw and normalized_kw in normalized)
            or normalized_kw in token_set
        ) and cat not in categories:
            categories.append(cat)

    return categories, concepts


# ─── Constraints + indexes ────────────────────────────────────────────────────


def _create_constraints_and_indexes(session):
    constraints = [
        "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
        "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE",
        "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT brand_name IF NOT EXISTS FOR (b:Brand) REQUIRE b.name IS UNIQUE",
        "CREATE CONSTRAINT tag_name IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE",
        "CREATE CONSTRAINT intent_name IF NOT EXISTS FOR (i:Intent) REQUIRE i.name IS UNIQUE",
        "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (cu:Customer) REQUIRE cu.user_id IS UNIQUE",
    ]
    for stmt in constraints:
        try:
            session.run(stmt)
        except Exception:  # noqa: BLE001
            pass  # constraint already exists

    # Full-text index for document search
    try:
        session.run(
            "CREATE FULLTEXT INDEX DocumentFullText IF NOT EXISTS "
            "FOR (d:Document) ON EACH [d.title, d.content, d.category]"
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        session.run(
            "CREATE FULLTEXT INDEX ProductFullText IF NOT EXISTS "
            "FOR (p:Product) ON EACH [p.name, p.product_type, p.brand]"
        )
    except Exception:  # noqa: BLE001
        pass


# ─── Phase 2A: Document ingestion ────────────────────────────────────────────


def build_kb_graph_documents(driver=None):
    """Ingest KBDocument rows from SQLite into Neo4j as Document nodes."""
    from advisor.models import KBDocument  # noqa: PLC0415

    driver = driver or get_neo4j_driver()
    if driver is None:
        return {"status": "skipped", "reason": "neo4j_unavailable"}

    documents = list(KBDocument.objects.all().order_by("id"))
    ingested = 0

    with driver.session() as session:
        _create_constraints_and_indexes(session)

        # Category hierarchy
        for cat, parent in CATEGORY_HIERARCHY.items():
            session.run("MERGE (:Category {name: $name})", name=cat)
            if parent:
                session.run(
                    "MATCH (child:Category {name: $child}), (parent:Category {name: $parent}) "
                    "MERGE (child)-[:IS_SUBCATEGORY_OF]->(parent)",
                    child=cat,
                    parent=parent,
                )

        for doc in documents:
            meta = doc.metadata or {}
            session.run(
                """
                MERGE (d:Document {doc_id: $doc_id})
                SET d.title = $title,
                    d.language = $language,
                    d.content = $content,
                    d.source = $source,
                    d.category = $category,
                    d.priority = $priority,
                    d.valid_from = $valid_from,
                    d.valid_to = $valid_to
                """,
                doc_id=int(doc.id),
                title=doc.title,
                language=doc.language,
                content=doc.content,
                source=doc.source,
                category=doc.category,
                priority=float(meta.get("priority", 1.0)),
                valid_from=str(meta.get("valid_from", "")),
                valid_to=str(meta.get("valid_to", "")),
            )

            # BELONGS_TO category
            if doc.category:
                session.run("MERGE (c:Category {name: $name})", name=doc.category)
                session.run(
                    "MATCH (d:Document {doc_id: $doc_id}), (c:Category {name: $cat}) "
                    "MERGE (d)-[:BELONGS_TO]->(c)",
                    doc_id=int(doc.id),
                    cat=doc.category,
                )

            # HAS_TAG
            for tag in meta.get("tags", []):
                tag_str = str(tag).strip()
                if tag_str:
                    session.run("MERGE (:Tag {name: $name})", name=tag_str)
                    session.run(
                        "MATCH (d:Document {doc_id: $doc_id}), (t:Tag {name: $tag}) "
                        "MERGE (d)-[:HAS_TAG]->(t)",
                        doc_id=int(doc.id),
                        tag=tag_str,
                    )

            # HAS_INTENT
            intent = str(meta.get("intent", "")).strip()
            if intent:
                session.run("MERGE (:Intent {name: $name})", name=intent)
                session.run(
                    "MATCH (d:Document {doc_id: $doc_id}), (i:Intent {name: $intent}) "
                    "MERGE (d)-[:HAS_INTENT]->(i)",
                    doc_id=int(doc.id),
                    intent=intent,
                )

            ingested += 1

    logger.info("KB Graph: ingested %d documents.", ingested)
    return {"status": "ok", "documents_ingested": ingested}


# ─── Phase 2B: Product + Customer entity extraction ──────────────────────────

_SERVICE_ENDPOINTS = {
    "computer": (settings.PRODUCT_SERVICE_URL, "/api/products/?type=computer"),
    "mobile": (settings.PRODUCT_SERVICE_URL, "/api/products/?type=mobile"),
    "clothes": (settings.PRODUCT_SERVICE_URL, "/api/products/?type=clothes"),
    "tablet": (settings.PRODUCT_SERVICE_URL, "/api/products/?type=tablet"),
    "audio": (settings.PRODUCT_SERVICE_URL, "/api/products/?type=audio"),
    "wearable": (settings.PRODUCT_SERVICE_URL, "/api/products/?type=wearable"),
    "component": (settings.PRODUCT_SERVICE_URL, "/api/products/?type=component"),
    "peripheral": (settings.PRODUCT_SERVICE_URL, "/api/products/?type=peripheral"),
    "monitor": (settings.PRODUCT_SERVICE_URL, "/api/products/?type=monitor"),
    "accessory": (settings.PRODUCT_SERVICE_URL, "/api/products/?type=accessory"),
    "charging": (settings.PRODUCT_SERVICE_URL, "/api/products/?type=charging"),
    "book": (settings.PRODUCT_SERVICE_URL, "/api/products/?type=book"),
}


def _fetch_products(product_type: str, base_url: str, path: str):
    """Fetch product list from a product service. Returns list of product dicts."""
    if not base_url:
        return []
    try:
        resp = requests.get(f"{base_url}{path}", timeout=5)
        if resp.ok:
            data = resp.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("results", data.get("data", []))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not fetch %s products: %s", product_type, exc)
    return []


def build_kb_graph_entities(driver=None):
    """Ingest Product/Brand/Customer nodes from product services + UserEvents."""
    from advisor.models import UserEvent  # noqa: PLC0415

    driver = driver or get_neo4j_driver()
    if driver is None:
        return {"status": "skipped", "reason": "neo4j_unavailable"}

    products_ingested = 0
    customers_ingested = 0

    with driver.session() as session:
        # ── Products from microservices ──────────────────────────────────────
        for product_type, (base_url, path) in _SERVICE_ENDPOINTS.items():
            products = _fetch_products(product_type, base_url, path)
            for p in products:
                pid = p.get("id") or p.get("product_id")
                name = str(p.get("name", "")).strip()
                if not pid or not name:
                    continue

                price = float(p.get("price", 0) or 0)
                stock = int(p.get("stock", 0) or 0)
                brand_name = str(p.get("brand", p.get("brand_name", ""))).strip()

                session.run(
                    """
                    MERGE (p:Product {product_id: $pid})
                    SET p.name = $name,
                        p.price = $price,
                        p.stock = $stock,
                        p.product_type = $product_type,
                        p.brand = $brand
                    """,
                    pid=f"{product_type}_{pid}",
                    name=name,
                    price=price,
                    stock=stock,
                    product_type=product_type,
                    brand=brand_name,
                )

                # BELONGS_TO category
                session.run("MERGE (:Category {name: $cat})", cat=product_type)
                session.run(
                    "MATCH (p:Product {product_id: $pid}), (c:Category {name: $cat}) "
                    "MERGE (p)-[:BELONGS_TO]->(c)",
                    pid=f"{product_type}_{pid}",
                    cat=product_type,
                )

                # HAS_BRAND
                if brand_name:
                    session.run("MERGE (:Brand {name: $b})", b=brand_name)
                    session.run(
                        "MATCH (p:Product {product_id: $pid}), (b:Brand {name: $b}) "
                        "MERGE (p)-[:HAS_BRAND]->(b)",
                        pid=f"{product_type}_{pid}",
                        b=brand_name,
                    )

                # Link Document ABOUT Product (same category + title keyword overlap)
                session.run(
                    """
                    MATCH (d:Document {category: $cat})
                    WHERE toLower(d.title) CONTAINS toLower($name)
                       OR toLower($name) CONTAINS toLower(d.title)
                    MATCH (p:Product {product_id: $pid})
                    MERGE (d)-[:ABOUT]->(p)
                    """,
                    cat=product_type,
                    name=name,
                    pid=f"{product_type}_{pid}",
                )

                products_ingested += 1

        # ── Customer behavior from UserEvent ────────────────────────────────
        events = list(UserEvent.objects.all().order_by("created_at"))
        customer_views: dict[str, Counter] = defaultdict(Counter)
        customer_buys: dict[str, Counter] = defaultdict(Counter)
        customer_searches: dict[str, set] = defaultdict(set)

        for evt in events:
            entity = evt.user_id or evt.session_id
            if not entity:
                continue
            pid_key = (
                f"{evt.product_type}_{evt.product_id}"
                if evt.product_id and evt.product_type
                else None
            )

            if (
                evt.event_type in ("product_detail_view", "product_list_view")
                and pid_key
            ):
                customer_views[entity][pid_key] += 1
            elif evt.event_type == "order_created" and pid_key:
                customer_buys[entity][pid_key] += 1
            elif evt.event_type == "search" and evt.product_type:
                customer_searches[entity].add(evt.product_type)

        for user_id, views in customer_views.items():
            session.run("MERGE (:Customer {user_id: $uid})", uid=user_id)
            customers_ingested += 1
            for pid_key, count in views.items():
                session.run(
                    "MATCH (cu:Customer {user_id: $uid}), (p:Product {product_id: $pid}) "
                    "MERGE (cu)-[r:VIEWS]->(p) SET r.count = $count",
                    uid=user_id,
                    pid=pid_key,
                    count=count,
                )

        for user_id, buys in customer_buys.items():
            session.run("MERGE (:Customer {user_id: $uid})", uid=user_id)
            for pid_key, count in buys.items():
                session.run(
                    "MATCH (cu:Customer {user_id: $uid}), (p:Product {product_id: $pid}) "
                    "MERGE (cu)-[r:BUYS]->(p) SET r.count = $count",
                    uid=user_id,
                    pid=pid_key,
                    count=count,
                )

        for user_id, cats in customer_searches.items():
            for cat in cats:
                session.run(
                    "MATCH (cu:Customer {user_id: $uid}), (c:Category {name: $cat}) "
                    "MERGE (cu)-[:SEARCHES]->(c)",
                    uid=user_id,
                    cat=cat,
                )

    logger.info(
        "KB Graph entities: %d products, %d customers.",
        products_ingested,
        customers_ingested,
    )
    return {
        "status": "ok",
        "products_ingested": products_ingested,
        "customers_ingested": customers_ingested,
    }


# ─── Phase 2C: Computed relationships ────────────────────────────────────────


def build_kb_graph_computed_edges(driver=None):
    """Compute SIMILAR_TO and OFTEN_BOUGHT_WITH edges from behavior data."""
    from advisor.models import UserEvent  # noqa: PLC0415

    driver = driver or get_neo4j_driver()
    if driver is None:
        return {"status": "skipped", "reason": "neo4j_unavailable"}

    events = list(UserEvent.objects.all().order_by("session_id", "created_at"))

    # ── OFTEN_BOUGHT_WITH: products co-bought in same session ─────────────
    session_orders: dict[str, list[str]] = defaultdict(list)
    for evt in events:
        if evt.event_type == "order_created" and evt.product_id and evt.product_type:
            key = f"{evt.product_type}_{evt.product_id}"
            session_orders[evt.session_id].append(key)

    co_buy_counter: Counter = Counter()
    for prods in session_orders.values():
        unique = list(set(prods))
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                pair = tuple(sorted([unique[i], unique[j]]))
                co_buy_counter[pair] += 1

    # ── SIMILAR_TO: products co-viewed by ≥2 customers ────────────────────
    customer_views: dict[str, set] = defaultdict(set)
    for evt in events:
        if (
            evt.event_type in ("product_detail_view",)
            and evt.product_id
            and evt.product_type
        ):
            entity = evt.user_id or evt.session_id
            customer_views[entity].add(f"{evt.product_type}_{evt.product_id}")

    co_view_counter: Counter = Counter()
    for viewed in customer_views.values():
        unique = list(viewed)
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                pair = tuple(sorted([unique[i], unique[j]]))
                co_view_counter[pair] += 1

    often_bought_edges = 0
    similar_edges = 0

    with driver.session() as session:
        for (p1, p2), count in co_buy_counter.items():
            if count >= 1:
                session.run(
                    """
                    MATCH (a:Product {product_id: $p1}), (b:Product {product_id: $p2})
                    MERGE (a)-[:OFTEN_BOUGHT_WITH]->(b)
                    MERGE (b)-[:OFTEN_BOUGHT_WITH]->(a)
                    """,
                    p1=p1,
                    p2=p2,
                )
                often_bought_edges += 1

        for (p1, p2), count in co_view_counter.items():
            if count >= 2:
                # score = co_view_count / (approximate total viewers)
                total_viewers = max(len(customer_views), 1)
                score = round(count / total_viewers, 4)
                session.run(
                    """
                    MATCH (a:Product {product_id: $p1}), (b:Product {product_id: $p2})
                    MERGE (a)-[r:SIMILAR_TO]->(b) SET r.score = $score
                    MERGE (b)-[r2:SIMILAR_TO]->(a) SET r2.score = $score
                    """,
                    p1=p1,
                    p2=p2,
                    score=score,
                )
                similar_edges += 1

    logger.info(
        "KB Graph computed: %d OFTEN_BOUGHT_WITH, %d SIMILAR_TO edges.",
        often_bought_edges,
        similar_edges,
    )
    return {
        "status": "ok",
        "often_bought_with_edges": often_bought_edges,
        "similar_to_edges": similar_edges,
    }


# ─── Master build function ────────────────────────────────────────────────────


def build_kb_graph(refresh: bool = False):
    """Run all ingestion phases. Returns combined stats dict."""
    driver = get_neo4j_driver()
    if driver is None:
        return {"status": "skipped", "reason": "neo4j_unavailable"}

    if refresh:
        # Wipe existing graph data before re-ingesting
        try:
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not clear graph: %s", exc)

    docs_result = build_kb_graph_documents(driver)
    entities_result = build_kb_graph_entities(driver)
    edges_result = build_kb_graph_computed_edges(driver)

    return {
        "status": "ok",
        "documents": docs_result,
        "entities": entities_result,
        "computed_edges": edges_result,
    }


# ─── Phase 3: Graph-based retrieval ──────────────────────────────────────────


def retrieve_documents_graph(
    query: str,
    language: str = "vi",
    limit: int = 3,
):
    """Retrieve KB documents using Neo4j graph traversal.

    Pipeline:
    1. Parse query → infer categories + concepts
    2. Cypher fulltext search on Document nodes
    3. Category-path traversal boost
    4. Traverse SIMILAR_TO / OFTEN_BOUGHT_WITH for product context docs
    5. Map results → KBChunk NamedTuple

    Returns ([KBChunk], mode_str).
    """
    driver = get_neo4j_driver()
    if driver is None:
        return [], "graph_unavailable"

    categories, concepts = _parse_query_intent(query)

    try:
        with driver.session() as session:
            chunks: list[KBChunk] = []
            seen_doc_ids: set[int] = set()

            # Step 1: Fulltext search on Document nodes
            ft_results = session.run(
                """
                CALL db.index.fulltext.queryNodes('DocumentFullText', $search_query)
                YIELD node AS d, score
                WHERE d.language IN [$language, 'vi', 'en']
                RETURN d.doc_id AS doc_id,
                       d.title AS title,
                       d.language AS language,
                       d.source AS source,
                       d.category AS category,
                       d.content AS content,
                       d.priority AS priority,
                       d.valid_from AS valid_from,
                       d.valid_to AS valid_to,
                       score
                ORDER BY score DESC
                LIMIT $limit_expanded
                """,
                search_query=query,
                language=language,
                limit_expanded=limit * 4,
            )
            ft_docs = list(ft_results)

            # Step 2: Category traversal — find Documents in inferred categories
            cat_docs = []
            for cat in categories:
                cat_results = session.run(
                    """
                    MATCH (d:Document)-[:BELONGS_TO]->(c:Category)
                    WHERE c.name = $cat AND d.language IN [$language, 'vi', 'en']
                    RETURN d.doc_id AS doc_id,
                           d.title AS title,
                           d.language AS language,
                           d.source AS source,
                           d.category AS category,
                           d.content AS content,
                           d.priority AS priority,
                           d.valid_from AS valid_from,
                           d.valid_to AS valid_to,
                           1.25 AS score
                    LIMIT $limit_expanded
                    """,
                    cat=cat,
                    language=language,
                    limit_expanded=limit * 2,
                )
                cat_docs.extend(list(cat_results))

            # Step 3: Traverse subcategory hierarchy (depth 1)
            sub_docs = []
            if categories:
                sub_results = session.run(
                    """
                    MATCH (child:Category)-[:IS_SUBCATEGORY_OF]->(parent:Category)
                    WHERE parent.name IN $cats
                    MATCH (d:Document)-[:BELONGS_TO]->(child)
                    WHERE d.language IN [$language, 'vi', 'en']
                    RETURN d.doc_id AS doc_id,
                           d.title AS title,
                           d.language AS language,
                           d.source AS source,
                           d.category AS category,
                           d.content AS content,
                           d.priority AS priority,
                           d.valid_from AS valid_from,
                           d.valid_to AS valid_to,
                           1.0 AS score
                    LIMIT $limit_expanded
                    """,
                    cats=categories,
                    language=language,
                    limit_expanded=limit,
                )
                sub_docs.extend(list(sub_results))

            # Step 4: Product-linked docs via ABOUT + SIMILAR_TO/OFTEN_BOUGHT_WITH
            product_docs = []
            if categories:
                prod_results = session.run(
                    """
                    MATCH (c:Category)<-[:BELONGS_TO]-(p:Product)
                    WHERE c.name IN $cats
                    MATCH (d:Document)-[:ABOUT]->(p)
                    RETURN d.doc_id AS doc_id,
                           d.title AS title,
                           d.language AS language,
                           d.source AS source,
                           d.category AS category,
                           d.content AS content,
                           d.priority AS priority,
                           d.valid_from AS valid_from,
                           d.valid_to AS valid_to,
                           1.1 AS score
                    LIMIT $limit_expanded
                    """,
                    cats=categories,
                    language=language,
                    limit_expanded=limit,
                )
                product_docs.extend(list(prod_results))

            # Merge all result sets, score order: ft > category > subcategory > product
            all_rows = []
            for row in ft_docs:
                all_rows.append(
                    (float(row["score"]) * float(row["priority"] or 1.0), row)
                )
            for row in cat_docs:
                all_rows.append(
                    (float(row["score"]) * float(row["priority"] or 1.0), row)
                )
            for row in sub_docs + product_docs:
                all_rows.append(
                    (float(row["score"]) * float(row["priority"] or 1.0), row)
                )

            all_rows.sort(key=lambda x: x[0], reverse=True)

            for _score, row in all_rows:
                doc_id = int(row["doc_id"])
                if doc_id in seen_doc_ids:
                    continue
                seen_doc_ids.add(doc_id)
                chunks.append(
                    KBChunk(
                        id=doc_id,
                        title=row["title"] or "",
                        language=row["language"] or "vi",
                        source=row["source"] or "",
                        category=row["category"] or "",
                        content=row["content"] or "",
                        metadata={
                            "priority": row["priority"],
                            "valid_from": row["valid_from"],
                            "valid_to": row["valid_to"],
                        },
                    )
                )
                if len(chunks) >= limit:
                    break

            return chunks, "graph_neo4j"

    except Exception as exc:  # noqa: BLE001
        logger.warning("Graph retrieval failed (%s) — caller should fallback.", exc)
        return [], "graph_error"


def _load_product_catalog(product_types, per_type_limit=200):
    from advisor.ml.recommend import fetch_products  # noqa: PLC0415

    catalog = {}
    for product_type in product_types:
        items = fetch_products(product_type, limit=per_type_limit)
        for item in items:
            raw_id = item.get("id") or item.get("product_id")
            if raw_id is None:
                continue
            catalog[f"{product_type}_{raw_id}"] = {
                **item,
                "product_type": product_type,
            }
    return catalog


def _build_behavior_preferences(user_id: str = "", session_id: str = ""):
    from advisor.models import UserEvent  # noqa: PLC0415

    queryset = UserEvent.objects.exclude(metadata__seeded=True)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    elif session_id:
        queryset = queryset.filter(session_id=session_id)
    else:
        queryset = queryset.none()

    category_counter = Counter()
    product_counter = Counter()
    search_terms = []

    for event in queryset.order_by("-created_at")[:200]:
        product_type = str(event.product_type or "").strip().lower()
        product_key = (
            f"{product_type}_{event.product_id}"
            if product_type and event.product_id is not None
            else ""
        )

        if product_type:
            if event.event_type == "order_created":
                category_counter[product_type] += 5
            elif event.event_type == "add_to_cart":
                category_counter[product_type] += 3
            elif event.event_type == "product_detail_view":
                category_counter[product_type] += 2
            elif event.event_type == "search":
                category_counter[product_type] += 1

        if product_key:
            if event.event_type == "order_created":
                product_counter[product_key] += 6
            elif event.event_type == "add_to_cart":
                product_counter[product_key] += 4
            elif event.event_type == "product_detail_view":
                product_counter[product_key] += 2

        if event.query_text:
            normalized = str(event.query_text).strip().lower()
            if normalized:
                search_terms.append(normalized)

    return {
        "top_categories": [category for category, _ in category_counter.most_common(4)],
        "category_scores": dict(category_counter),
        "product_scores": dict(product_counter),
        "recent_queries": search_terms[:10],
    }


def retrieve_products_graph(
    query: str,
    language: str = "vi",
    limit: int = 24,
    product_types=None,
    user_id: str = "",
    session_id: str = "",
):
    """Retrieve products using Neo4j fulltext + graph traversal.

    Returns (results, mode_str), where results is a list of hydrated product dicts.
    """
    del language  # reserved for future multilingual ranking

    driver = get_neo4j_driver()
    if driver is None:
        return [], "graph_unavailable"

    categories, _concepts = _parse_query_intent(query)
    behavior_preferences = _build_behavior_preferences(
        user_id=user_id, session_id=session_id
    )
    for preferred_category in behavior_preferences.get("top_categories", []):
        if preferred_category not in categories:
            categories.append(preferred_category)
    requested_types = []
    normalized_product_types = product_types
    if isinstance(normalized_product_types, str):
        normalized_product_types = [
            part.strip() for part in normalized_product_types.split(",") if part.strip()
        ]

    for item in normalized_product_types or []:
        value = str(item or "").strip().lower()
        if value and value not in requested_types:
            requested_types.append(value)

    if requested_types:
        categories = [
            cat for cat in categories if cat in requested_types
        ] or requested_types

    try:
        with driver.session() as session:
            scored_rows = []

            ft_rows = session.run(
                """
                CALL db.index.fulltext.queryNodes('ProductFullText', $search_query)
                YIELD node AS p, score
                WHERE $product_types = [] OR p.product_type IN $product_types
                RETURN p.product_id AS product_id,
                       p.name AS name,
                       p.product_type AS product_type,
                       p.brand AS brand,
                       p.price AS price,
                       p.stock AS stock,
                       score AS score
                ORDER BY score DESC
                LIMIT $limit_expanded
                """,
                search_query=query,
                product_types=requested_types,
                limit_expanded=max(limit * 4, 12),
            )
            scored_rows.extend((float(row["score"]), row) for row in ft_rows)

            if categories:
                cat_rows = session.run(
                    """
                    MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
                    WHERE c.name IN $cats
                      AND ($product_types = [] OR p.product_type IN $product_types)
                    RETURN p.product_id AS product_id,
                           p.name AS name,
                           p.product_type AS product_type,
                           p.brand AS brand,
                           p.price AS price,
                           p.stock AS stock,
                           1.15 AS score
                    LIMIT $limit_expanded
                    """,
                    cats=categories,
                    product_types=requested_types,
                    limit_expanded=max(limit * 3, 10),
                )
                scored_rows.extend((float(row["score"]), row) for row in cat_rows)

            if categories:
                related_rows = session.run(
                    """
                    MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
                    WHERE c.name IN $cats
                      AND ($product_types = [] OR p.product_type IN $product_types)
                    OPTIONAL MATCH (p)-[s:SIMILAR_TO|OFTEN_BOUGHT_WITH]->(related:Product)
                    WHERE $product_types = [] OR related.product_type IN $product_types
                    RETURN related.product_id AS product_id,
                           related.name AS name,
                           related.product_type AS product_type,
                           related.brand AS brand,
                           related.price AS price,
                           related.stock AS stock,
                           coalesce(s.score, 0.85) AS score
                    LIMIT $limit_expanded
                    """,
                    cats=categories,
                    product_types=requested_types,
                    limit_expanded=max(limit * 2, 8),
                )
                for row in related_rows:
                    if row["product_id"]:
                        scored_rows.append((float(row["score"]), row))

        if not scored_rows:
            return [], "graph_neo4j"

        if requested_types or categories:
            product_type_scope = requested_types or categories
        else:
            from advisor.ml.recommend import SERVICE_ENDPOINTS  # noqa: PLC0415

            product_type_scope = list(SERVICE_ENDPOINTS.keys())
        catalog = _load_product_catalog(product_type_scope)
        merged_scores = {}
        row_by_id = {}
        for score, row in scored_rows:
            product_id = row["product_id"]
            if not product_id:
                continue
            behavior_boost = 0.0
            product_type = str(row.get("product_type") or "").strip().lower()
            if product_type:
                behavior_boost += (
                    behavior_preferences.get("category_scores", {}).get(product_type, 0)
                    * 0.08
                )
            behavior_boost += (
                behavior_preferences.get("product_scores", {}).get(product_id, 0) * 0.12
            )

            final_score = float(score) + behavior_boost
            merged_scores[product_id] = max(
                final_score, merged_scores.get(product_id, 0.0)
            )
            row_by_id[product_id] = row

        ranked = sorted(merged_scores.items(), key=lambda item: item[1], reverse=True)
        results = []
        for product_id, score in ranked:
            hydrated = catalog.get(product_id)
            if not hydrated:
                row = row_by_id[product_id]
                hydrated = {
                    "id": str(product_id).split("_", 1)[-1],
                    "name": row["name"] or "San pham",
                    "brand": row.get("brand") or "TechStore",
                    "price": row.get("price") or 0,
                    "stock": row.get("stock") or 0,
                    "product_type": row.get("product_type") or "computer",
                }

            hydrated = {
                **hydrated,
                "semantic_score": round(float(score), 4),
                "reason": hydrated.get("reason")
                or "Ket qua semantic search tu advisor graph",
            }
            results.append(hydrated)
            if len(results) >= limit:
                break

        return results, "graph_neo4j"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Graph product search failed (%s).", exc)
        return [], "graph_error"
