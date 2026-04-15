import json
import pickle
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


FEATURE_COLUMNS = [
    "views",
    "list_views",
    "searches",
    "cart_adds",
    "cart_updates",
    "checkouts",
    "orders",
    "reviews",
    "chat_messages",
    "buy_score_heuristic",
    "top_category",
]


class HeuristicBuyScoreModel:
    """Fallback model for tiny datasets in early MVP environments."""

    def predict_proba(self, dataframe):
        score = dataframe.get("buy_score_heuristic", 0).clip(0, 1)
        return [[1 - float(value), float(value)] for value in score]


def train_baseline(dataset_path: Path, artifact_dir: Path):
    artifact_dir.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(dataset_path)
    if dataset.empty or dataset["has_order"].nunique() < 2:
        model = HeuristicBuyScoreModel()
        metrics = {
            "mode": "heuristic_fallback",
            "rows": int(len(dataset)),
            "note": "Not enough labeled data to fit logistic regression.",
        }
        with (artifact_dir / "baseline_buy_score.pkl").open("wb") as output_file:
            pickle.dump(model, output_file)
        (artifact_dir / "baseline_metrics.json").write_text(
            json.dumps(metrics, indent=2)
        )
        return metrics

    X = dataset[FEATURE_COLUMNS]
    y = dataset["has_order"]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                StandardScaler(),
                [
                    "views",
                    "list_views",
                    "searches",
                    "cart_adds",
                    "cart_updates",
                    "checkouts",
                    "orders",
                    "reviews",
                    "chat_messages",
                    "buy_score_heuristic",
                ],
            ),
            ("cat", OneHotEncoder(handle_unknown="ignore"), ["top_category"]),
        ]
    )
    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=500)),
        ]
    )
    model.fit(X, y)

    predictions = model.predict(X)
    probabilities = model.predict_proba(X)[:, 1]
    metrics = {
        "accuracy": float(accuracy_score(y, predictions)),
        "f1": float(f1_score(y, predictions)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "rows": int(len(dataset)),
    }

    with (artifact_dir / "baseline_buy_score.pkl").open("wb") as output_file:
        pickle.dump(model, output_file)
    (artifact_dir / "baseline_metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics
