from rest_framework import serializers
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = [
            "id",
            "customer_id",
            "customer_name",
            "product_id",
            "product_type",
            "rating",
            "comment",
            "created_at",
        ]


class ReviewCreateSerializer(serializers.Serializer):
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
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, default="", allow_blank=True)
