import json
from pathlib import Path

import numpy as np

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, Dataset

    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False

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
TARGET_INDEX = {"computer": 0, "mobile": 1, "clothes": 2}


if TORCH_AVAILABLE:

    class SequenceDataset(Dataset):
        def __init__(self, sequence_path: Path, max_len: int = 20):
            raw = json.loads(sequence_path.read_text())
            self.rows = []
            for item in raw:
                events = item.get("events") or []
                categories = [
                    event.get("product_type")
                    for event in events
                    if event.get("product_type") in TARGET_INDEX
                ]
                if len(categories) < 2:
                    continue
                target = TARGET_INDEX[categories[-1]]
                features = []
                for event in events[:-1][-max_len:]:
                    features.append(
                        [
                            EVENT_INDEX.get(event.get("event_type"), 0),
                            PRODUCT_INDEX.get(event.get("product_type"), 0),
                        ]
                    )
                if not features:
                    continue
                while len(features) < max_len:
                    features.insert(0, [0, 0])
                self.rows.append(
                    (
                        torch.tensor(features, dtype=torch.float32),
                        torch.tensor(target, dtype=torch.long),
                    )
                )

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, index):
            return self.rows[index]

    class GRUCategoryModel(nn.Module):
        def __init__(
            self, input_size: int = 2, hidden_size: int = 16, output_size: int = 3
        ):
            super().__init__()
            self.gru = nn.GRU(
                input_size=input_size, hidden_size=hidden_size, batch_first=True
            )
            self.fc = nn.Linear(hidden_size, output_size)

        def forward(self, x):
            output, _ = self.gru(x)
            return self.fc(output[:, -1, :])


def train_gru(sequence_path: Path, artifact_dir: Path, epochs: int = 8):
    if not TORCH_AVAILABLE:
        return _train_transition_fallback(sequence_path, artifact_dir)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    dataset = SequenceDataset(sequence_path)
    if len(dataset) < 3:
        raise ValueError("Not enough sequence data to train GRU model")

    loader = DataLoader(dataset, batch_size=4, shuffle=True)
    model = GRUCategoryModel()
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    final_loss = 0.0
    for _ in range(epochs):
        for features, target in loader:
            optimizer.zero_grad()
            logits = model(features)
            loss = criterion(logits, target)
            loss.backward()
            optimizer.step()
            final_loss = float(loss.item())

    torch.save(model.state_dict(), artifact_dir / "gru_next_category.pt")
    metrics = {
        "rows": len(dataset),
        "epochs": epochs,
        "final_loss": final_loss,
        "mode": "gru_torch",
    }
    (artifact_dir / "gru_metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


def _train_transition_fallback(sequence_path: Path, artifact_dir: Path):
    """Fallback for environments where torch is unavailable."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    raw = json.loads(sequence_path.read_text())
    transitions = np.ones((3, 3), dtype=np.float64)
    row_count = 0

    for item in raw:
        events = item.get("events") or []
        categories = [
            event.get("product_type")
            for event in events
            if event.get("product_type") in TARGET_INDEX
        ]
        if len(categories) < 2:
            continue
        row_count += 1
        for idx in range(len(categories) - 1):
            src = TARGET_INDEX[categories[idx]]
            dst = TARGET_INDEX[categories[idx + 1]]
            transitions[src, dst] += 1

    transitions = transitions / transitions.sum(axis=1, keepdims=True)
    np.save(artifact_dir / "gru_transition_fallback.npy", transitions)
    metrics = {
        "rows": int(row_count),
        "mode": "transition_fallback",
        "note": "Torch unavailable, used transition fallback for next-category model.",
    }
    (artifact_dir / "gru_metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics
