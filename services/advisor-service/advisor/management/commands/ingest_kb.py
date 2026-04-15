from django.core.management.base import BaseCommand

from advisor.ml.kb import bootstrap_documents


class Command(BaseCommand):
    help = "Load built-in knowledge base documents into advisor-service"

    def add_arguments(self, parser):
        parser.add_argument("--noinput", action="store_true")
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Upsert documents from the JSON seed even when KB rows already exist",
        )

    def handle(self, *args, **options):
        summary = bootstrap_documents(refresh=options.get("refresh", False))
        self.stdout.write(
            self.style.SUCCESS(
                "Knowledge base documents available. "
                f"Inserted: {summary['inserted']}, Updated: {summary['updated']}"
            )
        )
