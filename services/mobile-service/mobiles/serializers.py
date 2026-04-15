from rest_framework import serializers
from .models import Mobile, MobileSpec
from categories.serializers import CategorySerializer


class MobileSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileSpec
        fields = ['screen_size', 'battery', 'camera', 'storage', 'ram', 'os']


class MobileSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    class Meta:
        model = Mobile
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'created_at', 'updated_at']


class MobileDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    specs = MobileSpecSerializer(read_only=True)
    class Meta:
        model = Mobile
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'specs', 'created_at', 'updated_at']


class MobileSpecCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileSpec
        fields = ['screen_size', 'battery', 'camera', 'storage', 'ram', 'os']


class MobileCreateSerializer(serializers.ModelSerializer):
    specs = MobileSpecCreateSerializer(required=False)
    category_id = serializers.IntegerField()

    class Meta:
        model = Mobile
        fields = ['name', 'brand', 'price', 'description', 'image', 'stock', 'category_id', 'specs']

    def create(self, validated_data):
        specs_data = validated_data.pop('specs', None)
        mobile = Mobile.objects.create(**validated_data)
        if specs_data:
            MobileSpec.objects.create(mobile=mobile, **specs_data)
        return mobile

    def update(self, instance, validated_data):
        specs_data = validated_data.pop('specs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if specs_data:
            spec, _ = MobileSpec.objects.get_or_create(mobile=instance)
            for attr, value in specs_data.items():
                setattr(spec, attr, value)
            spec.save()
        return instance
