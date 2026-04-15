from django.db import models


class Cart(models.Model):
    customer_id = models.IntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carts"

    def __str__(self):
        return f"Cart #{self.id} (customer: {self.customer_id})"


class CartItem(models.Model):
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

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product_id = models.IntegerField()
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES)
    product_name = models.CharField(max_length=255, default="")
    product_image = models.CharField(max_length=500, blank=True, default="")
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "cart_items"
        unique_together = ["cart", "product_id", "product_type"]

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.price * self.quantity
