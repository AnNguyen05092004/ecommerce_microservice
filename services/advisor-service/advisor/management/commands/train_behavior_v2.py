from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from advisor.ml.behavior_v2 import train_behavior_v2


class Command(BaseCommand):
    help = "Train behavior profile model v2 from generated behavior dataset"

    def handle(self, *args, **options):
        dataset_path = Path(settings.ARTIFACTS_DIR) / "behavior_dataset.csv"
        if not dataset_path.exists():
            raise CommandError(
                "behavior_dataset.csv not found. Run build_behavior_dataset first."
            )

        metrics = train_behavior_v2(dataset_path, Path(settings.ARTIFACTS_DIR))
        self.stdout.write(self.style.SUCCESS(f"Behavior v2 metrics: {metrics}"))
