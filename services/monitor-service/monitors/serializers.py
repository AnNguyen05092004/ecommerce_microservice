from rest_framework import serializers
from .models import Monitor, MonitorSpec
from categories.serializers import CategorySerializer


class MonitorSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitorSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class MonitorSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Monitor
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'created_at', 'updated_at']


class MonitorDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    specs = MonitorSpecSerializer(read_only=True)

    class Meta:
        model = Monitor
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'specs', 'created_at', 'updated_at']


class MonitorSpecCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitorSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class MonitorCreateSerializer(serializers.ModelSerializer):
    specs = MonitorSpecCreateSerializer(required=False)
    category_id = serializers.IntegerField()

    class Meta:
        model = Monitor
        fields = ['name', 'brand', 'price', 'description', 'image', 'stock', 'category_id', 'specs']

    def create(self, validated_data):
        specs_data = validated_data.pop('specs', None)
        monitor = Monitor.objects.create(**validated_data)
        if specs_data:
            MonitorSpec.objects.create(monitor=monitor, **specs_data)
        return monitor

    def update(self, instance, validated_data):
        specs_data = validated_data.pop('specs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if specs_data:
            spec, _ = MonitorSpec.objects.get_or_create(monitor=instance)
            for attr, value in specs_data.items():
                setattr(spec, attr, value)
            spec.save()

        return instance
