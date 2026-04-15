from rest_framework import serializers
from .models import Wearable, WearableSpec
from categories.serializers import CategorySerializer


class WearableSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = WearableSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class WearableSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Wearable
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'created_at', 'updated_at']


class WearableDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    specs = WearableSpecSerializer(read_only=True)

    class Meta:
        model = Wearable
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'specs', 'created_at', 'updated_at']


class WearableSpecCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WearableSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class WearableCreateSerializer(serializers.ModelSerializer):
    specs = WearableSpecCreateSerializer(required=False)
    category_id = serializers.IntegerField()

    class Meta:
        model = Wearable
        fields = ['name', 'brand', 'price', 'description', 'image', 'stock', 'category_id', 'specs']

    def create(self, validated_data):
        specs_data = validated_data.pop('specs', None)
        wearable = Wearable.objects.create(**validated_data)
        if specs_data:
            WearableSpec.objects.create(wearable=wearable, **specs_data)
        return wearable

    def update(self, instance, validated_data):
        specs_data = validated_data.pop('specs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if specs_data:
            spec, _ = WearableSpec.objects.get_or_create(wearable=instance)
            for attr, value in specs_data.items():
                setattr(spec, attr, value)
            spec.save()

        return instance
