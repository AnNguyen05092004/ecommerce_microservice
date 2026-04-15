from rest_framework import serializers
from .models import ClothesCategory


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClothesCategory
        fields = ['id', 'name', 'description']


class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClothesCategory
        fields = ['name', 'description']
