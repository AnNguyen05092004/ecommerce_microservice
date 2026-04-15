import requests
from django.conf import settings


def track_behavior_event(payload, timeout=3):
    session_id = (
        payload.get("session_id") or f"customer-{payload.get('user_id', 'anonymous')}"
    )
    body = {
        "user_id": str(payload.get("user_id", "")),
        "session_id": str(session_id),
        "event_type": payload.get("event_type", ""),
        "product_type": payload.get("product_type", ""),
        "product_id": payload.get("product_id"),
        "category_id": payload.get("category_id"),
        "query_text": payload.get("query_text", ""),
        "price": payload.get("price"),
        "quantity": payload.get("quantity"),
        "language": payload.get("language", "vi"),
        "metadata": payload.get("metadata", {}),
    }
    try:
        requests.post(
            f"{settings.ADVISOR_SERVICE_URL}/api/events/track/",
            json=body,
            timeout=timeout,
        )
    except requests.RequestException:
        return False
    return True
