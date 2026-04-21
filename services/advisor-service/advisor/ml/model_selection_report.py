import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path


MODEL_COMPARISON_MD = "model_comparison_report.md"
MODEL_COMPARISON_HTML = "model_comparison_report.html"
PRODUCTION_MODEL_MANIFEST = "behavior_model_manifest.json"
VALIDATION_CURVE_PLOT = "model_validation_accuracy_curve.png"

MODEL_FILES = {
    "baseline": "baseline_metrics.json",
    "mlp": "behavior_v2_metrics.json",
    "rnn": "behavior_rnn_metrics.json",
    "gru": "behavior_gru_metrics.json",
    "lstm": "behavior_lstm_metrics.json",
    "bilstm": "behavior_bilstm_metrics.json",
}

PRODUCTION_CANDIDATES = ("mlp", "rnn", "gru", "lstm", "bilstm")


def load_metrics_file(artifact_dir: Path, filename: str) -> dict:
    path = artifact_dir / filename
    if not path.exists():
        return {"mode": "not_found"}
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {"mode": "invalid_metrics"}


def collect_model_metrics(artifact_dir: Path) -> dict:
    return {
        name: load_metrics_file(artifact_dir, filename)
        for name, filename in MODEL_FILES.items()
    }


def _metric_value(metrics: dict, key: str):
    value = metrics.get(key)
    return value if isinstance(value, (int, float)) else None


def find_best_model(models: dict) -> str:
    best_model = "mlp"
    best_score = -1.0

    for model_name in PRODUCTION_CANDIDATES:
        metrics = models.get(model_name, {})
        score = _metric_value(metrics, "macro_f1")
        if score is not None and score > best_score:
            best_model = model_name
            best_score = float(score)

    return best_model


def build_production_manifest(models: dict) -> dict:
    best_model = find_best_model(models)
    best_metrics = models.get(best_model, {})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selected_model": best_model,
        "selection_basis": "highest_macro_f1",
        "selected_model_score": _metric_value(best_metrics, "macro_f1"),
        "selected_model_accuracy": _metric_value(best_metrics, "accuracy"),
        "fallback_model": "mlp",
        "candidates": [
            {
                "name": name,
                "mode": models.get(name, {}).get("mode", "unknown"),
                "macro_f1": _metric_value(models.get(name, {}), "macro_f1"),
                "accuracy": _metric_value(models.get(name, {}), "accuracy"),
                "rows": models.get(name, {}).get("rows", 0),
                "train_rows": models.get(name, {}).get("train_rows", 0),
                "test_rows": models.get(name, {}).get("test_rows", 0),
            }
            for name in PRODUCTION_CANDIDATES
        ],
    }


def generate_comparison_table(models: dict) -> str:
    rows = [
        "| Model | Mode | Rows | Train Rows | Test Rows | Accuracy | Macro F1 | Status |",
        "|-------|------|------|-----------|-----------|----------|----------|--------|",
    ]

    for model_name, metrics in models.items():
        rows.append(
            "| {name} | {mode} | {rows} | {train_rows} | {test_rows} | {accuracy} | {macro_f1} | {status} |".format(
                name=model_name.upper(),
                mode=metrics.get("mode", "unknown"),
                rows=metrics.get("rows", "-"),
                train_rows=metrics.get("train_rows", "-"),
                test_rows=metrics.get("test_rows", "-"),
                accuracy=metrics.get("accuracy", "-"),
                macro_f1=metrics.get("macro_f1", "-"),
                status=(
                    "✅"
                    if metrics.get("mode") not in {"not_found", "invalid_metrics"}
                    else "❌"
                ),
            )
        )
    return "\n".join(rows)


def generate_markdown_report(models: dict, manifest: dict) -> str:
    return "\n".join(
        [
            "# AI Model Comparison Report",
            "",
            "## Summary",
            f"**Best Model**: {manifest['selected_model'].upper()}",
            f"**Selection Basis**: {manifest['selection_basis']}",
            f"**Generated At**: {manifest['generated_at']}",
            "",
            "## Model Performance Table",
            "",
            generate_comparison_table(models),
            "",
            "## Production Manifest",
            "",
            f"- Selected model: **{manifest['selected_model']}**",
            f"- Selected macro F1: **{manifest.get('selected_model_score')}**",
            f"- Fallback model: **{manifest.get('fallback_model')}**",
            "",
        ]
    )


