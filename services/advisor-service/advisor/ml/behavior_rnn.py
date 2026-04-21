"""Vanilla RNN-based behavior profile classifier.

Uses event sequences (event_type + product_type per step) to classify
a user session into one of 5 behavior profiles. Falls back gracefully
when PyTorch is unavailable — callers must handle None returns.
"""

import json
import pickle
from pathlib import Path

import numpy as np

# model RNN thuần (vanilla RNN) theo chuỗi sự kiện.

try:
    import torch
    from torch import nn

    TORCH_AVAILABLE = True
except Exception:  # noqa: BLE001
    TORCH_AVAILABLE = False


# -----------------------------------------------------------------------------
# Constants shared between training and inference
# -----------------------------------------------------------------------------

BEHAVIOR_CLASSES = [
    "impulse_buyer",
    "researcher",
    "loyal_customer",
    "price_sensitive",
    "window_shopper",
]
CLASS_INDEX = {label: idx for idx, label in enumerate(BEHAVIOR_CLASSES)}

EVENT_INDEX = {
    "product_list_view": 1,
    "product_detail_view": 2,
    "search": 3,
    "add_to_cart": 4,
    "update_cart": 5,
    "remove_from_cart": 6,
    "checkout_start": 7,
    "order_created": 8,
    "review_created": 9,
    "chat_open": 10,
    "chat_message_sent": 11,
    "chat_recommendation_click": 12,
}
PRODUCT_INDEX = {"computer": 1, "mobile": 2, "clothes": 3}

MAX_SEQ_LEN = 30
INPUT_SIZE = 2  # [normalised_event_type, normalised_product_type]
HIDDEN_SIZE = 32
NUM_LAYERS = 2
NUM_CLASSES = len(BEHAVIOR_CLASSES)

RNN_WEIGHTS_FILENAME = "behavior_rnn.pt"
RNN_CONFIG_FILENAME = "behavior_rnn_config.pkl"
RNN_METRICS_FILENAME = "behavior_rnn_metrics.json"


# -----------------------------------------------------------------------------
# Feature encoding
# -----------------------------------------------------------------------------


def _encode_sequence(events, max_len: int = MAX_SEQ_LEN):
    """Encode a list of event dicts (or ORM objects) to (max_len, 2) float array.

    Each step is [event_type / 12, product_type / 3] so values are in [0, 1].
    Sequences shorter than max_len are left-padded with zeros.
    """
    encoded = []
    for event in events:
        if hasattr(event, "event_type"):
            et = event.event_type
            pt = event.product_type or ""
        else:
            et = event.get("event_type", "")
            pt = event.get("product_type", "") or ""
        encoded.append(
            [
                EVENT_INDEX.get(et, 0) / 12.0,
                PRODUCT_INDEX.get(pt, 0) / 3.0,
            ]
        )
    # Left-pad
    while len(encoded) < max_len:
        encoded.insert(0, [0.0, 0.0])
    return np.array(encoded[-max_len:], dtype=np.float32)


# -----------------------------------------------------------------------------
# Neural network (only defined when torch is available)
# -----------------------------------------------------------------------------

if TORCH_AVAILABLE:

    class BehaviorRNNNet(nn.Module):
        """Vanilla (Elman) RNN classifier for behavior profiles."""

        def __init__(
            self,
            input_size: int = INPUT_SIZE,
            hidden_size: int = HIDDEN_SIZE,
            num_layers: int = NUM_LAYERS,
            num_classes: int = NUM_CLASSES,
            dropout: float = 0.3,
        ):
            super().__init__()
            self.rnn = nn.RNN(
                input_size,
                hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
                nonlinearity="tanh",
            )
            self.classifier = nn.Sequential(
                nn.Dropout(dropout),
                nn.Linear(hidden_size, num_classes),
            )

        def forward(self, x):
            _, hidden = self.rnn(x)
            return self.classifier(hidden[-1])


# -----------------------------------------------------------------------------
# Training
# -----------------------------------------------------------------------------


