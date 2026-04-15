from rest_framework import serializers
from .models import Peripheral, PeripheralSpec
from categories.serializers import CategorySerializer


class PeripheralSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeripheralSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class PeripheralSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Peripheral
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'created_at', 'updated_at']


class PeripheralDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    specs = PeripheralSpecSerializer(read_only=True)

    class Meta:
        model = Peripheral
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'specs', 'created_at', 'updated_at']


class PeripheralSpecCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeripheralSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class PeripheralCreateSerializer(serializers.ModelSerializer):
    specs = PeripheralSpecCreateSerializer(required=False)
    category_id = serializers.IntegerField()

    class Meta:
        model = Peripheral
        fields = ['name', 'brand', 'price', 'description', 'image', 'stock', 'category_id', 'specs']

    def create(self, validated_data):
        specs_data = validated_data.pop('specs', None)
        peripheral = Peripheral.objects.create(**validated_data)
        if specs_data:
            PeripheralSpec.objects.create(peripheral=peripheral, **specs_data)
        return peripheral

    def update(self, instance, validated_data):
        specs_data = validated_data.pop('specs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if specs_data:
            spec, _ = PeripheralSpec.objects.get_or_create(peripheral=instance)
            for attr, value in specs_data.items():
                setattr(spec, attr, value)
            spec.save()

        return instance
