import json
from pathlib import Path

from advisor.ml.behavior_bilstm import infer_behavior_bilstm
from advisor.ml.behavior_gru import infer_behavior_gru
from advisor.ml.behavior_lstm import infer_behavior_lstm
from advisor.ml.model_selection_report import PRODUCTION_MODEL_MANIFEST
from advisor.ml.behavior_v2 import infer_behavior_v2


MODEL_CANDIDATES = [
    {
        "name": "bilstm",
        "metrics_file": "behavior_bilstm_metrics.json",
        "infer": infer_behavior_bilstm,
        "requires_events": True,
    },
    {
        "name": "lstm",
        "metrics_file": "behavior_lstm_metrics.json",
        "infer": infer_behavior_lstm,
        "requires_events": True,
    },
    {
        "name": "gru",
        "metrics_file": "behavior_gru_metrics.json",
        "infer": infer_behavior_gru,
        "requires_events": True,
    },
    {
        "name": "mlp",
        "metrics_file": "behavior_v2_metrics.json",
        "infer": None,
        "requires_events": False,
    },
]


def _read_metrics(artifact_dir: Path, filename: str):
    path = artifact_dir / filename
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _read_manifest(artifact_dir: Path):
    path = artifact_dir / PRODUCTION_MODEL_MANIFEST
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError):
        return {}


def select_best_behavior_model(artifact_dir: Path, events=None):
    manifest = _read_manifest(artifact_dir)
    manifest_name = str(manifest.get("selected_model") or "").strip().lower()
    best_candidate = None
    best_score = -1.0
    has_events = bool(events)

    if manifest_name:
        for candidate in MODEL_CANDIDATES:
            if candidate["name"] != manifest_name:
                continue
            if candidate["requires_events"] and not has_events:
                break
            return {
                "name": candidate["name"],
                "score": manifest.get("selected_model_score"),
                "metrics": _read_metrics(artifact_dir, candidate["metrics_file"]),
                "infer": candidate["infer"],
                "selection_source": "manifest",
            }

    for candidate in MODEL_CANDIDATES:
        if candidate["requires_events"] and not has_events:
            continue

        metrics = _read_metrics(artifact_dir, candidate["metrics_file"])
        score = metrics.get("macro_f1")
        if not isinstance(score, (int, float)):
            score = -1.0

        if score > best_score:
            best_score = float(score)
            best_candidate = {
                "name": candidate["name"],
                "score": round(float(score), 4) if score >= 0 else None,
                "metrics": metrics,
                "infer": candidate["infer"],
                "selection_source": "metrics",
            }

    if best_candidate is not None:
        return best_candidate

    return {
        "name": "mlp",
        "score": None,
        "metrics": _read_metrics(artifact_dir, "behavior_v2_metrics.json"),
        "infer": None,
        "selection_source": "fallback",
    }


def infer_behavior(features: dict, artifact_dir: Path, events=None):
    selected = select_best_behavior_model(artifact_dir, events=events)

    if selected["name"] == "mlp":
        result = infer_behavior_v2(features, artifact_dir, events=None)
    else:
        result = selected["infer"](events or [], artifact_dir)
        if result is None:
            result = infer_behavior_v2(features, artifact_dir, events=events)
            selected = select_best_behavior_model(artifact_dir, events=None)

    result = result or {
        "label": "uncertain",
        "confidence": 0.0,
        "mode": "unavailable",
        "top3_classes": [],
    }
    result["selected_model"] = selected["name"]
    result["selected_model_score"] = selected["score"]
    result["selection_source"] = selected.get("selection_source", "metrics")
    return result
