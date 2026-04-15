from rest_framework import serializers
from .models import Component, ComponentSpec
from categories.serializers import CategorySerializer


class ComponentSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponentSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class ComponentSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Component
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'created_at', 'updated_at']


class ComponentDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    specs = ComponentSpecSerializer(read_only=True)

    class Meta:
        model = Component
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'specs', 'created_at', 'updated_at']


class ComponentSpecCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponentSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class ComponentCreateSerializer(serializers.ModelSerializer):
    specs = ComponentSpecCreateSerializer(required=False)
    category_id = serializers.IntegerField()

    class Meta:
        model = Component
        fields = ['name', 'brand', 'price', 'description', 'image', 'stock', 'category_id', 'specs']

    def create(self, validated_data):
        specs_data = validated_data.pop('specs', None)
        component = Component.objects.create(**validated_data)
        if specs_data:
            ComponentSpec.objects.create(component=component, **specs_data)
        return component

    def update(self, instance, validated_data):
        specs_data = validated_data.pop('specs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if specs_data:
            spec, _ = ComponentSpec.objects.get_or_create(component=instance)
            for attr, value in specs_data.items():
                setattr(spec, attr, value)
            spec.save()

        return instance
