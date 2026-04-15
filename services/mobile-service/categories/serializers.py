from rest_framework import serializers
from .models import MobileCategory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileCategory
        fields = ['id', 'name', 'description']

class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileCategory
        fields = ['name', 'description']
