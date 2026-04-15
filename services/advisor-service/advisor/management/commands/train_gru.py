from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from advisor.ml.gru import train_gru


class Command(BaseCommand):
    help = "Train a GRU model to predict the next best category from event sequences"

    def handle(self, *args, **options):
        sequence_path = Path(settings.ARTIFACTS_DIR) / "behavior_sequences.json"
        if not sequence_path.exists():
            raise CommandError(
                "behavior_sequences.json not found. Run build_behavior_dataset first."
            )
        metrics = train_gru(sequence_path, Path(settings.ARTIFACTS_DIR))
        self.stdout.write(self.style.SUCCESS(f"GRU metrics: {metrics}"))
