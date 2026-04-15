from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from advisor.ml.behavior_gru import train_behavior_gru


class Command(BaseCommand):
    help = "Train GRU v1 behavior profile classifier from labeled event sequences"

    def add_arguments(self, parser):
        parser.add_argument(
            "--epochs",
            type=int,
            default=25,
            help="Number of training epochs (default: 25)",
        )

    def handle(self, *args, **options):
        sequence_path = Path(settings.ARTIFACTS_DIR) / "behavior_sequences.json"
        if not sequence_path.exists():
            raise CommandError(
                "behavior_sequences.json not found. Run build_behavior_dataset first."
            )

        self.stdout.write("Training GRU v1 behavior classifier...")
        metrics = train_behavior_gru(
            sequence_path,
            Path(settings.ARTIFACTS_DIR),
            epochs=int(options["epochs"]),
        )
        self.stdout.write(self.style.SUCCESS(f"GRU metrics: {metrics}"))
