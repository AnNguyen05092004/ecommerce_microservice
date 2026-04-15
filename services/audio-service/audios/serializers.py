from rest_framework import serializers
from .models import Audio, AudioSpec
from categories.serializers import CategorySerializer


class AudioSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class AudioSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Audio
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'created_at', 'updated_at']


class AudioDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    specs = AudioSpecSerializer(read_only=True)

    class Meta:
        model = Audio
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'specs', 'created_at', 'updated_at']


class AudioSpecCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class AudioCreateSerializer(serializers.ModelSerializer):
    specs = AudioSpecCreateSerializer(required=False)
    category_id = serializers.IntegerField()

    class Meta:
        model = Audio
        fields = ['name', 'brand', 'price', 'description', 'image', 'stock', 'category_id', 'specs']

    def create(self, validated_data):
        specs_data = validated_data.pop('specs', None)
        audio = Audio.objects.create(**validated_data)
        if specs_data:
            AudioSpec.objects.create(audio=audio, **specs_data)
        return audio

    def update(self, instance, validated_data):
        specs_data = validated_data.pop('specs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if specs_data:
            spec, _ = AudioSpec.objects.get_or_create(audio=instance)
            for attr, value in specs_data.items():
                setattr(spec, attr, value)
            spec.save()

        return instance
