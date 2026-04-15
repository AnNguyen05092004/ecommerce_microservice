from rest_framework import serializers
from .models import MonitorCategory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitorCategory
        fields = ['id', 'name', 'description']

class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitorCategory
        fields = ['name', 'description']
