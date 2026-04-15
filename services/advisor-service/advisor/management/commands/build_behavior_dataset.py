from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from advisor.ml.dataset import build_behavior_dataset


class Command(BaseCommand):
    help = "Build a behavior dataset and sequence file from raw user events"

    def handle(self, *args, **options):
        artifacts_dir = Path(settings.ARTIFACTS_DIR)
        dataset_path, sequence_path = build_behavior_dataset(artifacts_dir)
        self.stdout.write(self.style.SUCCESS(f"Dataset written to {dataset_path}"))
        self.stdout.write(self.style.SUCCESS(f"Sequences written to {sequence_path}"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Train split written to {artifacts_dir / 'behavior_train.csv'}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Validation split written to {artifacts_dir / 'behavior_val.csv'}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Test split written to {artifacts_dir / 'behavior_test.csv'}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Data quality report written to {artifacts_dir / 'behavior_data_quality.json'}"
            )
        )
