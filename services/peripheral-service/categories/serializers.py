from rest_framework import serializers
from .models import PeripheralCategory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PeripheralCategory
        fields = ['id', 'name', 'description']

class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeripheralCategory
        fields = ['name', 'description']
