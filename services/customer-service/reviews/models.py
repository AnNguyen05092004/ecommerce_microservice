from django.db import models


class Review(models.Model):
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

    customer_id = models.IntegerField()
    customer_name = models.CharField(max_length=255, default="")
    product_id = models.IntegerField()
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES)
    rating = models.IntegerField()  # 1-5
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reviews"
        ordering = ["-created_at"]
        unique_together = ["customer_id", "product_id", "product_type"]

    def __str__(self):
        return f"Review by {self.customer_name} - {self.rating}★"
