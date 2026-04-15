from rest_framework import serializers
from decimal import Decimal, InvalidOperation
from .models import Cart, CartItem


def _safe_decimal(value, default="0.00"):
    """Convert mixed numeric/string value to Decimal safely."""
    if value is None:
        return Decimal(default)

    text = str(value).strip()
    if not text:
        return Decimal(default)

    # Keep digits, minus sign, dot/comma and normalize separators.
    cleaned = "".join(ch for ch in text if ch.isdigit() or ch in ".,-")
    if not cleaned:
        return Decimal(default)

    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal(default)


class CartItemSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    def get_price(self, obj):
        value = _safe_decimal(getattr(obj, "price", 0))
        return f"{value:.2f}"

    def get_subtotal(self, obj):
        price = _safe_decimal(getattr(obj, "price", 0))
        quantity = int(getattr(obj, "quantity", 0) or 0)
        subtotal = price * quantity
        return f"{subtotal:.2f}"

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_id",
            "product_type",
            "product_name",
            "product_image",
            "quantity",
            "price",
            "subtotal",
        ]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "customer_id",
            "items",
            "total_amount",
            "created_at",
            "updated_at",
        ]

    def get_total_amount(self, obj):
        total = Decimal("0.00")
        for item in obj.items.all():
            price = _safe_decimal(getattr(item, "price", 0))
            quantity = int(getattr(item, "quantity", 0) or 0)
            total += price * quantity
        return f"{total:.2f}"


class CartItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    product_type = serializers.ChoiceField(
        choices=[
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
        ]
    )
    quantity = serializers.IntegerField(min_value=1, default=1)