def train_behavior_rnn(sequence_path: Path, artifact_dir: Path, epochs: int = 25):
    """Train vanilla RNN on labeled behavior sequences from behavior_sequences.json.

    Returns metrics dict. Always writes RNN_METRICS_FILENAME so callers can
    inspect mode/errors without crashing.
    """
    artifact_dir.mkdir(parents=True, exist_ok=True)

    if not TORCH_AVAILABLE:
        metrics = {
            "mode": "torch_unavailable",
            "note": "Install torch to enable RNN training. Falling back to MLP.",
        }
        (artifact_dir / RNN_METRICS_FILENAME).write_text(json.dumps(metrics, indent=2))
        return metrics

    raw = json.loads(sequence_path.read_text())
    labeled = [
        (row["events"], row["behavior_label"])
        for row in raw
        if row.get("behavior_label") in CLASS_INDEX and row.get("events")
    ]

    if len(labeled) < 10:
        metrics = {
            "mode": "insufficient_data",
            "rows": len(labeled),
            "note": f"Need ≥10 labeled sequences, got {len(labeled)}.",
        }
        (artifact_dir / RNN_METRICS_FILENAME).write_text(json.dumps(metrics, indent=2))
        return metrics

    X = np.stack([_encode_sequence(events) for events, _ in labeled])
    y = np.array([CLASS_INDEX[label] for _, label in labeled], dtype=np.int64)

    # Chronological split — same philosophy as dataset.py
    split = max(1, int(len(labeled) * 0.8))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    config = {
        "input_size": INPUT_SIZE,
        "hidden_size": HIDDEN_SIZE,
        "num_layers": NUM_LAYERS,
        "num_classes": NUM_CLASSES,
        "dropout": 0.3,
    }
    model = BehaviorRNNNet(**config)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    X_train_t = torch.tensor(X_train)
    y_train_t = torch.tensor(y_train)
    batch_size = min(32, len(X_train))
    val_accuracy_history = []

    if len(y_test) > 0:
        from sklearn.metrics import accuracy_score, f1_score

    model.train()
    for _ in range(epochs):
        perm = torch.randperm(len(X_train_t))
        X_shuf = X_train_t[perm]
        y_shuf = y_train_t[perm]
        for i in range(0, len(X_train_t), batch_size):
            xb = X_shuf[i : i + batch_size]
            yb = y_shuf[i : i + batch_size]
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
        scheduler.step()

        if len(y_test) > 0:
            model.eval()
            with torch.no_grad():
                logits = model(torch.tensor(X_test))
                preds = logits.argmax(dim=1).numpy()
            val_accuracy_history.append(round(float(accuracy_score(y_test, preds)), 4))
            model.train()

    # Evaluation
    model.eval()
    accuracy = 0.0
    macro_f1 = 0.0
    if len(y_test) > 0:
        with torch.no_grad():
            logits = model(torch.tensor(X_test))
            preds = logits.argmax(dim=1).numpy()
        accuracy = float(accuracy_score(y_test, preds))
        macro_f1 = float(f1_score(y_test, preds, average="macro", zero_division=0))

    # Persist weights + config
    torch.save(model.state_dict(), artifact_dir / RNN_WEIGHTS_FILENAME)
    with (artifact_dir / RNN_CONFIG_FILENAME).open("wb") as fh:
        pickle.dump(config, fh)

    metrics = {
        "mode": "rnn_v1",
        "rows": len(labeled),
        "train_rows": int(split),
        "test_rows": int(len(y_test)),
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "classes": BEHAVIOR_CLASSES,
        "epochs": epochs,
        "val_accuracy_history": val_accuracy_history,
    }
    (artifact_dir / RNN_METRICS_FILENAME).write_text(json.dumps(metrics, indent=2))
    return metrics


# -----------------------------------------------------------------------------
# Inference
# -----------------------------------------------------------------------------


def infer_behavior_rnn(events, artifact_dir: Path):
    """Classify behavior profile from an event sequence using vanilla RNN.

    Args:
        events: list of UserEvent ORM objects or dicts with event_type / product_type.
        artifact_dir: path to artifacts directory.

    Returns:
        dict with label/confidence/mode, or None if model unavailable.
    """
    weights_path = artifact_dir / RNN_WEIGHTS_FILENAME
    config_path = artifact_dir / RNN_CONFIG_FILENAME

    if not TORCH_AVAILABLE or not weights_path.exists() or not config_path.exists():
        return None

    try:
        with config_path.open("rb") as fh:
            config = pickle.load(fh)

        model = BehaviorRNNNet(**config)
        model.load_state_dict(
            torch.load(weights_path, map_location="cpu", weights_only=True)
        )
        model.eval()

        arr = _encode_sequence(events)
        x = torch.tensor(arr).unsqueeze(0)  # (1, seq_len, input_size)

        with torch.no_grad():
            logits = model(x)
            probs = torch.softmax(logits, dim=1).squeeze(0).numpy()

        best_idx = int(probs.argmax())
        return {
            "label": BEHAVIOR_CLASSES[best_idx],
            "confidence": round(float(probs[best_idx]), 4),
            "mode": "rnn_v1",
        }
    except Exception:  # noqa: BLE001
        return None
