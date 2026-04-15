from rest_framework import serializers
from .models import Charging, ChargingSpec
from categories.serializers import CategorySerializer


class ChargingSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargingSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class ChargingSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Charging
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'created_at', 'updated_at']


class ChargingDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    specs = ChargingSpecSerializer(read_only=True)

    class Meta:
        model = Charging
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'specs', 'created_at', 'updated_at']


class ChargingSpecCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargingSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class ChargingCreateSerializer(serializers.ModelSerializer):
    specs = ChargingSpecCreateSerializer(required=False)
    category_id = serializers.IntegerField()

    class Meta:
        model = Charging
        fields = ['name', 'brand', 'price', 'description', 'image', 'stock', 'category_id', 'specs']

    def create(self, validated_data):
        specs_data = validated_data.pop('specs', None)
        charging = Charging.objects.create(**validated_data)
        if specs_data:
            ChargingSpec.objects.create(charging=charging, **specs_data)
        return charging

    def update(self, instance, validated_data):
        specs_data = validated_data.pop('specs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if specs_data:
            spec, _ = ChargingSpec.objects.get_or_create(charging=instance)
            for attr, value in specs_data.items():
                setattr(spec, attr, value)
            spec.save()

        return instance