def generate_html_report(models: dict, manifest: dict) -> str:
    rows = []
    for model_name, metrics in models.items():
        rows.append(
            "<tr><td>{name}</td><td>{mode}</td><td>{rows}</td><td>{train_rows}</td><td>{test_rows}</td><td>{accuracy}</td><td>{macro_f1}</td></tr>".format(
                name=escape(model_name.upper()),
                mode=escape(str(metrics.get("mode", "unknown"))),
                rows=escape(str(metrics.get("rows", "-"))),
                train_rows=escape(str(metrics.get("train_rows", "-"))),
                test_rows=escape(str(metrics.get("test_rows", "-"))),
                accuracy=escape(str(metrics.get("accuracy", "-"))),
                macro_f1=escape(str(metrics.get("macro_f1", "-"))),
            )
        )

    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Model Comparison Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; background: #f8fafc; }}
    .hero {{ background: linear-gradient(135deg, #1d4ed8, #4338ca); color: white; padding: 24px; border-radius: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 24px 0; }}
    .card {{ background: white; border-radius: 16px; padding: 18px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 16px; overflow: hidden; }}
    th, td {{ padding: 12px 14px; border-bottom: 1px solid #e5e7eb; text-align: left; }}
    th {{ background: #eef2ff; }}
  </style>
</head>
<body>
  <div class="hero">
    <h1>AI Model Comparison Report</h1>
    <p>Generated at {generated_at}</p>
  </div>
  <div class="grid">
    <div class="card"><strong>Selected Model</strong><div>{best_model}</div></div>
    <div class="card"><strong>Macro F1</strong><div>{best_score}</div></div>
    <div class="card"><strong>Fallback Model</strong><div>{fallback_model}</div></div>
    <div class="card"><strong>Selection Basis</strong><div>{basis}</div></div>
  </div>
  <div class="card">
    <h2>Model Metrics</h2>
    <table>
      <thead>
        <tr>
          <th>Model</th><th>Mode</th><th>Rows</th><th>Train</th><th>Test</th><th>Accuracy</th><th>Macro F1</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
    <div class="card">
        <h2>Visualizations</h2>
        <p><strong>Final comparison</strong></p>
        <img src="model_comparison_plot.png" alt="Model comparison plot" style="max-width: 100%; border-radius: 12px; margin-bottom: 16px;">
        <p><strong>Validation accuracy by epoch</strong></p>
        <img src="model_validation_accuracy_curve.png" alt="Validation accuracy curve" style="max-width: 100%; border-radius: 12px;">
    </div>
</body>
</html>
    """.format(
        generated_at=escape(manifest["generated_at"]),
        best_model=escape(str(manifest["selected_model"]).upper()),
        best_score=escape(str(manifest.get("selected_model_score", "-"))),
        fallback_model=escape(str(manifest.get("fallback_model", "mlp")).upper()),
        basis=escape(str(manifest.get("selection_basis", "highest_macro_f1"))),
        rows="".join(rows),
    )


MODEL_COMPARISON_PLOT = "model_comparison_plot.png"


def generate_model_comparison_plot(models: dict, artifact_dir: Path) -> bool:
    """Generate a grouped bar chart (Accuracy + Macro F1) for all models.

    Saves model_comparison_plot.png to artifact_dir.
    Returns True on success, False if matplotlib is unavailable.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")  # non-interactive backend, safe in containers
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return False

    candidate_names = [n for n in PRODUCTION_CANDIDATES if n in models]
    accuracies = []
    f1_scores = []
    for name in candidate_names:
        m = models[name]
        acc = _metric_value(m, "accuracy")
        f1 = _metric_value(m, "macro_f1")
        accuracies.append(acc if acc is not None else 0.0)
        f1_scores.append(f1 if f1 is not None else 0.0)

    x = np.arange(len(candidate_names))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width / 2, accuracies, width, label="Accuracy", color="#4f86c6")
    bars2 = ax.bar(x + width / 2, f1_scores, width, label="Macro F1", color="#f4845f")

    ax.set_xlabel("Model")
    ax.set_ylabel("Score")
    ax.set_title("Model Comparison: Accuracy vs Macro F1")
    ax.set_xticks(x)
    ax.set_xticklabels([n.upper() for n in candidate_names])
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.bar_label(bars1, fmt="%.3f", padding=3, fontsize=8)
    ax.bar_label(bars2, fmt="%.3f", padding=3, fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    fig.tight_layout()
    plot_path = artifact_dir / MODEL_COMPARISON_PLOT
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    return True


def generate_validation_accuracy_curve(models: dict, artifact_dir: Path) -> bool:
    """Generate a line chart of validation accuracy across epochs."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    curve_models = []
    for model_name in ("rnn", "lstm", "bilstm"):
        history = models.get(model_name, {}).get("val_accuracy_history", [])
        if isinstance(history, list) and history:
            curve_models.append((model_name.upper(), history))

    if not curve_models:
        return False

    fig, ax = plt.subplots(figsize=(10, 6))
    for label, history in curve_models:
        epochs = list(range(len(history)))
        ax.plot(epochs, history, linewidth=2, label=f"{label} Val Acc")

    ax.set_title("Validation Accuracy Comparison")
    ax.set_xlabel("Epochs")
    ax.set_ylabel("Accuracy")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig(artifact_dir / VALIDATION_CURVE_PLOT, dpi=150)
    plt.close(fig)
    return True


def write_model_selection_artifacts(artifact_dir: Path) -> dict:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    models = collect_model_metrics(artifact_dir)
    manifest = build_production_manifest(models)

    (artifact_dir / PRODUCTION_MODEL_MANIFEST).write_text(
        json.dumps(manifest, indent=2)
    )
    (artifact_dir / MODEL_COMPARISON_MD).write_text(
        generate_markdown_report(models, manifest)
    )
    (artifact_dir / MODEL_COMPARISON_HTML).write_text(
        generate_html_report(models, manifest)
    )
    generate_model_comparison_plot(models, artifact_dir)
    generate_validation_accuracy_curve(models, artifact_dir)

    return {
        "best_model": manifest["selected_model"],
        "manifest": manifest,
        "models": models,
        "report_files": {
            "markdown": str(artifact_dir / MODEL_COMPARISON_MD),
            "html": str(artifact_dir / MODEL_COMPARISON_HTML),
            "manifest": str(artifact_dir / PRODUCTION_MODEL_MANIFEST),
            "plot": str(artifact_dir / MODEL_COMPARISON_PLOT),
            "validation_curve": str(artifact_dir / VALIDATION_CURVE_PLOT),
        },
    }
