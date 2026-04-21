"""Wrapper script to generate model comparison reports and production manifest."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "services" / "advisor-service"))

import numpy as np
from advisor.ml.model_selection_report import (
    MODEL_COMPARISON_HTML,
    MODEL_COMPARISON_MD,
    PRODUCTION_MODEL_MANIFEST,
    collect_model_metrics,
    find_best_model,
    write_model_selection_artifacts,
)

# Try to import visualization libraries
try:
    import matplotlib.pyplot as plt
    import seaborn as sns

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def plot_accuracy_comparison(models: dict, output_path: Path):
    """Plot accuracy comparison bar chart."""
    if not MATPLOTLIB_AVAILABLE:
        return

    model_names = []
    accuracies = []

    for model_name, metrics in models.items():
        acc = metrics.get("accuracy")
        if isinstance(acc, (int, float)):
            model_names.append(model_name.upper())
            accuracies.append(acc)

    if not accuracies:
        return

    plt.figure(figsize=(10, 6))
    bars = plt.bar(
        model_names,
        accuracies,
        color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
    )
    plt.ylabel("Accuracy", fontsize=12)
    plt.title("Model Accuracy Comparison", fontsize=14, fontweight="bold")
    plt.ylim(0, 1.0)
    plt.grid(axis="y", alpha=0.3)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{height:.4f}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    plt.tight_layout()
    plt.savefig(output_path / "01_accuracy_comparison.png", dpi=150)
    plt.close()


def plot_f1_comparison(models: dict, output_path: Path):
    """Plot macro F1 score comparison bar chart."""
    if not MATPLOTLIB_AVAILABLE:
        return

    model_names = []
    f1_scores = []

    for model_name, metrics in models.items():
        f1 = metrics.get("macro_f1")
        if isinstance(f1, (int, float)):
            model_names.append(model_name.upper())
            f1_scores.append(f1)

    if not f1_scores:
        return

    plt.figure(figsize=(10, 6))
    bars = plt.bar(
        model_names,
        f1_scores,
        color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
    )
    plt.ylabel("Macro F1 Score", fontsize=12)
    plt.title("Model F1 Score Comparison", fontsize=14, fontweight="bold")
    plt.ylim(0, 1.0)
    plt.grid(axis="y", alpha=0.3)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{height:.4f}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    plt.tight_layout()
    plt.savefig(output_path / "02_f1_comparison.png", dpi=150)
    plt.close()


def plot_metrics_heatmap(models: dict, output_path: Path):
    """Plot metrics heatmap (accuracy vs F1 vs precision/recall)."""
    if not MATPLOTLIB_AVAILABLE:
        return

    model_names = []
    metrics_data = []

    for model_name, metrics in models.items():
        if metrics.get("mode") == "not_found":
            continue
        model_names.append(model_name.upper())
        metrics_data.append(
            [
                metrics.get("accuracy", 0),
                metrics.get("macro_f1", 0),
                metrics.get("test_rows", 0)
                / max(1, metrics.get("rows", 1)),  # test ratio
            ]
        )

    if not metrics_data:
        return

    plt.figure(figsize=(10, 6))
    data = np.array(metrics_data)
    sns.heatmap(
        data.T,
        annot=True,
        fmt=".4f",
        cmap="RdYlGn",
        xticklabels=model_names,
        yticklabels=["Accuracy", "Macro F1", "Test Ratio"],
        cbar_kws={"label": "Score"},
    )
    plt.title("Model Metrics Heatmap", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path / "03_metrics_heatmap.png", dpi=150)
    plt.close()


def generate_report(artifact_dir: Path, models: dict) -> str:
    """Compatibility wrapper retained for older callers."""
    return write_model_selection_artifacts(artifact_dir)["manifest"]["selected_model"]


def main(artifact_dir: Path = None):
    """Main comparison workflow."""
    if artifact_dir is None:
        from django.conf import settings

        artifact_dir = Path(settings.ARTIFACTS_DIR)

    artifact_dir.mkdir(parents=True, exist_ok=True)

    print("🔄 Collecting model metrics...")
    models = collect_model_metrics(artifact_dir)

    print("📊 Generating comparison table...")
    table = generate_comparison_table(models)
    print(table)

    print("🎯 Finding best model...")
    best_model = find_best_model(models)
    print(f"✅ Best model: {best_model.upper()}")

    if MATPLOTLIB_AVAILABLE:
        print("📈 Generating comparison plots...")
        plot_accuracy_comparison(models, artifact_dir)
        print("   ✅ Saved: 01_accuracy_comparison.png")

        plot_f1_comparison(models, artifact_dir)
        print("   ✅ Saved: 02_f1_comparison.png")

        plot_metrics_heatmap(models, artifact_dir)
        print("   ✅ Saved: 03_metrics_heatmap.png")
    else:
        print("⚠️  Matplotlib not available. Skipping visualization.")

    print("📝 Generating report + production manifest...")
    summary = write_model_selection_artifacts(artifact_dir)
    print(f"   ✅ Saved: {artifact_dir / MODEL_COMPARISON_MD}")
    print(f"   ✅ Saved: {artifact_dir / MODEL_COMPARISON_HTML}")
    print(f"   ✅ Saved: {artifact_dir / PRODUCTION_MODEL_MANIFEST}")

    print("\n✨ Model comparison complete!")
    return {"best_model": best_model, "models": models, "summary": summary}


if __name__ == "__main__":
    import sys
    from pathlib import Path

    artifact_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    main(artifact_dir)
