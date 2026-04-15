from rest_framework import serializers
from .models import Tablet, TabletSpec
from categories.serializers import CategorySerializer


class TabletSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = TabletSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class TabletSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Tablet
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'created_at', 'updated_at']


class TabletDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    specs = TabletSpecSerializer(read_only=True)

    class Meta:
        model = Tablet
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'specs', 'created_at', 'updated_at']


class TabletSpecCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TabletSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class TabletCreateSerializer(serializers.ModelSerializer):
    specs = TabletSpecCreateSerializer(required=False)
    category_id = serializers.IntegerField()

    class Meta:
        model = Tablet
        fields = ['name', 'brand', 'price', 'description', 'image', 'stock', 'category_id', 'specs']

    def create(self, validated_data):
        specs_data = validated_data.pop('specs', None)
        tablet = Tablet.objects.create(**validated_data)
        if specs_data:
            TabletSpec.objects.create(tablet=tablet, **specs_data)
        return tablet

    def update(self, instance, validated_data):
        specs_data = validated_data.pop('specs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if specs_data:
            spec, _ = TabletSpec.objects.get_or_create(tablet=instance)
            for attr, value in specs_data.items():
                setattr(spec, attr, value)
            spec.save()

        return instance
