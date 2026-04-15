from rest_framework import serializers
from .models import Clothes, ClothesSpec
from categories.serializers import CategorySerializer


class ClothesSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClothesSpec
        fields = ['size', 'color', 'material']


class ClothesSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Clothes
        fields = ['id', 'name', 'brand', 'price', 'description', 'image',
                  'stock', 'status', 'gender', 'category', 'created_at', 'updated_at']


class ClothesDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    specs = ClothesSpecSerializer(read_only=True)

    class Meta:
        model = Clothes
        fields = ['id', 'name', 'brand', 'price', 'description', 'image',
                  'stock', 'status', 'gender', 'category', 'specs', 'created_at', 'updated_at']


class ClothesSpecCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClothesSpec
        fields = ['size', 'color', 'material']


class ClothesCreateSerializer(serializers.ModelSerializer):
    specs = ClothesSpecCreateSerializer(required=False)
    category_id = serializers.IntegerField()

    class Meta:
        model = Clothes
        fields = ['name', 'brand', 'price', 'description', 'image',
                  'stock', 'gender', 'category_id', 'specs']

    def create(self, validated_data):
        specs_data = validated_data.pop('specs', None)
        clothes = Clothes.objects.create(**validated_data)
        if specs_data:
            ClothesSpec.objects.create(clothes=clothes, **specs_data)
        return clothes

    def update(self, instance, validated_data):
        specs_data = validated_data.pop('specs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if specs_data:
            ClothesSpec.objects.update_or_create(clothes=instance, defaults=specs_data)
        return instance
