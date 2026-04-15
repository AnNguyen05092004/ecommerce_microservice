from rest_framework import serializers
from .models import Computer, ComputerSpec
from categories.serializers import CategorySerializer


class ComputerSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComputerSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class ComputerSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Computer
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'created_at', 'updated_at']


class ComputerDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    specs = ComputerSpecSerializer(read_only=True)

    class Meta:
        model = Computer
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'specs', 'created_at', 'updated_at']


class ComputerSpecCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComputerSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class ComputerCreateSerializer(serializers.ModelSerializer):
    specs = ComputerSpecCreateSerializer(required=False)
    category_id = serializers.IntegerField()

    class Meta:
        model = Computer
        fields = ['name', 'brand', 'price', 'description', 'image', 'stock', 'category_id', 'specs']

    def create(self, validated_data):
        specs_data = validated_data.pop('specs', None)
        computer = Computer.objects.create(**validated_data)
        if specs_data:
            ComputerSpec.objects.create(computer=computer, **specs_data)
        return computer

    def update(self, instance, validated_data):
        specs_data = validated_data.pop('specs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if specs_data:
            spec, _ = ComputerSpec.objects.get_or_create(computer=instance)
            for attr, value in specs_data.items():
                setattr(spec, attr, value)
            spec.save()

        return instance
