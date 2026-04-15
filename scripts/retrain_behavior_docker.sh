#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/5] Checking Docker daemon..."
if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running. Please start Docker Desktop and rerun this script."
  exit 1
fi

echo "[2/5] Ensuring advisor-service container is running..."
docker compose up -d advisor-service

echo "[3/5] Rebuilding behavior dataset in container..."
docker compose exec -T advisor-service python manage.py build_behavior_dataset

echo "[4/5] Retraining behavior_v2 model in container..."
docker compose exec -T advisor-service python manage.py train_behavior_v2

echo "[5/5] Printing artifact metrics summary..."
docker compose exec -T advisor-service sh -lc 'ls -lh /app/artifacts/behavior_dataset.csv /app/artifacts/behavior_v2_mlp.pkl /app/artifacts/behavior_v2_metrics.json'
docker compose exec -T advisor-service python - <<'PY'
import json
from pathlib import Path
p = Path('/app/artifacts/behavior_v2_metrics.json')
print('metrics_path:', p)
print(json.dumps(json.loads(p.read_text()), indent=2))
PY

echo "Retrain completed successfully."
