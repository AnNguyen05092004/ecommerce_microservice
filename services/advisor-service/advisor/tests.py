import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from advisor.ml.behavior_runtime import select_best_behavior_model
from advisor.ml.model_selection_report import (
    PRODUCTION_MODEL_MANIFEST,
    write_model_selection_artifacts,
)


class BehaviorModelManifestTests(SimpleTestCase):
    def test_manifest_is_generated_from_metrics(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_dir = Path(tmp_dir)
            (artifact_dir / "behavior_v2_metrics.json").write_text(
                json.dumps(
                    {"mode": "mlp_v2", "macro_f1": 0.81, "accuracy": 0.83, "rows": 50}
                )
            )
            (artifact_dir / "behavior_gru_metrics.json").write_text(
                json.dumps(
                    {"mode": "gru_v1", "macro_f1": 0.74, "accuracy": 0.79, "rows": 50}
                )
            )
            summary = write_model_selection_artifacts(artifact_dir)

            manifest = json.loads(
                (artifact_dir / PRODUCTION_MODEL_MANIFEST).read_text()
            )
            self.assertEqual("mlp", manifest["selected_model"])
            self.assertEqual("mlp", summary["best_model"])

    def test_runtime_prefers_manifest_when_available(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_dir = Path(tmp_dir)
            (artifact_dir / PRODUCTION_MODEL_MANIFEST).write_text(
                json.dumps({"selected_model": "mlp", "selected_model_score": 0.91})
            )
            (artifact_dir / "behavior_v2_metrics.json").write_text(
                json.dumps({"mode": "mlp_v2", "macro_f1": 0.91})
            )

            selected = select_best_behavior_model(artifact_dir, events=[])
            self.assertEqual("mlp", selected["name"])
            self.assertEqual("manifest", selected["selection_source"])
