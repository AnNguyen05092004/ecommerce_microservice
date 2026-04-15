from django.db import models


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("shipping", "Shipping"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    customer_id = models.IntegerField()
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    shipping_address = models.TextField()
    phone = models.CharField(max_length=20)
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - {self.status}"


class OrderItem(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ("computer", "Computer"),
        ("mobile", "Mobile"),
        ("clothes", "Clothes"),
        ("tablet", "Tablet"),
        ("audio", "Audio"),
        ("wearable", "Wearable"),
        ("component", "Component"),
        ("peripheral", "Peripheral"),
        ("monitor", "Monitor"),
        ("accessory", "Accessory"),
        ("charging", "Charging"),
        ("book", "Book"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_id = models.IntegerField()
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES)
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "order_items"

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"
