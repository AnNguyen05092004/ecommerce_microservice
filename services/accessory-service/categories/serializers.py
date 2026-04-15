from rest_framework import serializers
from .models import AccessoryCategory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessoryCategory
        fields = ['id', 'name', 'description']

class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessoryCategory
        fields = ['name', 'description']
