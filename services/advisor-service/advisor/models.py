from django.db import models


class UserEvent(models.Model):
    EVENT_TYPES = [
        ("product_list_view", "product_list_view"),
        ("product_detail_view", "product_detail_view"),
        ("search", "search"),
        ("add_to_cart", "add_to_cart"),
        ("update_cart", "update_cart"),
        ("remove_from_cart", "remove_from_cart"),
        ("checkout_start", "checkout_start"),
        ("order_created", "order_created"),
        ("review_created", "review_created"),
        ("chat_open", "chat_open"),
        ("chat_message_sent", "chat_message_sent"),
        ("chat_recommendation_click", "chat_recommendation_click"),
    ]
    PRODUCT_TYPES = [
        ("computer", "computer"),
        ("mobile", "mobile"),
        ("clothes", "clothes"),
        ("tablet", "tablet"),
        ("audio", "audio"),
        ("wearable", "wearable"),
        ("component", "component"),
        ("peripheral", "peripheral"),
        ("monitor", "monitor"),
        ("accessory", "accessory"),
        ("charging", "charging"),
        ("book", "book"),
    ]

    user_id = models.CharField(max_length=64, blank=True)
    session_id = models.CharField(max_length=128, db_index=True)
    event_type = models.CharField(max_length=64, choices=EVENT_TYPES, db_index=True)
    product_type = models.CharField(max_length=16, choices=PRODUCT_TYPES, blank=True)
    product_id = models.PositiveIntegerField(null=True, blank=True)
    category_id = models.PositiveIntegerField(null=True, blank=True)
    query_text = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=8, default="vi")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class KBDocument(models.Model):
    title = models.CharField(max_length=255)
    language = models.CharField(max_length=8, default="vi")
    source = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=64, blank=True)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title", "language"]
