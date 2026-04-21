#!/usr/bin/env python3
import argparse
import importlib
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "services" / "advisor-service"))


def main():
    run_benchmark_suite = importlib.import_module(
        "advisor.ml.benchmark_suite"
    ).run_benchmark_suite

    parser = argparse.ArgumentParser(description="Advisor baseline benchmark runner")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Gateway base URL",
    )
    parser.add_argument(
        "--config",
        default="docs/ai_benchmark_prompts.json",
        help="Benchmark config JSON path",
    )
    parser.add_argument(
        "--out",
        default="docs/reports/ai_baseline_report.json",
        help="Output report JSON path",
    )
    parser.add_argument(
        "--phase",
        default="phase-0-baseline",
        help="Phase label for the report (e.g. phase-0-baseline, phase-4-rag-v2)",
    )
    parser.add_argument(
        "--version",
        default="v1.0",
        help="Version tag for the report (e.g. v1.0, v2.1)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not payload.get("chat_prompts", []):
        raise SystemExit("chat_prompts is empty")
    if not payload.get("recommendation_cases", []):
        raise SystemExit("recommendation_cases is empty")
    out_path = Path(args.out)
    report = run_benchmark_suite(
        args.base_url, payload, out_path.parent, args.phase, args.version
    )

    print(f"Report written to: {out_path}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
