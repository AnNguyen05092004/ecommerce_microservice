from rest_framework import serializers
from .models import BookCategory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookCategory
        fields = ['id', 'name', 'description']

class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookCategory
        fields = ['name', 'description']
