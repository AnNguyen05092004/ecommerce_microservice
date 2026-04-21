#!/usr/bin/env python
"""
Comprehensive AI model training and evaluation pipeline.

Orchestrates:
1. Building behavior dataset from user events
2. Training all 5 models (Baseline, MLP, GRU, LSTM, BiLSTM)
3. Exporting user500.csv dataset
4. Generating model comparison report
5. Selecting best model for production

Run from project root: python scripts/setup_ai_models.py
Or with Django: python manage.py shell < scripts/setup_ai_models.py
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd, description, shell=False):
    """Run shell command with nice output."""
    print(f"\n{'='*70}")
    print(f"🚀 {description}")
    print(f"{'='*70}")
    print(f"Command: {cmd}\n")

    result = subprocess.run(
        cmd if shell else cmd.split(),
        shell=shell,
        cwd=Path(__file__).parent.parent,
    )

    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        return False

    print(f"✅ Completed: {description}")
    return True


def main():
    """Main pipeline."""
    parser = argparse.ArgumentParser(
        description="Train models, select production model, and benchmark advisor"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Gateway base URL for benchmark execution",
    )
    parser.add_argument(
        "--skip-benchmark", action="store_true", help="Skip benchmark/evaluation step"
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "services" / "advisor-service"))

    steps = [
        {
            "cmd": "python services/advisor-service/manage.py build_behavior_dataset",
            "desc": "Step 1: Build behavior dataset from user events",
        },
        {
            "cmd": "python services/advisor-service/manage.py train_baseline",
            "desc": "Step 2: Train Baseline (LogisticRegression) model",
        },
        {
            "cmd": "python services/advisor-service/manage.py train_behavior_v2",
            "desc": "Step 3: Train MLP (MLPClassifier) model",
        },
        {
            "cmd": "python services/advisor-service/manage.py train_behavior_gru",
            "desc": "Step 4: Train GRU (RNN) model",
        },
        {
            "cmd": "python services/advisor-service/manage.py train_behavior_lstm",
            "desc": "Step 5: Train LSTM model",
        },
        {
            "cmd": "python services/advisor-service/manage.py train_behavior_bilstm",
            "desc": "Step 6: Train BiLSTM model",
        },
        {
            "cmd": "python scripts/export_user500_csv.py",
            "desc": "Step 7: Export user500.csv dataset",
        },
        {
            "cmd": "python -c 'from scripts.compare_models import main; main()'",
            "desc": "Step 8: Generate model comparison report",
            "shell": True,
        },
    ]

    if not args.skip_benchmark:
        steps.append(
            {
                "cmd": f"python scripts/benchmark_advisor_baseline.py --base-url {args.base_url} --out services/advisor-service/artifacts/advisor_benchmark_report.json --phase phase-final --version v2.0",
                "desc": "Step 9: Run automated benchmark for chat + recommendation + semantic search",
            }
        )

    completed = 0
    failed = 0

    print("\n" + "=" * 70)
    print("🤖 AI Model Training Pipeline")
    print("=" * 70)
    print(f"Total steps: {len(steps)}")
    print("Starting at: " + subprocess.check_output("date").decode().strip())

    for i, step in enumerate(steps, 1):
        success = run_command(
            step["cmd"],
            step["desc"],
            shell=step.get("shell", False),
        )
        if success:
            completed += 1
        else:
            failed += 1
            if i < len(steps):
                response = (
                    input(f"\n⚠️  Continue with remaining steps? (y/n): ")
                    .strip()
                    .lower()
                )
                if response != "y":
                    print("❌ Pipeline aborted by user")
                    break

    print("\n" + "=" * 70)
    print("📊 Pipeline Summary")
    print("=" * 70)
    print(f"✅ Completed: {completed}/{len(steps)}")
    print(f"❌ Failed: {failed}/{len(steps)}")
    print(f"Finished at: {subprocess.check_output('date').decode().strip()}")

    if failed == 0:
        print("\n🎉 All steps completed successfully!")
        print("\nNext steps:")
        print(
            "1. Review behavior_model_manifest.json in services/advisor-service/artifacts/"
        )
        print(
            "2. Review model_comparison_report.html and advisor_benchmark_report.html"
        )
        print("3. Check user500.csv in services/advisor-service/artifacts/")
        print("4. Open admin AI metrics page to view linked reports")
        return 0
    else:
        print(f"\n⚠️  Pipeline completed with {failed} error(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
