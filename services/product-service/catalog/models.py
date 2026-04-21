from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    PRODUCT_TYPES = [
        ("computer", "Laptop"),
        ("mobile", "Dien thoai"),
        ("clothes", "Quan ao"),
        ("tablet", "Tablet"),
        ("audio", "Audio"),
        ("wearable", "Wearable"),
        ("component", "Linh kien"),
        ("peripheral", "Phu kien PC"),
        ("monitor", "Man hinh"),
        ("accessory", "Phu kien dien thoai"),
        ("charging", "Sac va pin"),
        ("book", "Sach"),
    ]

    product_type = models.CharField(max_length=32, choices=PRODUCT_TYPES)
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=120, blank=True)
    price = models.DecimalField(max_digits=14, decimal_places=2)
    stock = models.IntegerField(default=0)
    image = models.URLField(blank=True)
    description = models.TextField(blank=True)
    specs = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=32, default="available")
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="products",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.product_type})"
