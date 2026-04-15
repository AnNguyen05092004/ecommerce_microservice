from rest_framework import serializers

from .models import KBDocument, UserEvent


class UserEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEvent
        fields = [
            "id",
            "user_id",
            "session_id",
            "event_type",
            "product_type",
            "product_id",
            "category_id",
            "query_text",
            "price",
            "quantity",
            "language",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TrackEventSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=False, allow_blank=True, max_length=64)
    session_id = serializers.CharField(max_length=128)
    event_type = serializers.ChoiceField(
        choices=[choice[0] for choice in UserEvent.EVENT_TYPES]
    )
    product_type = serializers.ChoiceField(
        choices=[choice[0] for choice in UserEvent.PRODUCT_TYPES],
        required=False,
        allow_blank=True,
    )
    product_id = serializers.IntegerField(required=False, allow_null=True)
    category_id = serializers.IntegerField(required=False, allow_null=True)
    query_text = serializers.CharField(required=False, allow_blank=True, max_length=255)
    price = serializers.DecimalField(
        required=False, allow_null=True, max_digits=12, decimal_places=2
    )
    quantity = serializers.IntegerField(required=False, allow_null=True)
    language = serializers.CharField(
        required=False, allow_blank=True, max_length=8, default="vi"
    )
    metadata = serializers.JSONField(required=False)


class RecommendationRequestSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=False, allow_blank=True)
    session_id = serializers.CharField(required=False, allow_blank=True)
    product_type = serializers.CharField(required=False, allow_blank=True)
    product_types = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    product_id = serializers.IntegerField(required=False, allow_null=True)
    limit = serializers.IntegerField(
        required=False, min_value=1, max_value=12, default=6
    )
    language = serializers.CharField(required=False, allow_blank=True, default="vi")
    ranker_variant = serializers.ChoiceField(
        required=False,
        choices=["auto", "v1", "v2"],
        default="auto",
    )


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    user_id = serializers.CharField(required=False, allow_blank=True)
    session_id = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(required=False, allow_blank=True, default="vi")
    product_type = serializers.CharField(required=False, allow_blank=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)


class KeywordSuggestionRequestSerializer(serializers.Serializer):
    prefix = serializers.CharField(max_length=120)
    session_id = serializers.CharField(required=False, allow_blank=True)
    user_id = serializers.CharField(required=False, allow_blank=True)
    product_type = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(required=False, allow_blank=True, default="vi")
    limit = serializers.IntegerField(
        required=False, min_value=1, max_value=8, default=5
    )


class SemanticSearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=240)
    session_id = serializers.CharField(required=False, allow_blank=True)
    user_id = serializers.CharField(required=False, allow_blank=True)
    product_type = serializers.CharField(required=False, allow_blank=True)
    product_types = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    language = serializers.CharField(required=False, allow_blank=True, default="vi")
    limit = serializers.IntegerField(
        required=False, min_value=1, max_value=96, default=24
    )


class KBDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KBDocument
        fields = [
            "id",
            "title",
            "language",
            "source",
            "category",
            "content",
            "metadata",
            "created_at",
            "updated_at",
        ]
