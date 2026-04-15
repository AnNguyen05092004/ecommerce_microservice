from rest_framework import serializers
from .models import AudioCategory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioCategory
        fields = ['id', 'name', 'description']

class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioCategory
        fields = ['name', 'description']
