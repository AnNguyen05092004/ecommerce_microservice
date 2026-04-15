"""Management command: build_kb_graph

Ingest KBDocument rows, product entities, and computed relationships
(SIMILAR_TO, OFTEN_BOUGHT_WITH) into the Neo4j Knowledge Graph.

Usage:
    python manage.py build_kb_graph              # incremental merge
    python manage.py build_kb_graph --refresh    # wipe graph first
    python manage.py build_kb_graph --skip-entities   # docs + edges only
    python manage.py build_kb_graph --skip-entities --skip-edges  # docs only
"""

from django.core.management.base import BaseCommand

from advisor.ml.kb_graph import (
    build_kb_graph_computed_edges,
    build_kb_graph_documents,
    build_kb_graph_entities,
    get_neo4j_driver,
)


class Command(BaseCommand):
    help = (
        "Build Neo4j Knowledge Graph from KBDocuments, product services, and UserEvents"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Wipe all existing graph data before re-ingesting",
        )
        parser.add_argument(
            "--skip-entities",
            action="store_true",
            help="Skip product/customer entity ingestion (docs only)",
        )
        parser.add_argument(
            "--skip-edges",
            action="store_true",
            help="Skip computed relationship building (SIMILAR_TO, OFTEN_BOUGHT_WITH)",
        )

    def handle(self, *args, **options):
        driver = get_neo4j_driver()
        if driver is None:
            self.stderr.write(
                self.style.ERROR(
                    "Neo4j is unavailable. Check NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD "
                    "settings and ensure the neo4j container is running."
                )
            )
            return

        if options["refresh"]:
            self.stdout.write("Clearing existing graph data...")
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            self.stdout.write(self.style.WARNING("Graph cleared."))

        # Phase 2A — Document nodes
        self.stdout.write("Ingesting KB documents...")
        doc_result = build_kb_graph_documents(driver)
        self.stdout.write(
            self.style.SUCCESS(
                f"  Documents: {doc_result.get('documents_ingested', '?')} nodes ingested."
            )
        )

        # Phase 2B — Product / Customer entities
        if not options["skip_entities"]:
            self.stdout.write("Ingesting product and customer entities...")
            entity_result = build_kb_graph_entities(driver)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Products: {entity_result.get('products_ingested', '?')}, "
                    f"Customers: {entity_result.get('customers_ingested', '?')}"
                )
            )
        else:
            self.stdout.write("Skipping entity ingestion (--skip-entities).")

        # Phase 2C — Computed edges
        if not options["skip_edges"]:
            self.stdout.write("Computing SIMILAR_TO and OFTEN_BOUGHT_WITH edges...")
            edges_result = build_kb_graph_computed_edges(driver)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  OFTEN_BOUGHT_WITH: {edges_result.get('often_bought_with_edges', '?')}, "
                    f"SIMILAR_TO: {edges_result.get('similar_to_edges', '?')}"
                )
            )
        else:
            self.stdout.write("Skipping computed edges (--skip-edges).")

        self.stdout.write(self.style.SUCCESS("Knowledge Graph build complete."))
