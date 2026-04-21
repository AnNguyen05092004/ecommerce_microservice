"""Export user behavior dataset in standardized user500.csv format.

This script exports the first 500 users (or all available users) with their
behavior profiles and creates a standardized CSV file for AI model training
and evaluation.
"""

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# Event scoring for behavior inference
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


def label_behavior_profile(counts: Counter, event_count: int):
    """Classify user behavior into 5 profiles."""
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


def export_user500_csv(events_queryset, output_path: Path, limit: int = 500):
    """
    Export user behavior data to user500.csv format.

    Args:
        events_queryset: Django queryset of UserEvent objects
        output_path: Path to save the CSV file
        limit: Maximum number of users to export (default: 500)

    Returns:
        Tuple of (csv_path, metadata_dict)
    """
    output_path.mkdir(parents=True, exist_ok=True)

    # Group events by user
    grouped = defaultdict(list)
    for event in events_queryset.order_by("created_at"):
        user_id = event.user_id or event.session_id
        grouped[user_id].append(event)

    # Extract first 500 users
    user_ids = list(grouped.keys())[:limit]
    rows = []

    for i, user_id in enumerate(user_ids, 1):
        entity_events = grouped[user_id]
        counts = Counter(evt.event_type for evt in entity_events)
        category_counts = Counter(
            evt.product_type for evt in entity_events if evt.product_type
        )

        behavior_label, label_confidence = label_behavior_profile(
            counts, len(entity_events)
        )

        top_category = (
            category_counts.most_common(1)[0][0] if category_counts else "computer"
        )
        buy_score = sum(EVENT_SCORE.get(evt.event_type, 0) for evt in entity_events)

        rows.append(
            {
                "user_id": user_id,
                "user_index": i,
                "behavior_label": behavior_label,
                "behavior_confidence": label_confidence,
                "views": counts.get("product_detail_view", 0),
                "list_views": counts.get("product_list_view", 0),
                "searches": counts.get("search", 0),
                "cart_adds": counts.get("add_to_cart", 0),
                "cart_updates": counts.get("update_cart", 0),
                "checkouts": counts.get("checkout_start", 0),
                "orders": counts.get("order_created", 0),
                "reviews": counts.get("review_created", 0),
                "chat_interactions": counts.get("chat_message_sent", 0),
                "buy_score": buy_score,
                "top_category": top_category,
                "has_purchased": 1 if counts.get("order_created", 0) > 0 else 0,
                "event_count": len(entity_events),
            }
        )

    # Save to CSV
    csv_path = output_path / "user500.csv"
    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)

    # Generate metadata
    metadata = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total_users": len(user_ids),
        "file_path": str(csv_path),
        "columns": list(df.columns),
        "behavior_taxonomy": BEHAVIOR_TAXONOMY,
        "behavior_distribution": df["behavior_label"].value_counts().to_dict(),
        "rows": len(df),
        "avg_event_count": float(df["event_count"].mean()),
        "avg_buy_score": float(df["buy_score"].mean()),
        "users_with_purchases": int(df["has_purchased"].sum()),
    }

    # Save metadata
    metadata_path = output_path / "user500_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    return csv_path, metadata


def export_from_django(limit: int = 500):
    """Django wrapper to export user500 dataset."""
    try:
        import django
        from django.conf import settings

        # Configure Django if not already configured
        if not settings.configured:
            django.setup()

        from advisor.models import UserEvent

        output_dir = Path(settings.ARTIFACTS_DIR)
        csv_path, metadata = export_user500_csv(
            UserEvent.objects.all(), output_dir, limit=limit
        )

        print(f"✅ Exported {metadata['total_users']} users to {csv_path}")
        print(f"\nDataset metadata:")
        print(f"  - Total users: {metadata['total_users']}")
        print(f"  - Total events: {sum(metadata['behavior_distribution'].values())}")
        print(f"  - Average events per user: {metadata['avg_event_count']:.2f}")
        print(f"  - Users with purchases: {metadata['users_with_purchases']}")
        print(f"  - Behavior distribution:")
        for behavior, count in metadata["behavior_distribution"].items():
            pct = (count / metadata["total_users"]) * 100
            print(f"    • {behavior}: {count} ({pct:.1f}%)")

        return csv_path, metadata
    except ImportError:
        print("❌ Django not available. Use from Django management command instead.")
        return None, None


if __name__ == "__main__":
    import sys

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    csv_path, metadata = export_from_django(limit=limit)
    if csv_path:
        print(
            f"\n📊 Metadata saved to: {Path(csv_path).parent / 'user500_metadata.json'}"
        )
