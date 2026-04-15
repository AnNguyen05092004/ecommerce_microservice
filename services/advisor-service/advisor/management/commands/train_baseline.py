from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from advisor.ml.baseline import train_baseline


class Command(BaseCommand):
    help = "Train the baseline buy_score model from the generated dataset"

    def handle(self, *args, **options):
        dataset_path = Path(settings.ARTIFACTS_DIR) / "behavior_dataset.csv"
        if not dataset_path.exists():
            raise CommandError(
                "behavior_dataset.csv not found. Run build_behavior_dataset first."
            )
        metrics = train_baseline(dataset_path, Path(settings.ARTIFACTS_DIR))
        self.stdout.write(self.style.SUCCESS(f"Baseline metrics: {metrics}"))
