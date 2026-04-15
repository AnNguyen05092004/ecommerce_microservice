from django.db import models
from categories.models import ClothesCategory


class Clothes(models.Model):
    STATUS_CHOICES = [('available', 'Available'), ('unavailable', 'Unavailable')]
    GENDER_CHOICES = [('male', 'Male'), ('female', 'Female'), ('unisex', 'Unisex')]

    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, default='')
    image = models.CharField(max_length=500, blank=True, default='')
    stock = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='unisex')
    category = models.ForeignKey(ClothesCategory, on_delete=models.SET_NULL, null=True, related_name='clothes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clothes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.brand})"


class ClothesSpec(models.Model):
    SIZE_CHOICES = [('XS', 'XS'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL')]

    clothes = models.OneToOneField(Clothes, on_delete=models.CASCADE, related_name='specs')
    size = models.CharField(max_length=5, choices=SIZE_CHOICES, blank=True, default='')
    color = models.CharField(max_length=50, blank=True, default='')
    material = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        db_table = 'clothes_specs'

    def __str__(self):
        return f"Specs for {self.clothes.name}"
