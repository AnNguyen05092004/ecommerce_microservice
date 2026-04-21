from django.core.management.base import BaseCommand
from catalog.models import Category, Product


SEED_ITEMS = [
    {
        "product_type": "computer",
        "name": "Gigabyte Aero 15",
        "brand": "Gigabyte",
        "price": 61000000,
        "stock": 7,
        "image": "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?auto=format&fit=crop&w=1200&q=80",
        "category": "Laptop",
    },
    {
        "product_type": "computer",
        "name": "Zenbook Pro Duo 15",
        "brand": "Zenbook",
        "price": 63000000,
        "stock": 6,
        "image": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=1200&q=80",
        "category": "Laptop",
    },
    {
        "product_type": "mobile",
        "name": "iPhone 13",
        "brand": "Apple",
        "price": 20000000,
        "stock": 9,
        "image": "https://images.unsplash.com/photo-1592286632028-4f5f0b53f8ef?auto=format&fit=crop&w=1200&q=80",
        "category": "Smartphone",
    },
    {
        "product_type": "book",
        "name": "Atomic Habits",
        "brand": "Avery",
        "price": 289000,
        "stock": 10,
        "image": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&w=1200&q=80",
        "category": "Sach ky nang",
    },
]


class Command(BaseCommand):
    help = "Seed initial catalog products for DDD-only stack"

    def handle(self, *args, **options):
        created = 0
        for item in SEED_ITEMS:
            category, _ = Category.objects.get_or_create(name=item["category"])
            _, was_created = Product.objects.get_or_create(
                product_type=item["product_type"],
                name=item["name"],
                defaults={
                    "brand": item["brand"],
                    "price": item["price"],
                    "stock": item["stock"],
                    "image": item["image"],
                    "category": category,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"seed_catalog complete: created {created} products")
        )
