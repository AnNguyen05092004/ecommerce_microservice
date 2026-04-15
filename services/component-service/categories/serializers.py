from rest_framework import serializers
from .models import ComponentCategory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponentCategory
        fields = ['id', 'name', 'description']

class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponentCategory
        fields = ['name', 'description']
