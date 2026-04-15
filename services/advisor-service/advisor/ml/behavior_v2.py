import json
import pickle
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer

# model MLP phân loại profile hành vi.

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
    "event_count",
    "top_category",
]

NUMERIC_COLUMNS = [
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
    "event_count",
]

CATEGORICAL_COLUMNS = ["top_category"]

MODEL_FILENAME = "behavior_v2_mlp.pkl"
METRICS_FILENAME = "behavior_v2_metrics.json"

SUPPORTED_PRODUCT_TYPES = {
    "computer",
    "mobile",
    "clothes",
    "tablet",
    "audio",
    "wearable",
    "component",
    "peripheral",
    "monitor",
    "accessory",
    "charging",
    "book",
}


class BehaviorV2HeuristicModel:
    """Fallback profile model when dataset is too small for stable MLP training."""

    CLASSES = [
        "impulse_buyer",
        "researcher",
        "loyal_customer",
        "price_sensitive",
        "window_shopper",
    ]

    def predict_proba(self, dataframe):
        rows = []
        for _, row in dataframe.iterrows():
            orders = float(row.get("orders", 0) or 0)
            searches = float(row.get("searches", 0) or 0)
            views = float(row.get("views", 0) or 0)
            cart_adds = float(row.get("cart_adds", 0) or 0)
            cart_updates = float(row.get("cart_updates", 0) or 0)

            scores = {
                "loyal_customer": 0.15 + min(0.8, orders * 0.35),
                "impulse_buyer": 0.2 + min(0.6, (cart_adds + orders) * 0.2),
                "researcher": 0.1 + min(0.7, (searches + views * 0.5) * 0.06),
                "price_sensitive": 0.1 + min(0.65, cart_updates * 0.15),
                "window_shopper": 0.1 + min(0.65, max(0.0, views - cart_adds) * 0.07),
            }
            total = sum(scores.values()) or 1.0
            rows.append([scores[label] / total for label in self.CLASSES])
        return rows

    @property
    def classes_(self):
        return self.CLASSES


def _build_training_frame(dataset: pd.DataFrame):
    frame = dataset.copy()
    for column in FEATURE_COLUMNS:
        if column not in frame.columns:
            frame[column] = 0

    frame["top_category"] = (
        frame["top_category"].fillna("computer").astype(str).str.strip().str.lower()
    )
    frame.loc[~frame["top_category"].isin(SUPPORTED_PRODUCT_TYPES), "top_category"] = (
        "computer"
    )

    frame = frame.dropna(subset=["behavior_label"])
    return frame


def train_behavior_v2(dataset_path: Path, artifact_dir: Path):
    artifact_dir.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(dataset_path)
    frame = _build_training_frame(dataset)

    if frame.empty or frame["behavior_label"].nunique() < 2 or len(frame) < 12:
        fallback = BehaviorV2HeuristicModel()
        metrics = {
            "mode": "heuristic_fallback",
            "rows": int(len(frame)),
            "classes": sorted(frame["behavior_label"].dropna().unique().tolist()),
            "note": "Insufficient dataset for stable MLP training.",
        }
        with (artifact_dir / MODEL_FILENAME).open("wb") as output_file:
            pickle.dump(fallback, output_file)
        (artifact_dir / METRICS_FILENAME).write_text(json.dumps(metrics, indent=2))
        return metrics

    X = frame[FEATURE_COLUMNS]
    y = frame["behavior_label"]

    x_train, x_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42,
        stratify=y if y.nunique() > 1 else None,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_COLUMNS),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "classifier",
                MLPClassifier(
                    hidden_layer_sizes=(64, 32),
                    activation="relu",
                    alpha=1e-4,
                    learning_rate_init=0.001,
                    max_iter=500,
                    random_state=42,
                ),
            ),
        ]
    )

    model.fit(x_train, y_train)
    pred = model.predict(x_test)

    majority_label = y_train.value_counts().idxmax()
    majority_pred = [majority_label for _ in range(len(y_test))]
    baseline_macro_f1 = float(f1_score(y_test, majority_pred, average="macro"))
    model_macro_f1 = float(f1_score(y_test, pred, average="macro"))
    improvement_pct = (
        ((model_macro_f1 - baseline_macro_f1) / baseline_macro_f1) * 100
        if baseline_macro_f1 > 0
        else 0.0
    )

    metrics = {
        "mode": "mlp_v2",
        "rows": int(len(frame)),
        "accuracy": float(accuracy_score(y_test, pred)),
        "macro_f1": model_macro_f1,
        "baseline_macro_f1": baseline_macro_f1,
        "macro_f1_improvement_pct": float(improvement_pct),
        "classes": sorted(frame["behavior_label"].unique().tolist()),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
    }

    with (artifact_dir / MODEL_FILENAME).open("wb") as output_file:
        pickle.dump(model, output_file)
    (artifact_dir / METRICS_FILENAME).write_text(json.dumps(metrics, indent=2))
    return metrics


def infer_behavior_v2(features: dict, artifact_dir: Path, events=None):
    """Classify behavior profile.

    Tries GRU sequence model first (when *events* sequence is provided and GRU
    model files exist), then falls back to the MLP/heuristic pipeline.
    """
    # --- GRU path ----------------------------------------------------------
    if events:
        try:
            from advisor.ml.behavior_gru import infer_behavior_gru  # noqa: PLC0415

            gru_result = infer_behavior_gru(events, artifact_dir)
            if gru_result is not None:
                if "top3_classes" not in gru_result:
                    gru_result["top3_classes"] = [
                        {
                            "label": gru_result.get("label", "window_shopper"),
                            "confidence": round(
                                float(gru_result.get("confidence", 0.0)), 4
                            ),
                        }
                    ]
                return gru_result
        except Exception:  # noqa: BLE001
            pass

    # --- MLP / heuristic fallback ------------------------------------------
    model_path = artifact_dir / MODEL_FILENAME
    if not model_path.exists():
        return {
            "label": "uncertain",
            "confidence": 0.0,
            "mode": "unavailable",
            "top3_classes": [],
        }

    with model_path.open("rb") as input_file:
        model = pickle.load(input_file)

    frame = pd.DataFrame(
        [{column: features.get(column, 0) for column in FEATURE_COLUMNS}]
    )
    top_category = str(frame.loc[0, "top_category"] or "computer").strip().lower()
    if top_category not in SUPPORTED_PRODUCT_TYPES:
        top_category = "computer"
    frame.loc[0, "top_category"] = top_category
    probabilities = model.predict_proba(frame)[0]
    classes = list(getattr(model, "classes_", BehaviorV2HeuristicModel.CLASSES))

    ranked_indices = sorted(
        range(len(probabilities)), key=lambda idx: probabilities[idx], reverse=True
    )
    best_idx = int(ranked_indices[0])
    best_confidence = float(probabilities[best_idx])
    top3 = [
        {
            "label": str(classes[idx]),
            "confidence": round(float(probabilities[idx]), 4),
        }
        for idx in ranked_indices[:3]
    ]

    # Quality gate: map low-confidence predictions to uncertain.
    if best_confidence < 0.4:
        return {
            "label": "uncertain",
            "confidence": round(best_confidence, 4),
            "mode": "model_low_confidence",
            "top3_classes": top3,
        }

    return {
        "label": str(classes[best_idx]),
        "confidence": round(best_confidence, 4),
        "mode": "model",
        "top3_classes": top3,
    }
