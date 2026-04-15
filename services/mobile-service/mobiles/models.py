from django.db import models
from categories.models import MobileCategory


class Mobile(models.Model):
    STATUS_CHOICES = [('available', 'Available'), ('unavailable', 'Unavailable')]

    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, default='')
    image = models.CharField(max_length=500, blank=True, default='')
    stock = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    category = models.ForeignKey(MobileCategory, on_delete=models.SET_NULL, null=True, related_name='mobiles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mobiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.brand})"


class MobileSpec(models.Model):
    mobile = models.OneToOneField(Mobile, on_delete=models.CASCADE, related_name='specs')
    screen_size = models.CharField(max_length=20, blank=True, default='')
    battery = models.CharField(max_length=50, blank=True, default='')
    camera = models.CharField(max_length=100, blank=True, default='')
    storage = models.CharField(max_length=50, blank=True, default='')
    ram = models.CharField(max_length=50, blank=True, default='')
    os = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        db_table = 'mobile_specs'

    def __str__(self):
        return f"Specs for {self.mobile.name}"
