import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from advisor.ml.benchmark_suite import run_benchmark_suite


class Command(BaseCommand):
    help = "Run automated advisor benchmark for chat, recommendations, and semantic search"

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            default="http://gateway:8000",
            help="Gateway base URL reachable from current runtime (default: http://gateway:8000)",
        )
        parser.add_argument(
            "--config",
            default=str(Path(settings.BASE_DIR).parent / "docs" / "ai_benchmark_prompts.json"),
            help="Benchmark config JSON path",
        )
        parser.add_argument(
            "--phase",
            default="phase-final",
            help="Phase label for report output",
        )
        parser.add_argument(
            "--report-version",
            default="v2.0",
            help="Version tag for benchmark report",
        )

    def handle(self, *args, **options):
        config_path = Path(options["config"])
        if not config_path.exists():
            raise CommandError(f"Config not found: {config_path}")

        payload = json.loads(config_path.read_text(encoding="utf-8"))
        if not payload.get("chat_prompts"):
            raise CommandError("chat_prompts is empty")
        if not payload.get("recommendation_cases"):
            raise CommandError("recommendation_cases is empty")
        if not payload.get("semantic_cases"):
            raise CommandError("semantic_cases is empty")

        report = run_benchmark_suite(
            options["base_url"],
            payload,
            Path(settings.ARTIFACTS_DIR),
            phase=options["phase"],
            version=options["report_version"],
        )
        self.stdout.write(self.style.SUCCESS(f"Benchmark completed: {report['generated_at']}"))
        self.stdout.write(self.style.SUCCESS(f"Artifacts written to {settings.ARTIFACTS_DIR}"))