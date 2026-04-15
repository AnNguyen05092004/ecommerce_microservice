from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from advisor.ml.kb_vector import build_kb_hybrid_index


class Command(BaseCommand):
    help = "Build hybrid TF-IDF index for KB semantic retrieval"

    def handle(self, *args, **options):
        metrics = build_kb_hybrid_index(Path(settings.ARTIFACTS_DIR))
        self.stdout.write(self.style.SUCCESS(f"KB index metrics: {metrics}"))
