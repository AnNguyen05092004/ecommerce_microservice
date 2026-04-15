from rest_framework import serializers
from .models import WearableCategory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WearableCategory
        fields = ['id', 'name', 'description']

class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WearableCategory
        fields = ['name', 'description']
