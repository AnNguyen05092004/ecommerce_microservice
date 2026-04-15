from rest_framework import serializers
from .models import TabletCategory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TabletCategory
        fields = ['id', 'name', 'description']

class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TabletCategory
        fields = ['name', 'description']
