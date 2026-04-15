import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from advisor.models import UserEvent


EVENT_SCORE = {
    "product_list_view": 1,
    "product_detail_view": 2,
    "search": 2,
    "add_to_cart": 4,
    "update_cart": 3,
    "remove_from_cart": -1,
    "checkout_start": 5,
    "order_created": 8,
    "review_created": 3,
    "chat_open": 1,
    "chat_message_sent": 2,
    "chat_recommendation_click": 3,
}


BEHAVIOR_TAXONOMY = [
    "impulse_buyer",
    "researcher",
    "loyal_customer",
    "price_sensitive",
    "window_shopper",
]


def _entity_key(event):
    return event.user_id or event.session_id


def _label_behavior_profile(counts: Counter, event_count: int):
    cart_adds = counts.get("add_to_cart", 0)
    checkouts = counts.get("checkout_start", 0)
    orders = counts.get("order_created", 0)
    searches = counts.get("search", 0)
    details = counts.get("product_detail_view", 0)
    updates = counts.get("update_cart", 0)
    removes = counts.get("remove_from_cart", 0)

    if orders >= 2:
        return "loyal_customer", 0.9
    if orders >= 1 and (cart_adds + checkouts) >= 2:
        return "impulse_buyer", 0.82
    if searches >= 4 and details >= 5 and orders == 0:
        return "researcher", 0.76
    if removes >= 2 and (searches + updates) >= 3 and orders == 0:
        return "price_sensitive", 0.74
    if details >= 3 and cart_adds == 0 and orders == 0:
        return "window_shopper", 0.72

    if event_count <= 2:
        return "window_shopper", 0.55
    if searches >= details:
        return "researcher", 0.58
    return "impulse_buyer", 0.52


def _time_based_split(dataframe: pd.DataFrame):
    if dataframe.empty:
        return dataframe.copy(), dataframe.copy(), dataframe.copy()

    sorted_frame = dataframe.sort_values(by="last_event_at").reset_index(drop=True)
    total = len(sorted_frame)
    train_end = max(1, int(total * 0.7))
    val_end = max(train_end + 1, int(total * 0.85)) if total > 2 else total

    train = sorted_frame.iloc[:train_end].copy()
    val = sorted_frame.iloc[train_end:val_end].copy()
    test = sorted_frame.iloc[val_end:].copy()
    return train, val, test


def _build_data_quality_report(dataset: pd.DataFrame):
    label_distribution = {}
    if "behavior_label" in dataset.columns:
        counts = dataset["behavior_label"].value_counts().to_dict()
        label_distribution = {str(key): int(value) for key, value in counts.items()}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": int(len(dataset)),
        "columns": [str(column) for column in dataset.columns],
        "null_counts": {
            str(key): int(value)
            for key, value in dataset.isnull().sum().to_dict().items()
        },
        "duplicate_rows": int(dataset.duplicated().sum()),
        "label_distribution": label_distribution,
        "taxonomy": BEHAVIOR_TAXONOMY,
    }


def build_behavior_dataset(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    events = list(UserEvent.objects.all().order_by("created_at"))
    rows = []
    sequences = []
    grouped = defaultdict(list)

    for event in events:
        grouped[_entity_key(event)].append(event)

    for entity_id, entity_events in grouped.items():
        counts = Counter(evt.event_type for evt in entity_events)
        category_counts = Counter(
            evt.product_type for evt in entity_events if evt.product_type
        )
        behavior_label, label_confidence = _label_behavior_profile(
            counts, len(entity_events)
        )
        has_order = int(counts.get("order_created", 0) > 0)
        top_category = "computer"
        if category_counts:
            top_category = category_counts.most_common(1)[0][0]

        first_event = entity_events[0].created_at if entity_events else None
        last_event = entity_events[-1].created_at if entity_events else None

        rows.append(
            {
                "entity_id": entity_id,
                "views": counts.get("product_detail_view", 0),
                "list_views": counts.get("product_list_view", 0),
                "searches": counts.get("search", 0),
                "cart_adds": counts.get("add_to_cart", 0),
                "cart_updates": counts.get("update_cart", 0),
                "checkouts": counts.get("checkout_start", 0),
                "orders": counts.get("order_created", 0),
                "reviews": counts.get("review_created", 0),
                "chat_messages": counts.get("chat_message_sent", 0),
                "buy_score_heuristic": sum(
                    EVENT_SCORE.get(evt.event_type, 0) for evt in entity_events
                ),
                "top_category": top_category,
                "has_order": has_order,
                "behavior_label": behavior_label,
                "label_confidence": round(float(label_confidence), 3),
                "event_count": len(entity_events),
                "first_event_at": first_event.isoformat() if first_event else "",
                "last_event_at": last_event.isoformat() if last_event else "",
            }
        )

        sequences.append(
            {
                "entity_id": entity_id,
                "events": [
                    {
                        "event_type": evt.event_type,
                        "product_type": evt.product_type,
                        "product_id": evt.product_id,
                        "category_id": evt.category_id,
                        "metadata": evt.metadata,
                        "created_at": evt.created_at.isoformat(),
                    }
                    for evt in entity_events
                ],
                "behavior_label": behavior_label,
                "label_confidence": round(float(label_confidence), 3),
            }
        )

    dataset_path = output_dir / "behavior_dataset.csv"
    sequence_path = output_dir / "behavior_sequences.json"
    dataset = pd.DataFrame(rows)
    dataset.to_csv(dataset_path, index=False)
    sequence_path.write_text(json.dumps(sequences, ensure_ascii=True, indent=2))

    train, val, test = _time_based_split(dataset)
    train.to_csv(output_dir / "behavior_train.csv", index=False)
    val.to_csv(output_dir / "behavior_val.csv", index=False)
    test.to_csv(output_dir / "behavior_test.csv", index=False)

    report = _build_data_quality_report(dataset)
    (output_dir / "behavior_data_quality.json").write_text(
        json.dumps(report, ensure_ascii=True, indent=2)
    )
    return dataset_path, sequence_path
