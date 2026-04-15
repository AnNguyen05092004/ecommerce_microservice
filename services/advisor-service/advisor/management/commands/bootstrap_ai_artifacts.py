import json
import pickle
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from advisor.ml.behavior_gru import train_behavior_gru
from advisor.ml.behavior_v2 import (
    BehaviorV2HeuristicModel,
    METRICS_FILENAME,
    MODEL_FILENAME,
    train_behavior_v2,
)
from advisor.ml.kb_vector import build_kb_hybrid_index
from advisor.ml.kb_graph import build_kb_graph


class Command(BaseCommand):
    help = "Bootstrap AI artifacts (KB index + behavior models) for fresh deployments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-kb",
            action="store_true",
            help="Skip KB bootstrap/index build",
        )
        parser.add_argument(
            "--skip-behavior",
            action="store_true",
            help="Skip behavior dataset/model bootstrap",
        )
        parser.add_argument(
            "--gru-epochs",
            type=int,
            default=25,
            help="GRU epochs when training behavior GRU (default: 25)",
        )

    def _ensure_behavior_fallback_artifact(self, artifacts_dir: Path, note: str):
        fallback = BehaviorV2HeuristicModel()
        with (artifacts_dir / MODEL_FILENAME).open("wb") as output_file:
            pickle.dump(fallback, output_file)
        metrics = {
            "mode": "bootstrap_heuristic_fallback",
            "rows": 0,
            "classes": BehaviorV2HeuristicModel.CLASSES,
            "note": note,
        }
        (artifacts_dir / METRICS_FILENAME).write_text(json.dumps(metrics, indent=2))
        return metrics

    def _bootstrap_kb(self, artifacts_dir: Path):
        call_command("ingest_kb", noinput=True, refresh=True)
        kb_metrics = build_kb_hybrid_index(artifacts_dir)
        # Build Neo4j Knowledge Graph (graceful — won't abort if Neo4j is down)
        try:
            graph_result = build_kb_graph(refresh=False)
            kb_metrics["graph"] = graph_result
        except Exception as exc:  # noqa: BLE001
            kb_metrics["graph"] = {"status": "skipped", "reason": str(exc)}
        return kb_metrics

    def _bootstrap_behavior(self, artifacts_dir: Path, gru_epochs: int):
        call_command("build_behavior_dataset")
        dataset_path = artifacts_dir / "behavior_dataset.csv"
        sequence_path = artifacts_dir / "behavior_sequences.json"

        behavior_metrics = {}
        if not dataset_path.exists() or dataset_path.stat().st_size == 0:
            behavior_metrics["behavior_v2"] = self._ensure_behavior_fallback_artifact(
                artifacts_dir,
                "Dataset missing/empty during bootstrap. Using heuristic fallback.",
            )
        else:
            try:
                frame = pd.read_csv(dataset_path)
                if frame.empty or frame.columns.size == 0:
                    behavior_metrics["behavior_v2"] = (
                        self._ensure_behavior_fallback_artifact(
                            artifacts_dir,
                            "Dataset has no rows during bootstrap. Using heuristic fallback.",
                        )
                    )
                else:
                    behavior_metrics["behavior_v2"] = train_behavior_v2(
                        dataset_path, artifacts_dir
                    )
            except Exception as exc:  # noqa: BLE001
                behavior_metrics["behavior_v2"] = (
                    self._ensure_behavior_fallback_artifact(
                        artifacts_dir,
                        f"Dataset parse/train failed during bootstrap: {exc}",
                    )
                )

        if sequence_path.exists() and sequence_path.stat().st_size > 0:
            try:
                behavior_metrics["behavior_gru"] = train_behavior_gru(
                    sequence_path, artifacts_dir, epochs=max(1, int(gru_epochs))
                )
            except Exception as exc:  # noqa: BLE001
                behavior_metrics["behavior_gru"] = {
                    "mode": "bootstrap_gru_failed",
                    "note": str(exc),
                }
        else:
            behavior_metrics["behavior_gru"] = {
                "mode": "sequence_missing",
                "note": "behavior_sequences.json unavailable during bootstrap",
            }

        return behavior_metrics

    def handle(self, *args, **options):
        artifacts_dir = Path(settings.ARTIFACTS_DIR)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        summary = {
            "artifacts_dir": str(artifacts_dir),
            "kb": None,
            "behavior": None,
        }

        if not options["skip_kb"]:
            self.stdout.write("Bootstrapping KB artifacts...")
            summary["kb"] = self._bootstrap_kb(artifacts_dir)

        if not options["skip_behavior"]:
            self.stdout.write("Bootstrapping behavior artifacts...")
            summary["behavior"] = self._bootstrap_behavior(
                artifacts_dir, options["gru_epochs"]
            )

        summary_path = artifacts_dir / "bootstrap_ai_artifacts_report.json"
        summary_path.write_text(json.dumps(summary, indent=2))
        self.stdout.write(self.style.SUCCESS(f"Bootstrap summary: {summary}"))
        self.stdout.write(self.style.SUCCESS(f"Report written to {summary_path}"))
