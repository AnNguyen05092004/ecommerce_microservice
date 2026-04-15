from rest_framework import serializers
from .models import ChargingCategory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargingCategory
        fields = ['id', 'name', 'description']

class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargingCategory
        fields = ['name', 'description']
