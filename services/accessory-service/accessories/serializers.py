from rest_framework import serializers
from .models import Accessory, AccessorySpec
from categories.serializers import CategorySerializer


class AccessorySpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessorySpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class AccessorySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Accessory
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'created_at', 'updated_at']


class AccessoryDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    specs = AccessorySpecSerializer(read_only=True)

    class Meta:
        model = Accessory
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'specs', 'created_at', 'updated_at']


class AccessorySpecCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessorySpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class AccessoryCreateSerializer(serializers.ModelSerializer):
    specs = AccessorySpecCreateSerializer(required=False)
    category_id = serializers.IntegerField()

    class Meta:
        model = Accessory
        fields = ['name', 'brand', 'price', 'description', 'image', 'stock', 'category_id', 'specs']

    def create(self, validated_data):
        specs_data = validated_data.pop('specs', None)
        accessory = Accessory.objects.create(**validated_data)
        if specs_data:
            AccessorySpec.objects.create(accessory=accessory, **specs_data)
        return accessory

    def update(self, instance, validated_data):
        specs_data = validated_data.pop('specs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if specs_data:
            spec, _ = AccessorySpec.objects.get_or_create(accessory=instance)
            for attr, value in specs_data.items():
                setattr(spec, attr, value)
            spec.save()

        return instance
