from rest_framework import serializers
from .models import Book, BookSpec
from categories.serializers import CategorySerializer


class BookSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class BookSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'created_at', 'updated_at']


class BookDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    specs = BookSpecSerializer(read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'name', 'brand', 'price', 'description', 'image', 'stock', 'status', 'category', 'specs', 'created_at', 'updated_at']


class BookSpecCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookSpec
        fields = ['cpu', 'ram', 'storage', 'gpu', 'screen_size', 'os']


class BookCreateSerializer(serializers.ModelSerializer):
    specs = BookSpecCreateSerializer(required=False)
    category_id = serializers.IntegerField()

    class Meta:
        model = Book
        fields = ['name', 'brand', 'price', 'description', 'image', 'stock', 'category_id', 'specs']

    def create(self, validated_data):
        specs_data = validated_data.pop('specs', None)
        book = Book.objects.create(**validated_data)
        if specs_data:
            BookSpec.objects.create(book=book, **specs_data)
        return book

    def update(self, instance, validated_data):
        specs_data = validated_data.pop('specs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if specs_data:
            spec, _ = BookSpec.objects.get_or_create(book=instance)
            for attr, value in specs_data.items():
                setattr(spec, attr, value)
            spec.save()

        return instance
