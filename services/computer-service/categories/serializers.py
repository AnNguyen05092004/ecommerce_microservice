from rest_framework import serializers
from .models import ComputerCategory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComputerCategory
        fields = ['id', 'name', 'description']

class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComputerCategory
        fields = ['name', 'description']
